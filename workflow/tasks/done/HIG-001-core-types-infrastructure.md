# Task: HIG-001 - Core Types & Infrastructure

**ID de tarea:** HIG-001
**Hito:** Human Input Gate Refactoring (ADR-002)
**Dependencias:** Ninguna
**Duración estimada:** 1-2 días

## Objetivo

Crear los tipos base (`PendingTask`) y la infraestructura (`MessageSink`) necesarios para la nueva arquitectura Human Input Gate.

## Contexto

Esta tarea establece los cimientos para toda la refactorización. Los tipos `PendingTask` (usando union types por ISP) y `MessageSink` serán usados por todos los demás componentes. Sin esto, las demás tareas no pueden proceder.

**Referencia:** [ADR-002-Human-Input-Gate-Architecture.md](../analysis/ADR-002-Human-Input-Gate-Architecture.md)

## Entregables

- [ ] `src/soni/core/pending_task.py` - Union types (CollectTask, ConfirmTask, InformTask) + factories + guards
- [ ] `src/soni/core/message_sink.py` - MessageSink ABC + WebSocketMessageSink + BufferedMessageSink
- [ ] Modificar `src/soni/core/state.py` - Añadir `_pending_task` a DialogueState
- [ ] Tests unitarios para todos los componentes
- [ ] Eliminar código obsoleto relacionado

---

## TDD Cycle (MANDATORY)

### Red Phase: Write Failing Tests

**Test file:** `tests/unit/core/test_pending_task.py`

```python
"""Tests for PendingTask types and factories."""
import pytest
from typing import get_args

from soni.core.pending_task import (
    CollectTask,
    ConfirmTask,
    InformTask,
    PendingTask,
    collect,
    confirm,
    inform,
    is_collect,
    is_confirm,
    is_inform,
    requires_input,
)


class TestCollectFactory:
    """Tests for collect() factory function."""

    def test_collect_creates_correct_type(self):
        """Test that collect() creates a CollectTask with correct type literal."""
        # Arrange
        prompt = "What is your account number?"
        slot = "account_number"

        # Act
        task = collect(prompt=prompt, slot=slot)

        # Assert
        assert task["type"] == "collect"
        assert task["prompt"] == prompt
        assert task["slot"] == slot

    def test_collect_with_options(self):
        """Test that collect() includes options when provided."""
        # Arrange
        options = ["checking", "savings"]

        # Act
        task = collect(prompt="Select account", slot="account_type", options=options)

        # Assert
        assert task["options"] == options

    def test_collect_with_metadata(self):
        """Test that collect() includes metadata when provided."""
        # Arrange
        metadata = {"expected_format": "8 digits"}

        # Act
        task = collect(prompt="Enter PIN", slot="pin", metadata=metadata)

        # Assert
        assert task["metadata"] == metadata


class TestConfirmFactory:
    """Tests for confirm() factory function."""

    def test_confirm_creates_correct_type(self):
        """Test that confirm() creates a ConfirmTask with correct type literal."""
        # Arrange
        prompt = "Transfer $500. Proceed?"

        # Act
        task = confirm(prompt=prompt)

        # Assert
        assert task["type"] == "confirm"
        assert task["prompt"] == prompt
        assert task["options"] == ["yes", "no"]  # Default options

    def test_confirm_with_custom_options(self):
        """Test that confirm() uses custom options when provided."""
        # Arrange
        options = ["yes", "no", "cancel"]

        # Act
        task = confirm(prompt="Confirm?", options=options)

        # Assert
        assert task["options"] == options


class TestInformFactory:
    """Tests for inform() factory function."""

    def test_inform_creates_correct_type(self):
        """Test that inform() creates an InformTask with correct type literal."""
        # Arrange
        prompt = "Your balance is $1,234"

        # Act
        task = inform(prompt=prompt)

        # Assert
        assert task["type"] == "inform"
        assert task["prompt"] == prompt
        assert task.get("wait_for_ack") is None  # Default: no wait

    def test_inform_with_wait_for_ack(self):
        """Test that inform() sets wait_for_ack when specified."""
        # Arrange & Act
        task = inform(prompt="Transfer complete!", wait_for_ack=True)

        # Assert
        assert task["wait_for_ack"] is True

    def test_inform_with_options(self):
        """Test that inform() includes options for acknowledgment."""
        # Arrange
        options = ["OK", "Got it"]

        # Act
        task = inform(prompt="Disclaimer", wait_for_ack=True, options=options)

        # Assert
        assert task["options"] == options


class TestTypeGuards:
    """Tests for type guard functions."""

    def test_is_collect_returns_true_for_collect_task(self):
        """Test is_collect() returns True for CollectTask."""
        # Arrange
        task = collect(prompt="Test", slot="test_slot")

        # Act & Assert
        assert is_collect(task) is True
        assert is_confirm(task) is False
        assert is_inform(task) is False

    def test_is_confirm_returns_true_for_confirm_task(self):
        """Test is_confirm() returns True for ConfirmTask."""
        # Arrange
        task = confirm(prompt="Test?")

        # Act & Assert
        assert is_confirm(task) is True
        assert is_collect(task) is False
        assert is_inform(task) is False

    def test_is_inform_returns_true_for_inform_task(self):
        """Test is_inform() returns True for InformTask."""
        # Arrange
        task = inform(prompt="Test")

        # Act & Assert
        assert is_inform(task) is True
        assert is_collect(task) is False
        assert is_confirm(task) is False


class TestRequiresInput:
    """Tests for requires_input() function."""

    def test_collect_requires_input(self):
        """Test that CollectTask always requires input."""
        # Arrange
        task = collect(prompt="Test", slot="slot")

        # Act & Assert
        assert requires_input(task) is True

    def test_confirm_requires_input(self):
        """Test that ConfirmTask always requires input."""
        # Arrange
        task = confirm(prompt="Test?")

        # Act & Assert
        assert requires_input(task) is True

    def test_inform_without_wait_does_not_require_input(self):
        """Test that InformTask without wait_for_ack does not require input."""
        # Arrange
        task = inform(prompt="Test")

        # Act & Assert
        assert requires_input(task) is False

    def test_inform_with_wait_requires_input(self):
        """Test that InformTask with wait_for_ack requires input."""
        # Arrange
        task = inform(prompt="Test", wait_for_ack=True)

        # Act & Assert
        assert requires_input(task) is True
```

