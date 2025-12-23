# Task: HIG-002 - Orchestrator Module

**ID de tarea:** HIG-002
**Hito:** Human Input Gate Refactoring (ADR-002)
**Dependencias:** HIG-001
**Duración estimada:** 2-3 días

## Objetivo

Crear el módulo Orchestrator con componentes separados siguiendo SRP: RuntimeContext, CommandHandler pattern, CommandProcessor, SubgraphExecutor, PendingTaskHandler, y el nodo orchestrator.

## Contexto

El orchestrator es el cerebro de la nueva arquitectura. Reemplaza la lógica monolítica de `execute_flow_node.py` con componentes separados y testeables. Usa el patrón Command (OCP) para extensibilidad y RuntimeContext (DIP) de LangGraph para inyección de dependencias.

**Referencia:** [ADR-002](../analysis/ADR-002-Human-Input-Gate-Architecture.md) - Secciones 3.1-3.8

## Entregables

- [ ] Modificar `runtime/context.py` - Añadir RuntimeContext y SubgraphRegistry protocol
- [ ] Crear `dm/orchestrator/__init__.py`
- [ ] Crear `dm/orchestrator/commands.py` (CommandHandler ABC + StartFlow, CancelFlow, SetSlot handlers)
- [ ] Crear `dm/orchestrator/command_processor.py`
- [ ] Crear `dm/orchestrator/executor.py` (SubgraphExecutor con streaming)
- [ ] Crear `dm/orchestrator/task_handler.py` (PendingTaskHandler, TaskAction, TaskResult)
- [ ] Crear `dm/nodes/orchestrator.py` (thin coordinator)
- [ ] Crear `dm/routing.py` (route_after_orchestrator)
- [ ] Tests unitarios con NLU mockeado

---

## TDD Cycle (MANDATORY)

### Red Phase: Write Failing Tests

**Test file:** `tests/unit/dm/orchestrator/test_commands.py`

```python
"""Tests for CommandHandler pattern (OCP)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from soni.dm.orchestrator.commands import (
    CommandHandler,
    StartFlowHandler,
    CancelFlowHandler,
    SetSlotHandler,
    DEFAULT_HANDLERS,
)
from soni.flow.delta import FlowDelta


class TestStartFlowHandler:
    """Tests for StartFlowHandler."""

    def test_can_handle_start_flow_command(self):
        """Test that handler recognizes start_flow commands."""
        # Arrange
        handler = StartFlowHandler()
        command = {"type": "start_flow", "flow_name": "transfer_funds"}

        # Act
        result = handler.can_handle(command)

        # Assert
        assert result is True

    def test_cannot_handle_other_commands(self):
        """Test that handler rejects non-start_flow commands."""
        # Arrange
        handler = StartFlowHandler()
        command = {"type": "cancel_flow"}

        # Act
        result = handler.can_handle(command)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_calls_push_flow(self):
        """Test that handle() calls flow_manager.push_flow()."""
        # Arrange
        handler = StartFlowHandler()
        command = {"type": "start_flow", "flow_name": "transfer_funds"}
        state = {"flow_stack": []}
        mock_fm = MagicMock()
        mock_fm.push_flow.return_value = FlowDelta(flow_stack=[{"flow_name": "transfer_funds"}])

        # Act
        delta = await handler.handle(command, state, mock_fm)

        # Assert
        mock_fm.push_flow.assert_called_once_with(state, "transfer_funds")
        assert delta.flow_stack is not None


class TestCancelFlowHandler:
    """Tests for CancelFlowHandler."""

    def test_can_handle_cancel_flow_command(self):
        """Test that handler recognizes cancel_flow commands."""
        # Arrange
        handler = CancelFlowHandler()
        command = {"type": "cancel_flow"}

        # Act & Assert
        assert handler.can_handle(command) is True

    @pytest.mark.asyncio
    async def test_handle_calls_pop_flow(self):
        """Test that handle() calls flow_manager.pop_flow()."""
        # Arrange
        handler = CancelFlowHandler()
        command = {"type": "cancel_flow"}
        state = {"flow_stack": [{"flow_name": "transfer_funds"}]}
        mock_fm = MagicMock()
        mock_fm.pop_flow.return_value = FlowDelta(flow_stack=[])

        # Act
        delta = await handler.handle(command, state, mock_fm)

        # Assert
        mock_fm.pop_flow.assert_called_once_with(state)


class TestSetSlotHandler:
    """Tests for SetSlotHandler."""

    def test_can_handle_set_slot_command(self):
        """Test that handler recognizes set_slot commands."""
        # Arrange
        handler = SetSlotHandler()
        command = {"type": "set_slot", "slot_name": "amount", "slot_value": "500"}

        # Act & Assert
        assert handler.can_handle(command) is True

    @pytest.mark.asyncio
    async def test_handle_calls_set_slot(self):
        """Test that handle() calls flow_manager.set_slot()."""
        # Arrange
        handler = SetSlotHandler()
        command = {"type": "set_slot", "slot_name": "amount", "slot_value": "500"}
        state = {}
        mock_fm = MagicMock()
        mock_fm.set_slot.return_value = FlowDelta(flow_slots={"amount": "500"})

        # Act
        delta = await handler.handle(command, state, mock_fm)

        # Assert
        mock_fm.set_slot.assert_called_once_with(state, "amount", "500")


class TestDefaultHandlers:
    """Tests for DEFAULT_HANDLERS list."""

    def test_default_handlers_contains_all_types(self):
        """Test that DEFAULT_HANDLERS has all required handlers."""
        # Arrange & Act
        handler_types = [type(h) for h in DEFAULT_HANDLERS]

        # Assert
        assert StartFlowHandler in handler_types
        assert CancelFlowHandler in handler_types
        assert SetSlotHandler in handler_types
```

