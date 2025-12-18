## Task: TASK-003 - CommandHandlerRegistry: Implementar OCP Correctamente

**ID de tarea:** 003
**Hito:** Architecture Improvements
**Dependencias:** Ninguna
**Duración estimada:** 4 horas
**Prioridad:** CRÍTICA

### Objetivo

Refactorizar CommandHandlerRegistry para que sea verdaderamente extensible sin modificación (Open/Closed Principle), agregar handlers faltantes, eliminar código muerto, y unificar el dispatch de comandos.

### Contexto

El análisis identificó múltiples problemas en `dm/nodes/command_registry.py`:

1. **OCP Violation:** Handlers hardcodeados en `__init__`:
```python
self._handlers = {
    StartFlow: StartFlowHandler(),
    SetSlot: SetSlotHandler(),
    # ... hardcoded
}
```

2. **Handlers Faltantes:** `CompleteFlow`, `ClearSlot`, `ChitChat` no tienen handlers

3. **Código Muerto:** `register()` method nunca se usa

4. **Dual Dispatch:** `PatternCommandHandler` llama a `dispatch_pattern_command()` creando doble nivel de dispatch

5. **Mutación de Estado:** Handlers mutan `state` directamente (violando patrón FlowDelta)

### Entregables

- [ ] Hacer registro de handlers data-driven (dict a nivel de módulo)
- [ ] Agregar handlers faltantes (CompleteFlow, ClearSlot, ChitChat)
- [ ] Eliminar método `register()` no usado
- [ ] Eliminar mutación de estado en handlers
- [ ] Unificar dispatch (eliminar PatternCommandHandler wrapper)
- [ ] Definir Protocol para CommandHandler interface

### Implementación Detallada

#### Paso 1: Definir Protocol para handlers

**Archivo a modificar:** `src/soni/dm/nodes/command_registry.py`

**Agregar al inicio del archivo:**
```python
from typing import Protocol, runtime_checkable
from dataclasses import dataclass, field

from soni.core.commands import (
    StartFlow,
    SetSlot,
    AffirmConfirmation,
    DenyConfirmation,
    CorrectSlot,
    CancelFlow,
    RequestClarification,
    HumanHandoff,
    CompleteFlow,
    ClearSlot,
    ChitChat,
    Command,
)


@dataclass
class CommandResult:
    """Result of handling a command."""

    updates: dict[str, Any] = field(default_factory=dict)
    messages: list[AIMessage] = field(default_factory=list)  # Typed!
    should_reset_flow_state: bool = False


@runtime_checkable
class CommandHandler(Protocol):
    """Protocol for command handlers - all handlers must implement this."""

    async def handle(
        self,
        cmd: Command,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        """Handle a command and return result.

        IMPORTANT: Handlers MUST NOT mutate state directly.
        All changes must be returned in CommandResult.updates.
        """
        ...
```

#### Paso 2: Refactorizar handlers para NO mutar estado

**Archivo a modificar:** `src/soni/dm/nodes/command_registry.py`

**Cambiar StartFlowHandler de:**
```python
class StartFlowHandler:
    async def handle(self, cmd, state, context, expected_slot) -> CommandResult:
        fm = context.flow_manager
        delta = await fm.handle_intent_change(state, cmd.flow_name)

        result = CommandResult(should_reset_flow_state=True)

        if delta:
            merge_delta(result.updates, delta)
            # REMOVE THIS - no state mutation
            if delta.flow_stack is not None:
                state["flow_stack"] = delta.flow_stack
            if delta.flow_slots is not None:
                state["flow_slots"] = delta.flow_slots

        return result
```

**A:**
```python
class StartFlowHandler:
    """Handler for StartFlow command."""

    async def handle(
        self,
        cmd: StartFlow,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        """Handle flow start - delegates to FlowManager.

        Does NOT mutate state - returns delta in updates.
        """
        fm = context.flow_manager
        delta = await fm.handle_intent_change(state, cmd.flow_name)

        result = CommandResult(should_reset_flow_state=True)

        if delta:
            merge_delta(result.updates, delta)
            # NO state mutation here - understand_node applies updates

        return result
```

