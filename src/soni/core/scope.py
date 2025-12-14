"""Dynamic action scoping for Soni Framework"""

import logging
from typing import Any

from cachetools import TTLCache

from soni.core.config import SoniConfig
from soni.core.interfaces import IScopeManager
from soni.core.security import SecurityGuardrails
from soni.core.state import DialogueState, get_all_slots, get_current_flow
from soni.utils.hashing import generate_cache_key_from_dict

logger = logging.getLogger(__name__)


class ScopeManager(IScopeManager):
    """
    Manages dynamic scoping of available actions based on dialogue state.

    This class filters actions to reduce context noise for the LLM:
    - Only includes actions relevant to current flow
    - Always includes global actions (help, cancel, restart)
    - Considers completed slots to determine relevant actions
    """

    def __init__(
        self,
        config: SoniConfig | dict[str, Any] | None = None,
        cache_size: int = 500,
        cache_ttl: int = 60,
    ) -> None:
        """
        Initialize ScopeManager.

        Args:
            config: SoniConfig or configuration dictionary
            cache_size: Maximum number of cached scoping results
            cache_ttl: Time-to-live for cache entries in seconds
        """
        if isinstance(config, SoniConfig):
            self.config = config
            self.flows = config.flows
            # Initialize security guardrails from config
            security_config = config.settings.security
            self.guardrails = (
                SecurityGuardrails(
                    allowed_actions=security_config.allowed_actions
                    if security_config.allowed_actions
                    else None,
                    blocked_intents=security_config.blocked_intents
                    if security_config.blocked_intents
                    else None,
                    max_confidence_threshold=security_config.max_confidence_threshold,
                    min_confidence_threshold=security_config.min_confidence_threshold,
                )
                if security_config.enable_guardrails
                else None
            )
        elif isinstance(config, dict):
            # For backward compatibility, extract flows from dict
            self.flows = config.get("flows", {})
            # Try to extract security config from dict
            security_settings = config.get("settings", {}).get("security", {})
            if security_settings.get("enable_guardrails", True):
                self.guardrails = SecurityGuardrails(
                    allowed_actions=security_settings.get("allowed_actions") or None,
                    blocked_intents=security_settings.get("blocked_intents") or None,
                    max_confidence_threshold=security_settings.get(
                        "max_confidence_threshold", 0.95
                    ),
                    min_confidence_threshold=security_settings.get("min_confidence_threshold", 0.0),
                )
            else:
                self.guardrails = None
        else:
            self.flows = {}
            self.guardrails = None

        # Global actions that are always available
        self.global_actions = ["help", "cancel", "restart"]

        # Cache for scoped actions
        self.scoping_cache: TTLCache[str, list[str]] = TTLCache(
            maxsize=cache_size,  # Cache up to 500 results
            ttl=cache_ttl,  # 1 minute TTL (60 seconds)
        )

        logger.debug(
            f"ScopeManager initialized with {len(self.flows)} flows, "
            f"guardrails: {'enabled' if self.guardrails else 'disabled'}"
        )

    def _get_cache_key(
        self,
        state: DialogueState | dict[str, Any],
    ) -> str:
        """
        Generate cache key for scoping request.

        Cache key format: MD5 hash of JSON-serialized dict containing flow and slots.
        This ensures scoping is recalculated when dialogue context changes.

        Args:
            state: Current dialogue state containing flow and slots

        Returns:
            32-character hexadecimal MD5 hash string

        Example:
            >>> state = create_empty_state()
            >>> push_flow(state, "booking")
            >>> set_slot(state, "origin", "NYC")
            >>> set_slot(state, "destination", "LAX")
            >>> manager._get_cache_key(state)
            'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6'

        Note:
            Cache key changes when:
            - current_flow changes (different flow context)
            - slots change (different dialogue state)
            This ensures scoped actions are recalculated for different contexts.
        """
        # Create hash based on flow and slots (main factors for scoping)
        current_flow = get_current_flow(state)
        all_slots = get_all_slots(state)
        return generate_cache_key_from_dict(
            {
                "flow": current_flow,
                "slots": all_slots,
            }
        )

    def get_available_actions(
        self,
        state: DialogueState | dict[str, Any],
    ) -> list[str]:
        """
        Get list of available actions based on current dialogue state.

        Args:
            state: Current dialogue state (DialogueState or dict)

        Returns:
            List of available action names
        """
        # Import here to avoid circular import
        # state can be DialogueState (TypedDict) or dict - both work with our helper functions
        # No conversion needed since get_current_flow and get_all_slots handle both

        # Check cache first
        cache_key = self._get_cache_key(state)
        if cache_key in self.scoping_cache:
            logger.debug(f"Scoping cache hit for key: {cache_key[:8]}...")
            cached_actions: list[str] = self.scoping_cache[cache_key]
            return cached_actions

        # Cache miss - compute actions
        logger.debug("Scoping cache miss, computing actions")

        # Start with global actions (always available)
        actions: list[str] = self.global_actions.copy()

        current_flow = get_current_flow(state)

        if current_flow and current_flow != "none":
            # We're in a flow - only include actions relevant to this flow
            flow_config = self.flows.get(current_flow)
            if flow_config:
                # Add flow-specific actions
                # Actions are defined in the flow configuration
                flow_actions = self._get_flow_actions(flow_config)
                actions.extend(flow_actions)

                # Add slots that still need to be collected
                pending_slots = self._get_pending_slots(flow_config, state)
                for slot_name in pending_slots:
                    actions.append(f"provide_{slot_name}")

        else:
            # No active flow - flow names are provided via get_available_flows()
            # Actions here are only action handlers, not flow triggers
            pass

        # Remove duplicates
        result = list(set(actions))

        # Apply security guardrails if enabled
        if self.guardrails:
            filtered_actions = []
            for action in result:
                is_valid, error = self.guardrails.validate_action(action)
                if is_valid:
                    filtered_actions.append(action)
                else:
                    logger.debug(f"Action '{action}' filtered by guardrails: {error}")
            result = filtered_actions

        # Cache result
        self.scoping_cache[cache_key] = result
        logger.debug(f"Cached scoping result for key: {cache_key[:8]}...")

        return result

    def _get_flow_actions(self, flow_config: Any) -> list[str]:
        """
        Extract action names from flow configuration.

        Supports multiple flow configuration formats:
        - Steps with type: action
        - Process with steps
        - Direct action references

        Args:
            flow_config: Flow configuration (FlowConfig or dict)

        Returns:
            List of action names used in this flow
        """
        actions: list[str] = []

        # Try different configuration formats
        actions.extend(self._extract_actions_from_steps(flow_config))
        actions.extend(self._extract_actions_from_process(flow_config))
        actions.extend(self._extract_actions_from_direct_list(flow_config))

        return list(set(actions))  # Remove duplicates

    def _extract_actions_from_steps(self, flow_config: Any) -> list[str]:
        """Extract actions from procedural steps."""
        actions: list[str] = []

        # Handle FlowConfig (Pydantic model)
        if hasattr(flow_config, "steps"):
            for step in flow_config.steps_or_process:
                if hasattr(step, "type") and step.type == "action":
                    if hasattr(step, "call") and step.call:
                        actions.append(step.call)
        # Handle dict format
        elif isinstance(flow_config, dict):
            steps = flow_config.get("steps", [])
            for step in steps:
                if isinstance(step, dict) and step.get("type") == "action":
                    action_name = step.get("call") or step.get("action")
                    if action_name:
                        actions.append(action_name)

        return actions

    def _extract_actions_from_process(self, flow_config: Any) -> list[str]:
        """Extract actions from process steps (dict format only)."""
        actions: list[str] = []

        if isinstance(flow_config, dict):
            process = flow_config.get("process")
            if isinstance(process, list):
                for step in process:
                    if isinstance(step, dict) and step.get("type") == "action":
                        action_name = step.get("call") or step.get("action")
                        if action_name:
                            actions.append(action_name)

        return actions

    def _extract_actions_from_direct_list(self, flow_config: Any) -> list[str]:
        """Extract actions from direct actions list (dict format only)."""
        actions: list[str] = []

        if isinstance(flow_config, dict):
            direct_actions = flow_config.get("actions", [])
            if isinstance(direct_actions, list):
                actions.extend(direct_actions)

        return actions

    def get_expected_slots(
        self,
        flow_name: str | None,
        available_actions: list[str] | None = None,
    ) -> list[str]:
        """Get list of expected slot names for a flow.

        If flow_name is None or "none", attempts to infer the flow from
        available_actions (e.g., "start_book_flight" suggests "book_flight").

        Args:
            flow_name: Name of the flow to get slots for, or None/"none" to infer
            available_actions: Optional list of available actions for flow inference

        Returns:
            List of expected slot names for the flow, empty list if flow not found
        """
        # Determine which flow to check
        flow_to_check = flow_name

        # If no flow specified, return empty list - caller should provide flow_name
        if not flow_to_check or flow_to_check == "none":
            return []
        if not flow_to_check or flow_to_check == "none":
            return []

        # Get flow configuration
        flow_config = self.flows.get(flow_to_check)
        if not flow_config:
            logger.warning(f"Flow '{flow_to_check}' not found in configuration")
            return []

        # Extract slots using existing private method
        try:
            expected_slots = self._extract_collect_slots(flow_config)
            logger.debug(
                f"Extracted {len(expected_slots)} expected slots from flow '{flow_to_check}': {expected_slots}"
            )
            return expected_slots
        except (AttributeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to extract expected slots from flow '{flow_to_check}': {e}")
            return []

    def _get_pending_slots(
        self, flow_config: Any, state: DialogueState | dict[str, Any]
    ) -> list[str]:
        """
        Get list of slots that still need to be collected.

        Args:
            flow_config: Flow configuration (FlowConfig or dict)
            state: Current dialogue state

        Returns:
            List of slot names that are not yet filled
        """
        pending: list[str] = []

        # Extract slots from flow steps
        collect_slots = self._extract_collect_slots(flow_config)
        all_slots = get_all_slots(state)
        for slot_name in collect_slots:
            # Check if slot is already filled
            if slot_name and slot_name not in all_slots:
                pending.append(slot_name)

        return pending

    def _extract_collect_slots(self, flow_config: Any) -> list[str]:
        """Extract slot names from collect steps."""
        slots: list[str] = []

        if hasattr(flow_config, "steps"):
            # FlowConfig (Pydantic model)
            slots.extend(self._extract_from_flowconfig_steps(flow_config.steps_or_process))
        elif isinstance(flow_config, dict):
            # Dict format
            slots.extend(self._extract_from_dict_steps(flow_config))
            slots.extend(self._extract_from_dict_process(flow_config))

        return slots

    def _extract_from_flowconfig_steps(self, steps: Any) -> list[str]:
        """Extract slots from FlowConfig steps."""
        slots: list[str] = []
        for step in steps:
            if hasattr(step, "type") and step.type == "collect":
                if hasattr(step, "slot") and step.slot:
                    slots.append(step.slot)
        return slots

    def _extract_from_dict_steps(self, flow_config: dict[str, Any]) -> list[str]:
        """Extract slots from dict steps."""
        slots: list[str] = []
        steps = flow_config.get("steps", [])
        for step in steps:
            if isinstance(step, dict) and step.get("type") == "collect":
                slot_name = step.get("slot")
                if slot_name:
                    slots.append(slot_name)
        return slots

    def _extract_from_dict_process(self, flow_config: dict[str, Any]) -> list[str]:
        """Extract slots from dict process steps."""
        slots: list[str] = []
        process = flow_config.get("process")
        if isinstance(process, list):
            for step in process:
                if isinstance(step, dict) and step.get("type") == "collect":
                    slot_name = step.get("slot")
                    if slot_name:
                        slots.append(slot_name)
        return slots

    def get_available_flows(
        self,
        state: DialogueState | dict[str, Any],
    ) -> dict[str, str]:
        """Get available flows with descriptions.

        Returns dict mapping flow names to descriptions. This is used by NLU
        to detect when user wants to switch to a different flow (intent change).

        Args:
            state: Current dialogue state (DialogueState or dict)

        Returns:
            Dict mapping flow names to descriptions
        """
        # Always return all flows with descriptions so NLU can detect intent changes
        # The routing logic will decide whether to allow the switch or treat as digression
        flows_with_descriptions = {}
        for flow_name, flow_config in self.config.flows.items():
            flows_with_descriptions[flow_name] = flow_config.description
        return flows_with_descriptions
