"""Runtime loop for dialogue processing."""

from typing import Any

from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver

from soni.actions.handler import ActionHandler
from soni.actions.registry import ActionRegistry
from soni.core.config import SoniConfig
from soni.core.state import create_empty_dialogue_state
from soni.core.types import RuntimeContext
from soni.dm.builder import build_orchestrator
from soni.du.modules import SoniDU
from soni.flow.manager import FlowManager


class RuntimeLoop:
    """Main runtime for processing dialogue messages."""

    def __init__(
        self,
        config: SoniConfig,
        checkpointer: BaseCheckpointSaver | None = None,
        registry: ActionRegistry | None = None,
    ):
        self.config = config
        self.checkpointer = checkpointer

        # Registry can be passed or created during init
        self._initial_registry = registry

        # Lazy initialization
        self.flow_manager: FlowManager | None = None
        self.du: SoniDU | None = None
        self.action_registry: ActionRegistry | None = None
        self.action_handler: ActionHandler | None = None
        self.graph: Runnable | None = None

    async def initialize(self) -> None:
        """Initialize all components."""
        if self.graph:
            return

        self.flow_manager = FlowManager()
        self.du = SoniDU(use_cot=True)
        self.action_registry = self._initial_registry or ActionRegistry()
        self.action_handler = ActionHandler(self.action_registry)

        # Compile graph with checkpointer
        # Pass checkpointer only if provided
        self.graph = build_orchestrator(self.config, self.checkpointer)

    async def getattr_du(self):
        """Helper to expose DU for tests if needed."""
        return self.du

    async def process_message(self, message: str, user_id: str = "default") -> str:
        """Process a user message and return response."""
        if not self.graph:
            await self.initialize()

        graph = self.graph
        if not graph:
            raise RuntimeError("Graph initialization failed")

        # Create runtime context for this request (Dependency Injection)
        # Note: Type hinting matches dataclass RuntimeContext
        context = RuntimeContext(
            flow_manager=self.flow_manager,  # type: ignore
            du=self.du,  # type: ignore
            action_handler=self.action_handler,  # type: ignore
            config=self.config,
        )

        run_config: dict[str, Any] = {"configurable": {"thread_id": user_id}}

        # Determine input state
        input_update: dict[str, Any] = {"user_message": message}
        input_payload: dict[str, Any]

        current_state = await self.get_state(user_id)
        if not current_state:
            # Initialize fresh state
            init_state = create_empty_dialogue_state()
            init_state.update(input_update)
            init_state["turn_count"] = 1
            input_payload = init_state
        else:
            # Just update message
            input_payload = input_update
            # We manually check turn count? Or graph does? graph doesn't auto-increment turn count.
            # So we should increment it.
            # But 'current_state' is a snapshot.
            if "turn_count" in current_state:
                input_payload["turn_count"] = int(current_state["turn_count"]) + 1
            else:
                input_payload["turn_count"] = 1

        # Inject context via configurable (robust pattern)
        run_config["configurable"]["runtime_context"] = context

        result = await graph.ainvoke(input_payload, config=run_config)

        # Extract response
        # Result is the final state.
        last_response = result.get("last_response")
        messages = result.get("messages", [])

        if last_response:
            return last_response
        elif messages and hasattr(messages[-1], "content"):
            return messages[-1].content

        return "I don't understand."

    async def get_state(self, user_id: str) -> dict[str, Any] | None:
        """Get current state snapshot."""
        if not self.graph:
            return None

        config = {"configurable": {"thread_id": user_id}}
        try:
            # Get state snapshot
            # graph.get_state(config) returns StateSnapshot
            snapshot = await self.graph.aget_state(config)
            if snapshot and snapshot.values:
                return dict(snapshot.values)
        except Exception:
            return None
        return None
