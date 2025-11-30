"""Dynamic action scoping for Soni Framework"""

import hashlib
import json
import logging
from typing import Any

from cachetools import TTLCache  # type: ignore[import-untyped]

from soni.core.config import SoniConfig
from soni.core.interfaces import IScopeManager
from soni.core.state import DialogueState

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
        elif isinstance(config, dict):
            # For backward compatibility, extract flows from dict
            self.flows = config.get("flows", {})
        else:
            self.flows = {}

        # Global actions that are always available
        self.global_actions = ["help", "cancel", "restart"]

        # Cache for scoped actions
        self.scoping_cache: TTLCache[str, list[str]] = TTLCache(
            maxsize=cache_size,  # Cache up to 500 results
            ttl=cache_ttl,  # 1 minute TTL (60 seconds)
        )

        logger.debug(f"ScopeManager initialized with {len(self.flows)} flows")

    def _get_cache_key(
        self,
        state: DialogueState,
    ) -> str:
        """
        Generate cache key for scoping request.

        Args:
            state: Current dialogue state

        Returns:
            Cache key as MD5 hash string
        """
        # Create hash based on flow and slots (main factors for scoping)
        key_data = json.dumps(
            {
                "flow": state.current_flow,
                "slots": state.slots,
            },
            sort_keys=True,
        )
        return hashlib.md5(key_data.encode()).hexdigest()

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
        # Convert dict to DialogueState if needed
        if isinstance(state, dict):
            state = DialogueState.from_dict(state)

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

        current_flow = state.current_flow

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
            # No active flow - allow starting any flow
            for flow_name in self.flows.keys():
                actions.append(f"start_{flow_name}")

        # Remove duplicates
        result = list(set(actions))

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
            for step in flow_config.steps:
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

    def _get_pending_slots(self, flow_config: Any, state: DialogueState) -> list[str]:
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
        for slot_name in collect_slots:
            # Check if slot is already filled
            if slot_name and slot_name not in state.slots:
                pending.append(slot_name)

        return pending

    def _extract_collect_slots(self, flow_config: Any) -> list[str]:
        """Extract slot names from collect steps."""
        slots: list[str] = []

        if hasattr(flow_config, "steps"):
            # FlowConfig (Pydantic model)
            slots.extend(self._extract_from_flowconfig_steps(flow_config.steps))
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
