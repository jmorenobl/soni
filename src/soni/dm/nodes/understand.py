"""Understand node - NLU orchestrator.

Refactored to comply with SRP by delegating responsibilities to specialized components:
- HistoryConverter: Message format conversion
- DialogueContextBuilder: NLU context construction
- FlowCommandProcessor: StartFlow/CancelFlow processing (ADR-002)
"""

import logging
from typing import Any, cast

from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

from soni.core.types import DialogueState
from soni.dm.nodes.context_builder import DialogueContextBuilder
from soni.dm.nodes.flow_command_processor import FlowCommandProcessor
from soni.dm.nodes.history_converter import HistoryConverter
from soni.runtime.context import RuntimeContext

logger = logging.getLogger(__name__)


async def understand_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Process user input through NLU pipeline.

    Orchestrates:
    1. Context building
    2. NLU Pass 1 (intent detection)
    3. NLU Pass 2 (slot extraction)
    4. Flow command processing (ADR-002)
    """
    ctx = runtime.context
    messages = state.get("messages", [])
    user_message = state.get("user_message", "")

    if not user_message:
        return {"commands": []}

    # 1. Prepare context and history
    history = HistoryConverter.to_nlu_format(messages)
    context_builder = DialogueContextBuilder(ctx)
    dialogue_context = context_builder.build(state)

    # 2. PASS 1: Intent detection
    try:
        nlu_result = await ctx.nlu_provider.acall(user_message, dialogue_context, history)
        commands = list(nlu_result.commands)
    except Exception as e:
        logger.error(f"NLU Pass 1 failed: {e}", exc_info=True)
        return {"commands": []}

    # 3. PASS 2: Slot extraction (only when StartFlow detected)
    # Per design: Pass 2 runs only for StartFlow to extract slots from the initial message.
    # When a flow is already active, Pass 1 should extract slots using expected_slot context.
    start_flow_cmd = next(
        (cmd for cmd in commands if getattr(cmd, "type", None) == "start_flow"), None
    )

    if start_flow_cmd:
        flow_name = cast(str, getattr(start_flow_cmd, "flow_name", None))
        if flow_name:
            slot_definitions = context_builder.get_slot_definitions(flow_name)
            logger.debug(
                f"SlotExtractor: flow={flow_name}, definitions={len(slot_definitions)}, "
                f"slots={[s.name for s in slot_definitions]}"
            )
            if slot_definitions:
                try:
                    slot_commands = await ctx.slot_extractor.acall(user_message, slot_definitions)
                    logger.debug(f"SlotExtractor extracted: {slot_commands}")
                    commands.extend(slot_commands)
                except Exception as e:
                    logger.error(f"Slot extraction failed: {e}", exc_info=True)

    # 4. Process flow commands (ADR-002)
    processor = FlowCommandProcessor(ctx.flow_manager, ctx.config)
    remaining_commands, updates = processor.process_commands(commands, state)

    return {
        **updates,
        "commands": remaining_commands,
        "messages": [HumanMessage(content=user_message)],
    }