**Hacer lo mismo para SetSlotHandler:**
```python
class SetSlotHandler:
    """Handler for SetSlot command."""

    async def handle(
        self,
        cmd: SetSlot,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        """Handle slot setting - delegates to FlowManager."""
        fm = context.flow_manager
        delta = fm.set_slot(state, cmd.slot, cmd.value)

        result = CommandResult()

        if delta:
            merge_delta(result.updates, delta)
            # NO state mutation

        # Reset flow state if this is the expected slot
        if cmd.slot == expected_slot:
            result.should_reset_flow_state = True

        return result
```

#### Paso 3: Agregar handlers faltantes

**Archivo a modificar:** `src/soni/dm/nodes/command_registry.py`

```python
class CompleteFlowHandler:
    """Handler for CompleteFlow command - marks flow as completed."""

    async def handle(
        self,
        cmd: CompleteFlow,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        """Handle flow completion."""
        fm = context.flow_manager

        # Pop current flow as completed
        popped, delta = fm.pop_flow(state, result=FlowContextState.COMPLETED)

        result = CommandResult()
        if delta:
            merge_delta(result.updates, delta)

        return result


class ClearSlotHandler:
    """Handler for ClearSlot command - clears a slot value."""

    async def handle(
        self,
        cmd: ClearSlot,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        """Handle slot clearing."""
        fm = context.flow_manager

        # Set slot to None to clear it
        delta = fm.set_slot(state, cmd.slot, None)

        result = CommandResult()
        if delta:
            merge_delta(result.updates, delta)

        return result


class ChitChatHandler:
    """Handler for ChitChat command - non-flow conversation."""

    async def handle(
        self,
        cmd: ChitChat,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        """Handle chitchat - generates friendly response."""
        from langchain_core.messages import AIMessage

        # Generate response for chitchat
        response = cmd.message or "I'm here to help! What would you like to do?"

        return CommandResult(
            messages=[AIMessage(content=response)],
        )
```

#### Paso 4: Hacer registro data-driven

**Archivo a modificar:** `src/soni/dm/nodes/command_registry.py`

**Mover handlers a dict a nivel de módulo:**
```python
# Module-level handler registry - extensible without modifying class
# To add a new handler: COMMAND_HANDLERS[NewCommandType] = NewHandler()

COMMAND_HANDLERS: dict[type[Command], CommandHandler] = {
    StartFlow: StartFlowHandler(),
    SetSlot: SetSlotHandler(),
    AffirmConfirmation: ConfirmationHandler(),
    DenyConfirmation: ConfirmationHandler(),
    CompleteFlow: CompleteFlowHandler(),
    ClearSlot: ClearSlotHandler(),
    ChitChat: ChitChatHandler(),
    # Pattern commands - delegated to pattern dispatcher
    CorrectSlot: PatternCommandHandler(),
    CancelFlow: PatternCommandHandler(),
    RequestClarification: PatternCommandHandler(),
    HumanHandoff: PatternCommandHandler(),
}


def register_command_handler(cmd_type: type[Command], handler: CommandHandler) -> None:
    """Register a handler for a command type.

    Use this to add custom handlers at runtime.

    Example:
        register_command_handler(MyCustomCommand, MyHandler())
    """
    if not isinstance(handler, CommandHandler):
        raise TypeError(f"Handler must implement CommandHandler protocol")
    COMMAND_HANDLERS[cmd_type] = handler
```

