## Task: 008 - Unify Pattern Handler Return Types with CommandResult

**ID de tarea:** 008
**Hito:** 2 - Quality Improvements
**Dependencias:** Ninguna
**Duración estimada:** 4 horas
**Prioridad:** MEDIA

### Objetivo

Unificar los tipos de retorno de los pattern handlers con los command handlers, haciendo que ambos retornen `CommandResult` en lugar de tener pattern handlers que retornan `tuple[dict, list[AIMessage]]`.

### Contexto

Actualmente hay inconsistencia en tipos de retorno:

**Command Handlers (command_registry.py:51-67):**
```python
@dataclass
class CommandResult:
    updates: dict[str, Any] = field(default_factory=dict)
    response_messages: list[AIMessage] = field(default_factory=list)
    should_reset_flow_state: bool = False
    applied_delta: bool = False

class CommandHandler(Protocol):
    async def handle(...) -> CommandResult:
        ...
```

**Pattern Handlers (dm/patterns/*.py):**
```python
class ClarificationHandler:
    async def handle(self, cmd, state, context) -> tuple[dict[str, Any], list[AIMessage]]:
        return {}, [AIMessage(content=explanation)]  # Tuple, not CommandResult!
```

**Problema en command_registry.py:229-248:**
```python
pattern_result = await dispatch_pattern_command(cmd, state, context)
if pattern_result:
    pattern_updates, messages = pattern_result  # Unpacks tuple
    for key, value in pattern_updates.items():
        if key != "should_reset_flow_state":
            result.updates[key] = value
    if pattern_updates.get("should_reset_flow_state"):
        result.should_reset_flow_state = True
```

Este código de adaptación es innecesario si los pattern handlers retornaran `CommandResult`.

### Entregables

- [ ] Actualizar `PatternHandler` protocol para retornar `CommandResult`
- [ ] Refactorizar todos los pattern handlers (correction, cancellation, clarification, etc.)
- [ ] Simplificar `dispatch_pattern_command()` en command_registry.py
- [ ] Tests unitarios para cada pattern handler

### Implementación Detallada

#### Paso 1: Actualizar PatternHandler protocol

**Archivo a modificar:** `src/soni/dm/patterns/base.py`

**ANTES:**
```python
from typing import Any, Protocol
from langchain_core.messages import AIMessage

from soni.core.types import DialogueState, RuntimeContext


class PatternHandler(Protocol):
    """Protocol for pattern handlers."""

    async def handle(
        self,
        cmd: Any,
        state: DialogueState,
        context: RuntimeContext,
    ) -> tuple[dict[str, Any], list[AIMessage]]:
        """Handle a pattern command.

        Returns:
            Tuple of (state updates dict, response messages list)
        """
        ...
```

**DESPUÉS:**
```python
from typing import Any, Protocol

from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.command_registry import CommandResult  # Import CommandResult


class PatternHandler(Protocol):
    """Protocol for pattern handlers.

    Pattern handlers process dialogue patterns like corrections,
    cancellations, and clarifications. They return CommandResult
    for consistency with command handlers.
    """

    async def handle(
        self,
        cmd: Any,
        state: DialogueState,
        context: RuntimeContext,
    ) -> CommandResult:
        """Handle a pattern command.

        Returns:
            CommandResult with updates and response messages
        """
        ...
```

#### Paso 2: Refactorizar ClarificationHandler

**Archivo a modificar:** `src/soni/dm/patterns/clarification.py`

**ANTES:**
```python
class ClarificationHandler:
    async def handle(
        self,
        cmd: AskClarification,
        state: DialogueState,
        context: RuntimeContext,
    ) -> tuple[dict[str, Any], list[AIMessage]]:
        # ... generate explanation ...
        return {}, [AIMessage(content=explanation)]
```

**DESPUÉS:**
```python
from soni.dm.nodes.command_registry import CommandResult


class ClarificationHandler:
    async def handle(
        self,
        cmd: AskClarification,
        state: DialogueState,
        context: RuntimeContext,
    ) -> CommandResult:
        """Handle clarification request.

        Generates an explanation of what slot the system is asking for.
        """
        # ... generate explanation ...

        return CommandResult(
            response_messages=[AIMessage(content=explanation)],
            # No state updates for clarification
        )
```

#### Paso 3: Refactorizar CorrectionHandler

**Archivo a modificar:** `src/soni/dm/patterns/correction.py`

**ANTES:**
```python
class CorrectionHandler:
    async def handle(
        self,
        cmd: CorrectSlot,
        state: DialogueState,
        context: RuntimeContext,
    ) -> tuple[dict[str, Any], list[AIMessage]]:
        flow_manager = context.flow_manager
        delta = flow_manager.set_slot(state, cmd.slot, cmd.new_value)

        updates: dict[str, Any] = {}
        if delta:
            from soni.flow.manager import merge_delta
            merge_delta(updates, delta)

        return updates, [AIMessage(content=f"I've updated {cmd.slot} to {cmd.new_value}.")]
```

**DESPUÉS:**
```python
from soni.dm.nodes.command_registry import CommandResult
from soni.flow.manager import merge_delta


class CorrectionHandler:
    async def handle(
        self,
        cmd: CorrectSlot,
        state: DialogueState,
        context: RuntimeContext,
    ) -> CommandResult:
        """Handle slot correction.

        Updates the specified slot with the new value and confirms to user.
        """
        flow_manager = context.flow_manager
        delta = flow_manager.set_slot(state, cmd.slot, cmd.new_value)

        result = CommandResult(
            response_messages=[
                AIMessage(content=f"I've updated {cmd.slot} to {cmd.new_value}.")
            ],
        )

        if delta:
            merge_delta(result.updates, delta)
            result.applied_delta = True

        return result
```

#### Paso 4: Refactorizar CancellationHandler

**Archivo a modificar:** `src/soni/dm/patterns/cancellation.py`

**DESPUÉS:**
```python
from soni.dm.nodes.command_registry import CommandResult


class CancellationHandler:
    async def handle(
        self,
        cmd: CancelFlow,
        state: DialogueState,
        context: RuntimeContext,
    ) -> CommandResult:
        """Handle flow cancellation.

        Pops the current flow from stack and confirms cancellation.
        """
        flow_manager = context.flow_manager

        # Pop the current flow
        try:
            popped, delta = flow_manager.pop_flow(
                state, result=FlowContextState.CANCELLED
            )

            result = CommandResult(
                response_messages=[
                    AIMessage(content=f"I've cancelled the {popped['flow_name']} flow.")
                ],
                should_reset_flow_state=True,
            )

            merge_delta(result.updates, delta)
            result.applied_delta = True

            return result

        except FlowStackError:
            return CommandResult(
                response_messages=[
                    AIMessage(content="There's no active flow to cancel.")
                ],
            )
```

#### Paso 5: Simplificar dispatch_pattern_command

**Archivo a modificar:** `src/soni/dm/nodes/command_registry.py`

**ANTES (líneas 229-248):**
```python
async def dispatch_pattern_command(
    cmd: Command,
    state: DialogueState,
    context: RuntimeContext,
) -> tuple[dict[str, Any], list[AIMessage]] | None:
    handler = PATTERN_HANDLERS.get(type(cmd))
    if handler:
        return await handler.handle(cmd, state, context)
    return None

# En el código que llama:
pattern_result = await dispatch_pattern_command(cmd, state, context)
if pattern_result:
    pattern_updates, messages = pattern_result
    for key, value in pattern_updates.items():
        if key != "should_reset_flow_state":
            result.updates[key] = value
    if pattern_updates.get("should_reset_flow_state"):
        result.should_reset_flow_state = True
    result.response_messages.extend(messages)
```

**DESPUÉS:**
```python
async def dispatch_pattern_command(
    cmd: Command,
    state: DialogueState,
    context: RuntimeContext,
) -> CommandResult | None:
    """Dispatch a pattern command to its handler.

    Returns:
        CommandResult from the handler, or None if no handler found
    """
    handler = PATTERN_HANDLERS.get(type(cmd))
    if handler:
        return await handler.handle(cmd, state, context)
    return None

# En el código que llama (mucho más simple):
pattern_result = await dispatch_pattern_command(cmd, state, context)
if pattern_result:
    # Merge directly since both are CommandResult
    result.updates.update(pattern_result.updates)
    result.response_messages.extend(pattern_result.response_messages)
    if pattern_result.should_reset_flow_state:
        result.should_reset_flow_state = True
    if pattern_result.applied_delta:
        result.applied_delta = True
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/dm/patterns/test_pattern_handlers.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from soni.dm.nodes.command_registry import CommandResult
from soni.core.commands import CorrectSlot, CancelFlow, AskClarification


class TestPatternHandlerReturnTypes:
    """Tests to verify all pattern handlers return CommandResult."""

    @pytest.fixture
    def mock_context(self):
        """Create mock RuntimeContext."""
        context = MagicMock()
        context.flow_manager = MagicMock()
        context.flow_manager.set_slot = MagicMock(return_value=None)
        context.config = MagicMock()
        return context

    @pytest.fixture
    def mock_state(self):
        """Create mock DialogueState."""
        return {
            "flow_stack": [{"flow_id": "test", "flow_name": "test_flow"}],
            "flow_slots": {"test": {}},
            "waiting_for_slot": "amount",
        }

    @pytest.mark.asyncio
    async def test_clarification_handler_returns_command_result(
        self, mock_context, mock_state
    ):
        """Test that ClarificationHandler returns CommandResult."""
        from soni.dm.patterns.clarification import ClarificationHandler

        handler = ClarificationHandler()
        cmd = AskClarification(slot="amount")

        result = await handler.handle(cmd, mock_state, mock_context)

        assert isinstance(result, CommandResult)
        assert len(result.response_messages) > 0

    @pytest.mark.asyncio
    async def test_correction_handler_returns_command_result(
        self, mock_context, mock_state
    ):
        """Test that CorrectionHandler returns CommandResult."""
        from soni.dm.patterns.correction import CorrectionHandler

        handler = CorrectionHandler()
        cmd = CorrectSlot(slot="amount", new_value="100")

        result = await handler.handle(cmd, mock_state, mock_context)

        assert isinstance(result, CommandResult)

    @pytest.mark.asyncio
    async def test_cancellation_handler_returns_command_result(
        self, mock_context, mock_state
    ):
        """Test that CancellationHandler returns CommandResult."""
        from soni.dm.patterns.cancellation import CancellationHandler
        from soni.flow.manager import FlowDelta
        from soni.core.constants import FlowContextState

        # Setup mock for pop_flow
        mock_context.flow_manager.pop_flow = MagicMock(
            return_value=(
                {"flow_id": "test", "flow_name": "test_flow"},
                FlowDelta(flow_stack=[]),
            )
        )

        handler = CancellationHandler()
        cmd = CancelFlow()

        result = await handler.handle(cmd, mock_state, mock_context)

        assert isinstance(result, CommandResult)
        assert result.should_reset_flow_state is True


class TestDispatchPatternCommand:
    """Tests for dispatch_pattern_command function."""

    @pytest.mark.asyncio
    async def test_returns_command_result_for_known_pattern(self):
        """Test that dispatch returns CommandResult for known patterns."""
        from soni.dm.nodes.command_registry import dispatch_pattern_command

        # Mock state and context
        state = {"flow_stack": [], "flow_slots": {}}
        context = MagicMock()

        cmd = AskClarification(slot="test")

        result = await dispatch_pattern_command(cmd, state, context)

        assert result is None or isinstance(result, CommandResult)

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_command(self):
        """Test that dispatch returns None for unknown command types."""
        from soni.dm.nodes.command_registry import dispatch_pattern_command

        state = {"flow_stack": [], "flow_slots": {}}
        context = MagicMock()

        # Use a non-pattern command
        from soni.core.commands import StartFlow
        cmd = StartFlow(flow_name="test")

        result = await dispatch_pattern_command(cmd, state, context)

        assert result is None
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/dm/patterns/test_pattern_handlers.py -v
# Expected: FAILED (handlers return tuple, not CommandResult)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for pattern handler return types"
```

#### Green Phase: Make Tests Pass

See "Implementación Detallada" section.

**Verify tests pass:**
```bash
uv run pytest tests/unit/dm/patterns/test_pattern_handlers.py -v
# Expected: PASSED
```

**Commit:**
```bash
git add src/ tests/
git commit -m "refactor: unify pattern handler return types to CommandResult

- Update PatternHandler protocol to return CommandResult
- Refactor ClarificationHandler, CorrectionHandler, CancellationHandler
- Simplify dispatch_pattern_command
- Consistent return types between command and pattern handlers"
```

### Criterios de Éxito

- [ ] Todos los pattern handlers retornan `CommandResult`
- [ ] `PatternHandler` protocol actualizado
- [ ] `dispatch_pattern_command` simplificado
- [ ] Código de adaptación eliminado
- [ ] Todos los tests pasan
- [ ] Linting y type checking pasan

### Validación Manual

**Comandos para validar:**

```bash
# Verificar tipos
uv run mypy src/soni/dm/patterns/

# Ejecutar tests de patterns
uv run pytest tests/unit/dm/patterns/ -v

# Probar flujo completo con corrección
uv run soni chat --config examples/banking/soni.yaml
# Probar: "transfer 100 euros" luego "actually make it 200"
```

### Referencias

- `src/soni/dm/patterns/` - Pattern handlers
- `src/soni/dm/nodes/command_registry.py` - CommandResult definition
- Command Handler pattern en el mismo archivo

### Notas Adicionales

**Beneficios:**
- Código más consistente y fácil de entender
- Menos conversión de tipos
- Mejor soporte de IDE/type checking
- Facilita agregar nuevos patterns