**Test file:** `tests/unit/dm/orchestrator/test_command_processor.py`

```python
"""Tests for CommandProcessor (SRP)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from soni.dm.orchestrator.command_processor import CommandProcessor
from soni.dm.orchestrator.commands import DEFAULT_HANDLERS
from soni.flow.delta import FlowDelta


class TestCommandProcessor:
    """Tests for CommandProcessor."""

    @pytest.mark.asyncio
    async def test_process_empty_commands_returns_empty_delta(self):
        """Test that processing no commands returns empty delta."""
        # Arrange
        processor = CommandProcessor(DEFAULT_HANDLERS)
        mock_fm = MagicMock()

        # Act
        delta = await processor.process(commands=[], state={}, flow_manager=mock_fm)

        # Assert
        assert delta.flow_stack is None
        assert delta.flow_slots is None

    @pytest.mark.asyncio
    async def test_process_delegates_to_correct_handler(self):
        """Test that commands are routed to correct handlers."""
        # Arrange
        processor = CommandProcessor(DEFAULT_HANDLERS)
        commands = [{"type": "start_flow", "flow_name": "check_balance"}]
        state = {"flow_stack": []}
        mock_fm = MagicMock()
        mock_fm.push_flow.return_value = FlowDelta(
            flow_stack=[{"flow_name": "check_balance", "flow_id": "test_id"}]
        )

        # Act
        delta = await processor.process(commands, state, mock_fm)

        # Assert
        mock_fm.push_flow.assert_called_once()
        assert delta.flow_stack is not None

    @pytest.mark.asyncio
    async def test_process_handles_multiple_commands(self):
        """Test that multiple commands are all processed."""
        # Arrange
        processor = CommandProcessor(DEFAULT_HANDLERS)
        commands = [
            {"type": "start_flow", "flow_name": "transfer"},
            {"type": "set_slot", "slot_name": "amount", "slot_value": "100"},
        ]
        mock_fm = MagicMock()
        mock_fm.push_flow.return_value = FlowDelta(flow_stack=[])
        mock_fm.set_slot.return_value = FlowDelta(flow_slots={"amount": "100"})

        # Act
        delta = await processor.process(commands, {}, mock_fm)

        # Assert
        assert mock_fm.push_flow.called
        assert mock_fm.set_slot.called
```

