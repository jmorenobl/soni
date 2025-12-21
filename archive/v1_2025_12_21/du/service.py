"""NLU Service - Centralized NLU processing with 2-pass architecture.

This service encapsulates the complete NLU pipeline, making it reusable
across different components (understand_node, RuntimeLoop, etc.) while
maintaining DRY and SOLID principles.

Architecture:
- Pass 1: Intent detection via DU module (no slot context)
- Pass 2: Slot extraction via SlotExtractor (only for StartFlow commands)

This follows SRP by having a single component responsible for NLU processing.
"""

import logging
from typing import Any, Literal

from soni.core.commands import StartFlow
from soni.core.constants import SlotWaitType
from soni.core.types import (
    ConfigProtocol,
    DialogueState,
    DUProtocol,
    RuntimeContext,
    SlotExtractorProtocol,
)
from soni.du.models import CommandInfo, DialogueContext, FlowInfo, SlotValue
from soni.du.slot_extractor import SlotExtractionInput

logger = logging.getLogger(__name__)


# =============================================================================
# Context Building Functions (Source of Truth)
# =============================================================================


def build_du_context(state: DialogueState, context: RuntimeContext) -> DialogueContext:
    """Construct NLU context from current dialogue state.

    Builds a comprehensive DialogueContext object containing all information
    the NLU needs to understand user intent: available flows, commands,
    current slots, and expected slot.

    Note: This does NOT include flow_slots for Pass 1 to avoid context overload.
    Slot extraction happens in Pass 2 if StartFlow is detected.

    Args:
        state: Current dialogue state from LangGraph
        context: Runtime context with config and managers

    Returns:
        DialogueContext ready for NLU processing
    """
    config = context.config
    fm = context.flow_manager

    # 1. Available flows from config
    available_flows = []
    if hasattr(config, "flows"):
        for name, flow_cfg in config.flows.items():
            # Use trigger_intents from YAML or fallback to heuristic
            trigger_intents = flow_cfg.trigger_intents or [f"start {name}", name]
            available_flows.append(
                FlowInfo(
                    name=name,
                    description=flow_cfg.description,
                    trigger_intents=trigger_intents,
                )
            )

    # 2. Available commands
    # Include required_fields so LLM knows what to provide
    available_commands = [
        CommandInfo(
            command_type="start_flow",
            description="Start a new flow. flow_name must match one of available_flows.name",
            required_fields=["flow_name"],
            example='{"type": "start_flow", "flow_name": "check_balance"}',
        ),
        CommandInfo(
            command_type="set_slot",
            description="Set a slot value when user provides information",
            required_fields=["slot", "value"],
            example='{"type": "set_slot", "slot": "account_type", "value": "checking"}',
        ),
    ]

    # 3. Active flow and expected slot
    curr_ctx = fm.get_active_context(state)
    active_flow = curr_ctx["flow_name"] if curr_ctx else None
    expected_slot = state.get("waiting_for_slot")  # Set by collect/confirm nodes

    # 4. Current slots - convert from dict to SlotValue list
    current_slots: list[SlotValue] = []
    if curr_ctx:
        flow_id = curr_ctx["flow_id"]
        slot_dict = state.get("flow_slots", {}).get(flow_id, {})
        for slot_name, slot_value in slot_dict.items():
            # Skip internal slots (prefixed with __)
            if not slot_name.startswith("__"):
                # NOTE: Converting to string to maintain consistency with NLU expectations
                # Type coercion happens in validators, not here
                current_slots.append(
                    SlotValue(name=slot_name, value=str(slot_value) if slot_value else None)
                )

    # Determine conversation state
    waiting_for_slot_type = state.get("waiting_for_slot_type")

    # Detect conversation state using explicit slot type
    # Replaces the previous suffix-based heuristic (waiting_for_slot.endswith("_confirmed"))
    is_confirming = waiting_for_slot_type == SlotWaitType.CONFIRMATION
    conversation_state: Literal["idle", "collecting", "confirming", "action_pending"] = (
        "idle" if not active_flow else "confirming" if is_confirming else "collecting"
    )

    return DialogueContext(
        available_flows=available_flows,
        available_commands=available_commands,
        active_flow=active_flow,
        current_slots=current_slots,
        expected_slot=expected_slot,  # Keeping original variable name for compatibility
        conversation_state=conversation_state,
    )