**Simplificar CommandHandlerRegistry:**
```python
class CommandHandlerRegistry:
    """Registry for command handlers - uses module-level COMMAND_HANDLERS."""

    def get_handler(self, cmd: Command) -> CommandHandler | None:
        """Get handler for a command type."""
        return COMMAND_HANDLERS.get(type(cmd))

    async def dispatch(
        self,
        cmd: Command,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult | None:
        """Dispatch command to appropriate handler.

        Returns:
            CommandResult if handled, None if no handler found.
        """
        handler = self.get_handler(cmd)

        if handler:
            return await handler.handle(cmd, state, context, expected_slot)

        # Log unhandled command with warning (not misleading debug)
        cmd_type = getattr(cmd, "type", type(cmd).__name__)
        logger.warning(f"No handler registered for command type: {cmd_type}")
        return None


# Singleton for convenience
_registry: CommandHandlerRegistry | None = None


def get_command_registry() -> CommandHandlerRegistry:
    """Get the global command registry singleton."""
    global _registry
    if _registry is None:
        _registry = CommandHandlerRegistry()
    return _registry
```

#### Paso 5: Actualizar understand_node para aplicar updates correctamente

**Archivo a modificar:** `src/soni/dm/nodes/understand.py`

**En el loop de procesamiento de comandos, asegurarse de aplicar updates al final:**
```python
# After all commands processed, ensure state updates are returned
for cmd in commands:
    result = await registry.dispatch(cmd, state, runtime_ctx, expected_slot)
    if result:
        # Accumulate updates - handlers don't mutate state directly
        updates.update(result.updates)
        response_messages.extend(result.messages)
        if result.should_reset_flow_state:
            should_reset_flow_state = True

# Apply accumulated deltas to state for subsequent commands in same turn
# This is the ONLY place state should be mutated
if "flow_stack" in updates:
    state["flow_stack"] = updates["flow_stack"]
if "flow_slots" in updates:
    state["flow_slots"] = updates["flow_slots"]
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/dm/nodes/test_command_registry.py`