**Test file:** `tests/unit/dm/orchestrator/test_task_handler.py`

```python
"""Tests for PendingTaskHandler (SRP)."""
import pytest

from soni.core.pending_task import collect, confirm, inform
from soni.core.message_sink import BufferedMessageSink
from soni.dm.orchestrator.task_handler import (
    PendingTaskHandler,
    TaskAction,
    TaskResult,
)


class TestPendingTaskHandler:
    """Tests for PendingTaskHandler."""

    @pytest.mark.asyncio
    async def test_handle_collect_returns_interrupt(self):
        """Test that CollectTask always triggers interrupt."""
        # Arrange
        sink = BufferedMessageSink()
        handler = PendingTaskHandler(sink)
        task = collect(prompt="Enter amount", slot="amount")

        # Act
        result = await handler.handle(task)

        # Assert
        assert result.action == TaskAction.INTERRUPT
        assert result.task == task
        assert sink.messages == []  # Collect doesn't send message

    @pytest.mark.asyncio
    async def test_handle_confirm_returns_interrupt(self):
        """Test that ConfirmTask always triggers interrupt."""
        # Arrange
        sink = BufferedMessageSink()
        handler = PendingTaskHandler(sink)
        task = confirm(prompt="Proceed?")

        # Act
        result = await handler.handle(task)

        # Assert
        assert result.action == TaskAction.INTERRUPT
        assert result.task == task

    @pytest.mark.asyncio
    async def test_handle_inform_without_wait_sends_and_continues(self):
        """Test that InformTask without wait sends message and continues."""
        # Arrange
        sink = BufferedMessageSink()
        handler = PendingTaskHandler(sink)
        task = inform(prompt="Your balance is $1,234")

        # Act
        result = await handler.handle(task)

        # Assert
        assert result.action == TaskAction.CONTINUE
        assert sink.messages == ["Your balance is $1,234"]

    @pytest.mark.asyncio
    async def test_handle_inform_with_wait_sends_and_interrupts(self):
        """Test that InformTask with wait_for_ack sends message and interrupts."""
        # Arrange
        sink = BufferedMessageSink()
        handler = PendingTaskHandler(sink)
        task = inform(prompt="Transfer complete!", wait_for_ack=True)

        # Act
        result = await handler.handle(task)

        # Assert
        assert result.action == TaskAction.INTERRUPT
        assert result.task == task
        assert sink.messages == ["Transfer complete!"]
```

**Test file:** `tests/unit/dm/test_routing.py`

```python
"""Tests for routing functions."""
import pytest

from soni.core.pending_task import collect, confirm, inform
from soni.dm.routing import route_after_orchestrator


class TestRouteAfterOrchestrator:
    """Tests for route_after_orchestrator function."""

    def test_returns_pending_task_when_task_exists(self):
        """Test that returns 'pending_task' when _pending_task is set."""
        # Arrange
        state = {"_pending_task": collect(prompt="Test", slot="test")}

        # Act
        result = route_after_orchestrator(state)

        # Assert
        assert result == "pending_task"

    def test_returns_end_when_no_task(self):
        """Test that returns 'end' when _pending_task is None."""
        # Arrange
        state = {"_pending_task": None}

        # Act
        result = route_after_orchestrator(state)

        # Assert
        assert result == "end"

    def test_returns_end_when_task_key_missing(self):
        """Test that returns 'end' when _pending_task key doesn't exist."""
        # Arrange
        state = {}

        # Act
        result = route_after_orchestrator(state)

        # Assert
        assert result == "end"
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/dm/orchestrator/ tests/unit/dm/test_routing.py -v
# Expected: FAILED (modules not implemented yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test(HIG-002): add failing tests for orchestrator module"
```

---

### Green Phase: Make Tests Pass

