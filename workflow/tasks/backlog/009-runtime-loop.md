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
        self.flow_manager = FlowManager()
        self.du = SoniDU()
        self.graph = None
        self.checkpointer = None
    
    async def initialize(self) -> None:
        """Initialize the runtime (compile graph, setup checkpointer)."""
        # Context is passed at invoke time, not build time
        # but we need to pass a dummy or schema to builder if needed for validation
        orchestrator = OrchestratorGraph(self.config, RuntimeContext)
        self.graph = orchestrator.build().compile(
            checkpointer=self.checkpointer
        )
    
    async def process_message(
        self,
        message: str,
        user_id: str = "default",
    ) -> str:
        """Process a user message and return response."""
        if self.graph is None:
            await self.initialize()
        
        # Create context for this specific run
        context = RuntimeContext(
            flow_manager=self.flow_manager,
            du=self.du,
            config=self.config,
            # Add action_handler when implemented
        )
        
        config = {"configurable": {"thread_id": user_id}}
        
        # Get or create state
        state = await self._get_or_create_state(user_id)
        state["user_message"] = message
        state["turn_count"] += 1
        
        # Run graph
        result = await self.graph.ainvoke(
            state, 
            config=config,
            context=context,  # <-- Pass runtime context here
        )
        
        return result.get("last_response", "I don't understand.")
    
    async def _get_or_create_state(self, user_id: str) -> DialogueState:
        """Get existing state or create new one."""
        if self.checkpointer:
            # Try to load from checkpointer
            pass
        return create_empty_dialogue_state()
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        # Close checkpointer, etc
        pass
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
