## Task: 009 - Runtime Loop

**ID de tarea:** 009
**Hito:** 6 - Runtime
**Dependencias:** 007, 008
**Duración estimada:** 6 horas

### Objetivo

Implement RuntimeLoop - the main entry point for processing messages.

### Entregables

- [ ] `runtime/loop.py` - RuntimeLoop class
- [ ] `runtime/checkpointer.py` - Checkpointer factory
- [ ] Message processing with state persistence
- [ ] Multi-user support
- [ ] Cleanup/resource management

### Implementación Detallada

**Archivo:** `src/soni/runtime/loop.py`

```python
"""Runtime loop for dialogue processing."""
import asyncio
from langgraph.checkpoint.base import BaseCheckpointSaver
from soni.core.config import SoniConfig
from soni.core.types import DialogueState, create_empty_dialogue_state
from soni.dm.orchestrator import OrchestratorGraph
from soni.flow.manager import FlowManager
from soni.du.modules import SoniDU


class RuntimeLoop:
    """Main runtime for processing dialogue messages."""
    
    def __init__(self, config: SoniConfig):
        self.config = config
        # Lazy initialization for everything
        self.flow_manager: FlowManager | None = None
        self.du: SoniDU | None = None
        self.graph: CompiledGraph | None = None
        self.checkpointer: BaseCheckpointSaver | None = None
    
    async def initialize(self) -> None:
        """Initialize all components."""
        self.flow_manager = FlowManager()
        self.du = SoniDU(use_cot=True)
        
        # Use builder to compile graph
        context = {"flow_manager": self.flow_manager} # passed to builder, not graph invoke
        self.graph = build_orchestrator(self.config, context)

    async def process_message(self, message: str, user_id: str = "default") -> str:
        if self.graph is None:
            await self.initialize()

        # Create runtime context for this request
        context = RuntimeContext(
            flow_manager=self.flow_manager,
            du=self.du,
            config=self.config
        )

        config = {"configurable": {"thread_id": user_id}}
        state = await self._get_or_create_state(user_id)
        state["user_message"] = message
        state["turn_count"] += 1
        
        result = await self.graph.ainvoke(
            state, 
            config=config,
            context=context
        )
        return result.get("last_response", "I don't understand.")

    async def _get_or_create_state(self, user_id: str) -> DialogueState:
        """Get existing state or create new one."""
        # TODO: Implement actual checkpoint loading
        # For now, always fresh state if not using persistent checkpointer
        return create_empty_dialogue_state()
```

### TDD Cycle

```python
# tests/unit/runtime/test_loop.py
class TestRuntimeLoop:
    @pytest.mark.asyncio
    async def test_process_message_returns_response(self):
        # Arrange
        config = SoniConfig(flows={
            "greet": FlowConfig(
                description="Greeting",
                steps=[StepConfig(step="say_hi", type="say", message="Hello!")]
            )
        })
        runtime = RuntimeLoop(config)
        
        # Act
        response = await runtime.process_message("Hi")
        
        # Assert
        assert response is not None

    @pytest.mark.asyncio
    async def test_state_persists_between_messages(self):
        # Arrange
        config = SoniConfig(flows={})
        runtime = RuntimeLoop(config)
        
        # Act
        await runtime.process_message("First message", user_id="user1")
        await runtime.process_message("Second message", user_id="user1")
        
        # Assert - turn_count should be 2
        state = await runtime._get_or_create_state("user1")
        # State should persist
```

### Criterios de Éxito

- [ ] process_message returns response
- [ ] State persists between turns
- [ ] Multi-user isolation works
- [ ] Cleanup releases resources