**Test file:** `tests/unit/core/test_message_sink.py`

```python
"""Tests for MessageSink interface and implementations."""
import pytest

from soni.core.message_sink import (
    MessageSink,
    BufferedMessageSink,
)


class TestBufferedMessageSink:
    """Tests for BufferedMessageSink implementation."""

    @pytest.mark.asyncio
    async def test_send_appends_message_to_buffer(self):
        """Test that send() appends message to internal buffer."""
        # Arrange
        sink = BufferedMessageSink()

        # Act
        await sink.send("Hello")
        await sink.send("World")

        # Assert
        assert sink.messages == ["Hello", "World"]

    @pytest.mark.asyncio
    async def test_buffer_starts_empty(self):
        """Test that buffer is empty initially."""
        # Arrange & Act
        sink = BufferedMessageSink()

        # Assert
        assert sink.messages == []

    @pytest.mark.asyncio
    async def test_clear_empties_buffer(self):
        """Test that clear() empties the message buffer."""
        # Arrange
        sink = BufferedMessageSink()
        await sink.send("Test")

        # Act
        sink.clear()

        # Assert
        assert sink.messages == []
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/core/test_pending_task.py tests/unit/core/test_message_sink.py -v
# Expected: FAILED (modules not implemented yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test(HIG-001): add failing tests for PendingTask and MessageSink"
```

---

### Green Phase: Make Tests Pass

#### Paso 1: Crear pending_task.py

**Archivo:** `src/soni/core/pending_task.py`

```python
"""PendingTask types for Human Input Gate architecture.

This module defines the core data structures that subgraphs return when they
need user input. Uses union types (ISP) instead of one generic TypedDict.
"""
from typing import Any, Literal, NotRequired, TypedDict


# ─────────────────────────────────────────────────────────────────
# Specific Task Types (ISP: each type has only the fields it needs)
# ─────────────────────────────────────────────────────────────────


class CollectTask(TypedDict):
    """Task that collects a slot value from the user."""

    type: Literal["collect"]
    prompt: str
    slot: str  # REQUIRED for collect
    options: NotRequired[list[str]]
    metadata: NotRequired[dict[str, Any]]


class ConfirmTask(TypedDict):
    """Task that asks user for confirmation (yes/no/cancel)."""

    type: Literal["confirm"]
    prompt: str
    options: list[str]  # REQUIRED
    metadata: NotRequired[dict[str, Any]]


class InformTask(TypedDict):
    """Task that displays information to the user."""

    type: Literal["inform"]
    prompt: str
    wait_for_ack: NotRequired[bool]
    options: NotRequired[list[str]]
    metadata: NotRequired[dict[str, Any]]


# Union type (discriminated union on "type" field)
PendingTask = CollectTask | ConfirmTask | InformTask


# ─────────────────────────────────────────────────────────────────
# Factory Functions
# ─────────────────────────────────────────────────────────────────


def collect(
    prompt: str,
    slot: str,
    *,
    options: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> CollectTask:
    """Create a CollectTask to gather a slot value from the user."""
    task: CollectTask = {"type": "collect", "prompt": prompt, "slot": slot}
    if options:
        task["options"] = options
    if metadata:
        task["metadata"] = metadata
    return task


def confirm(
    prompt: str,
    options: list[str] | None = None,
    *,
    metadata: dict[str, Any] | None = None,
) -> ConfirmTask:
    """Create a ConfirmTask to ask for user confirmation."""
    task: ConfirmTask = {
        "type": "confirm",
        "prompt": prompt,
        "options": options or ["yes", "no"],
    }
    if metadata:
        task["metadata"] = metadata
    return task


def inform(
    prompt: str,
    *,
    wait_for_ack: bool = False,
    options: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> InformTask:
    """Create an InformTask to display information to the user."""
    task: InformTask = {"type": "inform", "prompt": prompt}
    if wait_for_ack:
        task["wait_for_ack"] = True
    if options:
        task["options"] = options
    if metadata:
        task["metadata"] = metadata
    return task


# ─────────────────────────────────────────────────────────────────
# Type Guards
# ─────────────────────────────────────────────────────────────────


def is_collect(task: PendingTask) -> bool:
    """Check if task is a CollectTask."""
    return task["type"] == "collect"


def is_confirm(task: PendingTask) -> bool:
    """Check if task is a ConfirmTask."""
    return task["type"] == "confirm"


def is_inform(task: PendingTask) -> bool:
    """Check if task is an InformTask."""
    return task["type"] == "inform"


def requires_input(task: PendingTask) -> bool:
    """Check if this task requires user input (pauses flow)."""
    if task["type"] in ("collect", "confirm"):
        return True
    if task["type"] == "inform":
        return task.get("wait_for_ack", False)
    return False
```