#### Paso 1: Modificar RuntimeContext

**Archivo:** `src/soni/runtime/context.py`

```python
"""Runtime context for LangGraph dependency injection."""
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from langgraph.types import CompiledGraph
    from soni.core.message_sink import MessageSink
    from soni.flow.manager import FlowManager


class SubgraphRegistry(Protocol):
    """Registry for compiled flow subgraphs."""

    def get(self, flow_name: str) -> "CompiledGraph":
        """Get compiled subgraph by flow name."""
        ...


@dataclass(frozen=True)
class RuntimeContext:
    """Immutable runtime context for LangGraph (DIP).

    Passed via context_schema when building the graph, accessed via
    runtime.context in nodes. Read-only during execution.
    """

    flow_manager: "FlowManager"
    subgraph_registry: SubgraphRegistry
    message_sink: "MessageSink"
    nlu_provider: "NLUProvider"  # type: ignore[name-defined]
    command_handlers: tuple["CommandHandler", ...] | None = None  # type: ignore[name-defined]
```

#### Paso 2: Crear commands.py

**Archivo:** `src/soni/dm/orchestrator/commands.py`

```python
"""Command handlers for orchestrator (OCP: Open for Extension)."""
from abc import ABC, abstractmethod
from typing import Any

from soni.flow.delta import FlowDelta


class CommandHandler(ABC):
    """Abstract handler for processing NLU commands."""

    @abstractmethod
    def can_handle(self, command: dict[str, Any]) -> bool:
        """Check if this handler can process the command."""
        ...

    @abstractmethod
    async def handle(
        self,
        command: dict[str, Any],
        state: dict[str, Any],
        flow_manager: Any,
    ) -> FlowDelta:
        """Process the command and return state changes."""
        ...


class StartFlowHandler(CommandHandler):
    """Handles StartFlow commands."""

    def can_handle(self, command: dict[str, Any]) -> bool:
        return command.get("type") == "start_flow"

    async def handle(self, command, state, flow_manager) -> FlowDelta:
        return flow_manager.push_flow(state, command["flow_name"])


class CancelFlowHandler(CommandHandler):
    """Handles CancelFlow commands."""

    def can_handle(self, command: dict[str, Any]) -> bool:
        return command.get("type") == "cancel_flow"

    async def handle(self, command, state, flow_manager) -> FlowDelta:
        return flow_manager.pop_flow(state)


class SetSlotHandler(CommandHandler):
    """Handles SetSlot commands."""

    def can_handle(self, command: dict[str, Any]) -> bool:
        return command.get("type") == "set_slot"

    async def handle(self, command, state, flow_manager) -> FlowDelta:
        return flow_manager.set_slot(
            state,
            command["slot_name"],
            command["slot_value"],
        )


DEFAULT_HANDLERS: list[CommandHandler] = [
    StartFlowHandler(),
    CancelFlowHandler(),
    SetSlotHandler(),
]
```

#### Paso 3: Crear command_processor.py

**Archivo:** `src/soni/dm/orchestrator/command_processor.py`

```python
"""Command processor for orchestrator (SRP)."""
from typing import Any

from soni.dm.orchestrator.commands import CommandHandler
from soni.flow.delta import FlowDelta, merge_deltas


class CommandProcessor:
    """Processes NLU commands and produces FlowDelta."""

    def __init__(self, handlers: list[CommandHandler]) -> None:
        self._handlers = handlers

    async def process(
        self,
        commands: list[dict[str, Any]],
        state: dict[str, Any],
        flow_manager: Any,
    ) -> FlowDelta:
        """Process all commands and return merged delta."""
        deltas: list[FlowDelta] = []

        for command in commands:
            for handler in self._handlers:
                if handler.can_handle(command):
                    delta = await handler.handle(command, state, flow_manager)
                    deltas.append(delta)
                    break

        return merge_deltas(deltas) if deltas else FlowDelta()
```

#### Paso 4: Crear task_handler.py

