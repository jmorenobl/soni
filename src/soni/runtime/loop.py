"""Runtime loop for dialogue processing."""
from typing import Any
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.runnables import Runnable


from soni.core.config import SoniConfig
from soni.core.types import DialogueState, RuntimeContex
from soni.core.state import create_empty_dialogue_state
from soni.dm.builder import build_orchestrator
from soni.flow.manager import FlowManager
from soni.du.modules import SoniDU


class ActionHandler:
    """Stub action handler."""
    async def execute(self, action_name: str, **kwargs) -> dict[str, Any]:
        return {"status": "executed", "action": action_name}


class RuntimeLoop:
    """Main runtime for processing dialogue messages."""

    def __init__(
        self,
        config: SoniConfig,
        checkpointer: BaseCheckpointSaver | None = None
    ):
        self.config = config
        self.checkpointer = checkpointer

        # Lazy initialization
        self.flow_manager: FlowManager | None = None
        self.du: SoniDU | None = None
        self.action_handler: ActionHandler | None = None
        self.graph: Runnable | None = None

    async def initialize(self) -> None:
        """Initialize all components."""
        if self.graph:
            return

        self.flow_manager = FlowManager()
        self.du = SoniDU(use_cot=True)
        self.action_handler = ActionHandler()

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

        # Create runtime context for this request (Dependency Injection)
        # Note: Type hinting matches dataclass RuntimeContex
        context = RuntimeContext(
            flow_manager=self.flow_manager,
            du=self.du,
            action_handler=self.action_handler,
            config=self.config
        )

        config = {"configurable": {"thread_id": user_id}}

        # Determine input state
        # If we have a checkpointer, LangGraph handles loading.
        # But we need to update 'user_message'.
        # If it's a new conversation, we need initial structure.

        input_update: dict[str, Any] = {"user_message": message}

        # If no checkpointer, we must provide full state every time?
        # Or we rely on graph holding state in memory for the run?
        # WITHOUT checkpointer, LangGraph is stateless between invokes unless we manage it.
        # But our RuntimeLoop is designed to be stateful via checkpointer.
        # If no checkpointer is passed, we assume ephemeral.
        # However, for 'test_state_persists', we rely on checkpointer.

        # For ephemeral runs (no checkpointer), we might need to recreate state or pass it back.
        # But LangGraph 'CompiledGraph' is standard.

        # Let's assume for now we just pass partial update and let reducers handle it?
        # But DialogueState fields need initialization.
        # We can fetch current state to check if initialized.

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
                input_payload["turn_count"] = current_state["turn_count"] + 1
            else:
                input_payload["turn_count"] = 1

        # Inject context via configurable (robust pattern)
        config["configurable"]["runtime_context"] = contex

        result = await self.graph.ainvoke(
             input_payload,
             config=config
        )

        # Extract response
        # Result is the final state.
        last_response = result.get("last_response")
        messages = result.get("messages", [])

        if last_response:
            return last_response
        elif messages and hasattr(messages[-1], "content"):
            return messages[-1].conten

        return "I don't understand."

    async def get_state(self, user_id: str) -> dict[str, Any] | None:
        """Get current state snapshot."""
        if not self.graph:
            return None

        config = {"configurable": {"thread_id": user_id}}
        try:
            # Get state snapsho
            # graph.get_state(config) returns StateSnapsho
            snapshot = await self.graph.aget_state(config)
            if snapshot and snapshot.values:
                return snapshot.values
        except Exception:
            return None
        return None