#### Paso 2: Crear message_sink.py

**Archivo:** `src/soni/core/message_sink.py`

```python
"""MessageSink interface for real-time message delivery.

This module defines the abstract interface and implementations for
streaming messages to users during flow execution.
"""
from abc import ABC, abstractmethod


class MessageSink(ABC):
    """Interface for streaming messages to the user in real-time (DIP)."""

    @abstractmethod
    async def send(self, message: str) -> None:
        """Send a message to the user immediately."""
        ...


class BufferedMessageSink(MessageSink):
    """Buffers messages for testing or batch delivery."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        """Append message to buffer."""
        self.messages.append(message)

    def clear(self) -> None:
        """Clear the message buffer."""
        self.messages.clear()


class WebSocketMessageSink(MessageSink):
    """WebSocket-based real-time delivery."""

    def __init__(self, websocket: "WebSocket") -> None:  # type: ignore[name-defined]
        self._ws = websocket

    async def send(self, message: str) -> None:
        """Send message via WebSocket."""
        await self._ws.send_json({"type": "message", "content": message})
```

#### Paso 3: Modificar DialogueState

**Archivo:** `src/soni/core/state.py` (añadir campo)

```python
# Añadir a DialogueState:
from soni.core.pending_task import PendingTask

class DialogueState(TypedDict):
    # ... campos existentes ...

    # NEW: Pending task from subgraph (union type)
    _pending_task: NotRequired[PendingTask | None]
```

**Verify tests pass:**
```bash
uv run pytest tests/unit/core/test_pending_task.py tests/unit/core/test_message_sink.py -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat(HIG-001): implement PendingTask types and MessageSink"
```

---

### Refactor Phase

- Verificar que todos los imports son correctos
- Añadir `__all__` exports a los módulos
- Verificar type hints con mypy

**Commit:**
```bash
git add src/
git commit -m "refactor(HIG-001): add exports and improve types"
```

---

## Limpieza Progresiva

En esta fase **NO hay código obsoleto que eliminar** - estamos creando nuevos tipos.

---

## Criterios de Éxito

- [ ] `pending_task.py` exporta todos los tipos y funciones
- [ ] `message_sink.py` exporta MessageSink ABC e implementaciones
- [ ] DialogueState incluye `_pending_task`
- [ ] Todos los tests pasan
- [ ] `uv run ruff check src/soni/core/` sin errores
- [ ] `uv run mypy src/soni/core/` sin errores

## Validación Manual

```bash
# Verificar imports funcionan
uv run python -c "from soni.core.pending_task import collect, confirm, inform; print('OK')"
uv run python -c "from soni.core.message_sink import BufferedMessageSink; print('OK')"

# Verificar tests
uv run pytest tests/unit/core/test_pending_task.py tests/unit/core/test_message_sink.py -v

# Verificar linting
uv run ruff check src/soni/core/pending_task.py src/soni/core/message_sink.py
uv run mypy src/soni/core/pending_task.py src/soni/core/message_sink.py
```

## Referencias

- [ADR-002: Human Input Gate Architecture](../analysis/ADR-002-Human-Input-Gate-Architecture.md)
- Sección 5: PendingTask Data Structure (ISP)
- Sección 3.9: MessageSink Interface