def get_flow_slot_definitions(
    config: ConfigProtocol,
    flow_name: str,
) -> list[SlotExtractionInput]:
    """Get slot definitions for a specific flow.

    Collects slot names from collect steps in the flow, then looks up
    each slot in config.slots to get type information for NLU extraction.

    Args:
        config: Soni configuration (via Protocol)
        flow_name: Name of the flow to get slots for

    Returns:
        List of SlotExtractionInput for Pass 2 of two-pass NLU
    """
    flow_cfg = config.flows.get(flow_name)
    if not flow_cfg:
        logger.debug(f"Flow '{flow_name}' not found in config")
        return []

    # Collect slot names from collect steps
    slot_names = {step.slot for step in flow_cfg.steps if step.type == "collect" and step.slot}

    if not slot_names:
        logger.debug(f"Flow '{flow_name}' has no collect steps")
        return []

    # Build SlotExtractionInput for each slot with definition
    slot_defs: list[SlotExtractionInput] = []
    for name in slot_names:
        slot_config = config.slots.get(name)
        if slot_config:
            slot_defs.append(
                SlotExtractionInput(
                    name=name,
                    slot_type=slot_config.type,
                    description=slot_config.description or slot_config.prompt,
                    examples=slot_config.examples,
                )
            )
        else:
            # Slot used but not defined globally - use minimal info
            logger.debug(f"Slot '{name}' used in flow but not defined in config.slots")
            slot_defs.append(
                SlotExtractionInput(
                    name=name,
                    slot_type="string",
                    description=f"Value for {name}",
                )
            )

    logger.debug(f"Built {len(slot_defs)} slot definitions for flow '{flow_name}'")
    return slot_defs


# =============================================================================
# NLU Service Class
# =============================================================================


class NLUService:
    """Centralized service for NLU processing.

    This service encapsulates the 2-pass NLU architecture:
    1. Pass 1: Intent detection (SoniDU)
    2. Pass 2: Slot extraction (SlotExtractor - only for StartFlow)

    By centralizing this logic, we:
    - Maintain DRY (no duplication between understand_node and RuntimeLoop)
    - Follow SRP (single responsibility: NLU processing)
    - Enable testability (easy to mock)
    - Support dependency injection (depends on abstractions)

    Usage:
        nlu_service = NLUService(du, slot_extractor)
        commands = await nlu_service.process_message(message, state, runtime_ctx)
    """

    def __init__(
        self,
        du: DUProtocol,
        slot_extractor: SlotExtractorProtocol | None = None,
    ):
        """Initialize NLU service with dependencies.

        Args:
            du: Dialogue Understanding module (DUProtocol)
            slot_extractor: Optional slot extractor for Pass 2
        """
        self.du = du
        self.slot_extractor = slot_extractor

    async def process_message(
        self,
        message: str,
        state: DialogueState,
        runtime_ctx: RuntimeContext,
    ) -> list[Any]:
        """Process user message through 2-pass NLU pipeline.

        Pass 1: Intent Detection
        - Analyzes user message to detect intent
        - Returns commands (StartFlow, SetSlot, etc.)
        - Does NOT include slot definitions (avoids context overload)

        Pass 2: Slot Extraction (conditional)
        - Only runs if StartFlow detected in Pass 1
        - Extracts slot values mentioned in the same message
        - Appends SetSlot commands to Pass 1 results

        Args:
            message: User's input message
            state: Current dialogue state
            runtime_ctx: Runtime context with config and managers

        Returns:
            List of NLU commands (StartFlow, SetSlot, etc.)
        """
        # Pass 1: Intent detection via DU
        logger.debug(f"NLU Pass 1: Intent detection for message: '{message[:50]}...'")
        du_context = build_du_context(state, runtime_ctx)
        nlu_output = await self.du.acall(message, du_context)

        # Start with commands from Pass 1
        commands = list(nlu_output.commands)

        # Pass 2: Slot extraction if StartFlow detected
        start_flow_cmd = next(
            (c for c in commands if isinstance(c, StartFlow)),
            None,
        )

        if start_flow_cmd and self.slot_extractor:
            flow_name = start_flow_cmd.flow_name
            slot_defs = get_flow_slot_definitions(runtime_ctx.config, flow_name)

            if slot_defs:
                logger.debug(
                    f"NLU Pass 2: Extracting {len(slot_defs)} slots for flow '{flow_name}'"
                )
                try:
                    extracted_slots = await self.slot_extractor.acall(message, slot_defs)

                    if extracted_slots:
                        logger.info(
                            f"Pass 2 extracted {len(extracted_slots)} slots: "
                            f"{[s.slot for s in extracted_slots]}"
                        )
                        commands.extend(extracted_slots)
                except Exception as e:
                    # Log but don't fail - slot extraction is optional
                    logger.warning(f"Pass 2 slot extraction failed: {e}")

        logger.debug(f"NLU processing complete: {len(commands)} commands generated")
        return commands

    def serialize_commands(self, commands: list[Any]) -> list[dict[str, Any]]:
        """Serialize commands for state storage.

        Converts command objects to dictionaries for JSON serialization.

        Args:
            commands: List of command objects

        Returns:
            List of serialized command dictionaries
        """
        serialized = []
        for cmd in commands:
            if hasattr(cmd, "model_dump"):
                # Pydantic model
                serialized.append(cmd.model_dump())
            elif isinstance(cmd, dict):
                # Already serialized
                serialized.append(cmd)
            else:
                # Generic object - try to extract attributes
                logger.warning(f"Unexpected command type: {type(cmd)}")
                serialized.append({"type": str(type(cmd).__name__)})

        return serialized