```python
"""Tests for CommandHandlerRegistry."""

import pytest
from unittest.mock import Mock, AsyncMock

from soni.core.commands import (
    StartFlow, SetSlot, CompleteFlow, ClearSlot, ChitChat,
    AffirmConfirmation, DenyConfirmation,
)
from soni.dm.nodes.command_registry import (
    CommandHandlerRegistry,
    CommandResult,
    COMMAND_HANDLERS,
    register_command_handler,
    get_command_registry,
)


class TestCommandHandlerRegistry:
    """Test command registry functionality."""

    @pytest.fixture
    def registry(self):
        return CommandHandlerRegistry()

    @pytest.fixture
    def mock_context(self):
        ctx = Mock()
        ctx.flow_manager = Mock()
        ctx.flow_manager.handle_intent_change = AsyncMock(return_value=None)
        ctx.flow_manager.set_slot = Mock(return_value=None)
        ctx.flow_manager.pop_flow = Mock(return_value=(None, None))
        return ctx

    @pytest.fixture
    def empty_state(self):
        return {
            "flow_stack": [],
            "flow_slots": {},
            "messages": [],
        }


class TestHandlerRegistration:
    """Test handler registration."""

    def test_all_command_types_have_handlers(self):
        """Every command type should have a handler."""
        command_types = [
            StartFlow, SetSlot, CompleteFlow, ClearSlot, ChitChat,
            AffirmConfirmation, DenyConfirmation,
        ]

        for cmd_type in command_types:
            assert cmd_type in COMMAND_HANDLERS, f"Missing handler for {cmd_type}"

    def test_register_custom_handler(self):
        """Should be able to register custom handlers."""
        class CustomCommand:
            type = "custom"

        class CustomHandler:
            async def handle(self, cmd, state, context, expected_slot):
                return CommandResult()

        register_command_handler(CustomCommand, CustomHandler())

        assert CustomCommand in COMMAND_HANDLERS


class TestStartFlowHandler:
    """Test StartFlow command handling."""

    @pytest.fixture
    def registry(self):
        return CommandHandlerRegistry()

    @pytest.mark.asyncio
    async def test_does_not_mutate_state_directly(self, registry):
        """Handler should NOT mutate state - only return updates."""
        ctx = Mock()
        ctx.flow_manager.handle_intent_change = AsyncMock(return_value=Mock(
            flow_stack=[{"flow_name": "test"}],
            flow_slots={"id": {}},
        ))

        state = {"flow_stack": [], "flow_slots": {}}
        original_stack = state["flow_stack"]
        original_slots = state["flow_slots"]

        cmd = StartFlow(flow_name="test")
        result = await registry.dispatch(cmd, state, ctx, None)

        # State should NOT be mutated
        assert state["flow_stack"] is original_stack
        assert state["flow_slots"] is original_slots

        # Updates should be in result
        assert "flow_stack" in result.updates or "flow_slots" in result.updates


class TestCompleteFlowHandler:
    """Test CompleteFlow command handling."""

    @pytest.fixture
    def registry(self):
        return CommandHandlerRegistry()

    @pytest.mark.asyncio
    async def test_pops_current_flow(self, registry):
        """CompleteFlow should pop the current flow."""
        ctx = Mock()
        ctx.flow_manager.pop_flow = Mock(return_value=(
            {"flow_name": "completed"},
            Mock(flow_stack=[]),
        ))

        state = {"flow_stack": [{"flow_name": "test"}], "flow_slots": {}}
        cmd = CompleteFlow()

        result = await registry.dispatch(cmd, state, ctx, None)

        ctx.flow_manager.pop_flow.assert_called_once()


class TestChitChatHandler:
    """Test ChitChat command handling."""

    @pytest.fixture
    def registry(self):
        return CommandHandlerRegistry()

    @pytest.mark.asyncio
    async def test_returns_message(self, registry):
        """ChitChat should return a message."""
        ctx = Mock()
        state = {"flow_stack": [], "flow_slots": {}, "messages": []}
        cmd = ChitChat(message="Hello!")

        result = await registry.dispatch(cmd, state, ctx, None)

        assert len(result.messages) > 0
        assert "Hello" in result.messages[0].content or "help" in result.messages[0].content.lower()


class TestUnhandledCommands:
    """Test handling of unknown command types."""

    @pytest.fixture
    def registry(self):
        return CommandHandlerRegistry()

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_command(self, registry):
        """Unknown command types should return None."""
        class UnknownCommand:
            type = "unknown"

        ctx = Mock()
        state = {}

        result = await registry.dispatch(UnknownCommand(), state, ctx, None)

        assert result is None
```

#### Green Phase

Implement the changes as described above.

```bash
uv run pytest tests/unit/dm/nodes/test_command_registry.py -v
```

### Criterios de Éxito

- [ ] Todos los tipos de comando tienen handler registrado
- [ ] Handlers NO mutan `state` directamente
- [ ] `register_command_handler()` permite agregar handlers externos
- [ ] COMMAND_HANDLERS es extensible sin modificar clase
- [ ] Tests pasan
- [ ] `CompleteFlow`, `ClearSlot`, `ChitChat` tienen handlers funcionales

### Validación Manual

```bash
# Run full test suite
uv run pytest tests/ -v

# Verify no state mutation in handlers
grep -n "state\[" src/soni/dm/nodes/command_registry.py
# Should only show reads, not assignments
```

### Referencias

- Open/Closed Principle: https://en.wikipedia.org/wiki/Open%E2%80%93closed_principle
- Análisis original: CommandHandlerRegistry OCP violations
- core/commands.py: Definiciones de comandos

### Notas Adicionales

- La mutación de estado debe ocurrir SOLO en understand_node después de procesar todos los comandos
- PatternCommandHandler puede simplificarse eliminando el wrapper si COMMAND_HANDLERS incluye pattern handlers directamente
- Considerar logging estructurado para debugging de command dispatch
