## Task: 010 - Actions and Integration

**ID de tarea:** 010
**Hito:** 7 - Actions & Integration
**Dependencias:** 009
**Duración estimada:** 4 horas

### Objetivo

Implement ActionRegistry and ActionHandler, plus run E2E integration tests.

### Entregables

- [ ] `actions/registry.py` - ActionRegistry
- [ ] `actions/handler.py` - ActionHandler
- [ ] E2E test: flight booking flow
- [ ] E2E test: multi-turn conversation
- [ ] README update with examples

### Implementación Detallada

**Archivo:** `src/soni/actions/registry.py`

```python
"""Action registry for storing action handlers."""
from typing import Any, Callable, Awaitable

ActionFunc = Callable[..., Awaitable[dict[str, Any]]]


class ActionRegistry:
    """Registry for action handlers."""
    
    def __init__(self):
        self._actions: dict[str, ActionFunc] = {}
    
    def register(self, name: str) -> Callable[[ActionFunc], ActionFunc]:
        """Decorator to register an action."""
        def decorator(func: ActionFunc) -> ActionFunc:
            self._actions[name] = func
            return func
        return decorator
    
    def get(self, name: str) -> ActionFunc | None:
        """Get an action by name."""
        return self._actions.get(name)
    
    def list(self) -> list[str]:
        """List all registered actions."""
        return list(self._actions.keys())
```

**Archivo:** `src/soni/actions/handler.py`

```python
"""Action handler for executing registered actions."""
from typing import Any
from soni.actions.registry import ActionRegistry
from soni.core.errors import ActionError


class ActionHandler:
    """Handles action execution."""
    
    def __init__(self, registry: ActionRegistry):
        self.registry = registry
    
    async def execute(self, action_name: str, inputs: dict) -> dict:
        """Execute a registered action with validation."""
        action = self.registry.get(action_name)
        if not action:
            raise ActionError(f"Action '{action_name}' not found")

        # Validate arguments using inspection
        sig = inspect.signature(action)
        required = [
            p.name for p in sig.parameters.values() 
            if p.default == inspect.Parameter.empty 
            and p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        ]
        
        missing = [param for param in required if param not in inputs]
        if missing:
             raise ActionError(f"Action '{action_name}' missing inputs: {missing}")

        # Execute
        try:
            return await action(**inputs)
        except Exception as e:
            raise ActionError(f"Action execution failed: {e}")
```

### TDD Cycle

```python
# tests/e2e/test_booking_flow.py
class TestBookingFlowE2E:
    @pytest.mark.asyncio
    async def test_complete_booking_flow(self):
        """
        GIVEN a flight booking flow
        WHEN user completes all steps
        THEN booking is confirmed
        """
        # Arrange
        from soni import ConversationalFramework
        
        framework = ConversationalFramework()
        framework.load_flows("examples/flight_booking/soni.yaml")
        framework.compile()
        
        # Act
        r1 = await framework.run_async("Book a flight to Paris")
        r2 = await framework.run_async("From Madrid")
        r3 = await framework.run_async("Tomorrow")
        
        # Assert
        assert "Paris" in r3 or "flight" in r3.lower()
```

### Criterios de Éxito

- [ ] Actions can be registered
- [ ] Actions can be executed
- [ ] E2E booking flow works
- [ ] Multi-turn conversation works
- [ ] README updated