**Archivo:** `src/soni/dm/orchestrator/task_handler.py`

```python
"""Pending task handler for orchestrator (SRP)."""
from dataclasses import dataclass
from enum import Enum

from soni.core.pending_task import PendingTask, is_inform, requires_input
from soni.core.message_sink import MessageSink


class TaskAction(Enum):
    """What to do after handling a pending task."""

    CONTINUE = "continue"
    INTERRUPT = "interrupt"
    COMPLETE = "complete"


@dataclass
class TaskResult:
    """Result of handling a pending task."""

    action: TaskAction
    task: PendingTask | None = None


class PendingTaskHandler:
    """Handles pending tasks from subgraph outputs (SRP)."""

    def __init__(self, message_sink: MessageSink) -> None:
        self._sink = message_sink

    async def handle(self, task: PendingTask) -> TaskResult:
        """Process a pending task and determine next action."""
        if is_inform(task):
            await self._sink.send(task["prompt"])

            if requires_input(task):
                return TaskResult(action=TaskAction.INTERRUPT, task=task)
            return TaskResult(action=TaskAction.CONTINUE)

        # COLLECT or CONFIRM: always interrupt
        return TaskResult(action=TaskAction.INTERRUPT, task=task)
```

#### Paso 5: Crear routing.py

**Archivo:** `src/soni/dm/routing.py`

```python
"""Routing functions for orchestrator graph."""
from typing import Any, Literal


def route_after_orchestrator(state: dict[str, Any]) -> Literal["pending_task", "end"]:
    """Determine next step after orchestrator.

    If there's a pending task requiring user input, loop back to human_input_gate.
    Otherwise, end the graph execution.
    """
    pending = state.get("_pending_task")
    if pending:
        return "pending_task"
    return "end"
```

#### Paso 6: Crear __init__.py

**Archivo:** `src/soni/dm/orchestrator/__init__.py`

```python
"""Orchestrator module for Human Input Gate architecture."""
from soni.dm.orchestrator.commands import (
    CommandHandler,
    StartFlowHandler,
    CancelFlowHandler,
    SetSlotHandler,
    DEFAULT_HANDLERS,
)
from soni.dm.orchestrator.command_processor import CommandProcessor
from soni.dm.orchestrator.task_handler import (
    PendingTaskHandler,
    TaskAction,
    TaskResult,
)

__all__ = [
    "CommandHandler",
    "StartFlowHandler",
    "CancelFlowHandler",
    "SetSlotHandler",
    "DEFAULT_HANDLERS",
    "CommandProcessor",
    "PendingTaskHandler",
    "TaskAction",
    "TaskResult",
]
```

**Verify tests pass:**
```bash
uv run pytest tests/unit/dm/orchestrator/ tests/unit/dm/test_routing.py -v
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat(HIG-002): implement orchestrator module with Command pattern"
```

---

## Limpieza Progresiva

**En esta fase NO eliminar todavía `execute_flow.py`** - se eliminará en HIG-005 cuando todo esté integrado.

---

## Criterios de Éxito

- [ ] RuntimeContext tiene todos los campos necesarios
- [ ] CommandHandler pattern implementado y extensible
- [ ] CommandProcessor procesa múltiples comandos
- [ ] PendingTaskHandler distingue entre INFORM (sin wait) y otros
- [ ] route_after_orchestrator funciona correctamente
- [ ] Todos los tests pasan con mocks
- [ ] `uv run mypy src/soni/dm/orchestrator/` sin errores

## Validación Manual

```bash
# Verificar imports
uv run python -c "from soni.dm.orchestrator import CommandProcessor, PendingTaskHandler; print('OK')"

# Verificar tests
uv run pytest tests/unit/dm/orchestrator/ -v

# Verificar tipos
uv run mypy src/soni/dm/orchestrator/
```

## Referencias

- [ADR-002](../analysis/ADR-002-Human-Input-Gate-Architecture.md) - Secciones 3.1-3.8
