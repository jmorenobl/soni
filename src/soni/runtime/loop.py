"""RuntimeLoop for M7 (ADR-002 compliant interrupt architecture)."""

import sys
from typing import TYPE_CHECKING, Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from soni.config.models import SoniConfig
from soni.core.state import create_empty_state
from soni.core.types import DialogueState
from soni.dm.builder import build_orchestrator, compile_all_subgraphs
from soni.du.modules import SoniDU
from soni.flow.manager import FlowManager
from soni.runtime.context import RuntimeContext

if TYPE_CHECKING:
    from soni.actions.registry import ActionRegistry


class RuntimeLoop:
    """Runtime loop for M7 with ADR-002 interrupt architecture.

    Uses LangGraph's native interrupt/resume mechanism for multi-turn flows.
    """

    def __init__(
        self,
        config: SoniConfig,
        checkpointer: BaseCheckpointSaver | None = None,
        action_registry: "ActionRegistry | None" = None,
    ) -> None:
        self.config = config
        self.checkpointer = checkpointer
        self._action_registry = action_registry
        self._graph: CompiledStateGraph[DialogueState, RuntimeContext, Any, Any] | None = None
        self._context: RuntimeContext | None = None

    async def __aenter__(self) -> "RuntimeLoop":
        """Initialize graphs, NLU modules, and action registry."""
        # Compile ALL subgraphs upfront (ADR-002)
        subgraphs = compile_all_subgraphs(self.config)

        # Create flow manager and NLU modules (two-pass)
        flow_manager = FlowManager()
        du = SoniDU.create_with_best_model()  # Pass 1: Intent detection

        from soni.du.slot_extractor import SlotExtractor

        slot_extractor = SlotExtractor.create_with_best_model()  # Pass 2: Slot extraction

        # Use provided registry or create empty one
        from soni.actions.registry import ActionRegistry

        action_registry = self._action_registry or ActionRegistry()

        # M8: Initialize rephraser if enabled
        rephraser = None
        if self.config.settings.rephrase_responses:
            from soni.du.rephraser import ResponseRephraser

            rephraser = ResponseRephraser.create_with_best_model()
            rephraser.tone = self.config.settings.rephrase_tone

        # ADR-002: Pass subgraphs to context
        self._context = RuntimeContext(
            config=self.config,
            flow_manager=flow_manager,
            du=du,
            slot_extractor=slot_extractor,
            action_registry=action_registry,
            subgraphs=subgraphs,
            rephraser=rephraser,  # M8: Response rephrasing
        )

        # Build orchestrator with checkpointer
        self._graph = build_orchestrator(checkpointer=self.checkpointer)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Cleanup."""
        pass

    async def process_message(self, message: str, user_id: str = "default") -> str:
        """Process a message and return response.

        With ADR-002 architecture:
        - First turn: Fresh invoke, may interrupt waiting for input
        - Subsequent turns: Resume from interrupt with user's response
        """
        if self._graph is None or self._context is None:
            raise RuntimeError("RuntimeLoop not initialized. Use 'async with' context.")

        # Thread config for persistence
        thread_id = f"thread_{user_id}"
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

        try:
            # Check for pending interrupts
            snapshot = None
            if self.checkpointer:
                snapshot = await self._graph.aget_state(config)
                if snapshot:
                    pass  # Resuming from interrupt

            # ADR-002: Resume if there are pending tasks (interrupt was called)
            if snapshot and snapshot.tasks:
                # CRITICAL: Process NLU BEFORE resuming to generate SetSlot commands
                # Without this, user's response (e.g. "checking") won't be parsed as slot value
                from soni.du.models import (
                    CommandInfo,
                    DialogueContext,
                    FlowInfo,
                    SlotDefinition,
                    SlotValue,
                )

                fm = self._context.flow_manager
                du = self._context.du
                slot_extractor = self._context.slot_extractor
                config_obj = self._context.config

                # Get current state from snapshot
                current_state = dict(snapshot.values) if snapshot.values else {}

                # Build context for NLU
                active_ctx = fm.get_active_context(current_state)
                active_flow = active_ctx["flow_name"] if active_ctx else None

                # Get expected slot from interrupt
                pending = current_state.get("_pending_prompt")
                expected_slot = pending.get("slot") if pending else None

                # Get slot definitions for active flow
                flow_slots_defs: list[SlotDefinition] = []
                if active_flow and active_flow in config_obj.flows:
                    from soni.config.models import CollectStepConfig

                    flow_config = config_obj.flows[active_flow]
                    for step in flow_config.steps:
                        if isinstance(step, CollectStepConfig):
                            flow_slots_defs.append(
                                SlotDefinition(
                                    name=step.slot,
                                    slot_type="string",
                                    description=step.message or f"Value for {step.slot}",
                                )
                            )

                # Get current slots
                current_slots: list[SlotValue] = []
                if active_ctx:
                    flow_id = active_ctx["flow_id"]
                    flow_slots_state = current_state.get("flow_slots", {})
                    if flow_slots_state:
                        slot_dict = flow_slots_state.get(flow_id, {})
                        for name, value in slot_dict.items():
                            if not name.startswith("_"):
                                current_slots.append(
                                    SlotValue(
                                        name=name, value=str(value) if value is not None else None
                                    )
                                )

                flows_info = [
                    FlowInfo(name=name, description=flow.description or name)
                    for name, flow in config_obj.flows.items()
                ]

                commands_info = [
                    CommandInfo(
                        command_type="set_slot",
                        description="Set a slot value when user provides information",
                        required_fields=["slot", "value"],
                    ),
                    CommandInfo(command_type="affirm", description="User confirms"),
                    CommandInfo(command_type="deny", description="User denies"),
                ]

                context_nlu = DialogueContext(
                    available_flows=flows_info,
                    available_commands=commands_info,
                    active_flow=active_flow,
                    flow_slots=flow_slots_defs,
                    current_slots=current_slots,
                    expected_slot=expected_slot,
                    conversation_state="collecting" if active_flow else "idle",
                )

                # Get history
                messages = current_state.get("messages", [])
                history = [
                    {
                        "role": "user" if hasattr(m, "type") and m.type == "human" else "assistant",
                        "content": m.content if hasattr(m, "content") else str(m),
                    }
                    for m in messages[-10:]
                ]

                # Run NLU
                try:
                    nlu_result = await du.acall(message, context_nlu, history)
                    commands = [
                        cmd.model_dump() if hasattr(cmd, "model_dump") else dict(cmd)
                        for cmd in nlu_result.commands
                    ]
                except Exception:
                    commands = []

                # Resume with commands in payload
                result = await self._graph.ainvoke(
                    Command(
                        resume=message,
                        update={
                            "commands": commands,
                            "user_message": message,
                        },
                    ),
                    config=config,
                    context=self._context,
                )
            else:
                # Fresh execution
                state = create_empty_state()
                state["user_message"] = message
                result = await self._graph.ainvoke(state, config=config, context=self._context)

            # Handle interrupt response (return prompt to user)
            if "__interrupt__" in result:
                interruption = result["__interrupt__"]
                val = interruption

                # Unwrap list/tuple (e.g. [Interrupt(...)])
                while isinstance(val, (list, tuple)) and val:
                    val = val[0]

                # Unwrap Interrupt object
                if hasattr(val, "value"):
                    val = val.value

                # Extract prompt from interrupt payload
                if isinstance(val, dict):
                    if "prompt" in val:
                        return str(val["prompt"])
                    if "response" in val:
                        return str(val["response"])
                return str(val) if val else ""

            if "_pending_responses" in result and result["_pending_responses"]:
                return "\n".join(result["_pending_responses"])

            return str(result.get("response") or "")

        except Exception:
            import traceback

            traceback.print_exc(file=sys.stderr)

            # Try to get response from snapshot if available
            if self.checkpointer:
                try:
                    snapshot = await self._graph.aget_state(config)
                    if snapshot and snapshot.values:
                        response = snapshot.values.get("response")
                        if response:
                            return str(response)
                except Exception:
                    pass

            raise
