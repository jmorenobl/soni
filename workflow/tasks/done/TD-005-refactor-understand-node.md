## Task: TD-005 - Refactor understand_node (SRP Violation)

**ID de tarea:** TD-005
**Fase:** Phase 2 - Structure
**Prioridad:** 🔴 HIGH
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Refactorizar `understand_node` de 264 líneas que viola el Principio de Responsabilidad Única (SRP) en clases y módulos separados con responsabilidades bien definidas.

### Contexto

`understand_node` actualmente hace demasiadas cosas:
1. Construye el contexto de diálogo (FlowInfo, CommandInfo)
2. Convierte formatos de historial de mensajes
3. Llama NLU Pass 1 (SoniDU)
4. Llama NLU Pass 2 (SlotExtractor)
5. Procesa comandos StartFlow/CancelFlow
6. Actualiza flow_stack

**Impacto:** Difícil de testear, modificar y debuggear. Cambios en un área pueden romper otras.

**Archivo afectado:** [dm/nodes/understand.py](file:///Users/jorge/Projects/Playground/soni/src/soni/dm/nodes/understand.py)

### Entregables

- [ ] Crear `dm/nodes/context_builder.py` - Clase `DialogueContextBuilder`
- [ ] Crear `dm/nodes/history_converter.py` - Clase `HistoryConverter`
- [ ] Crear `dm/nodes/flow_command_processor.py` - Procesador de StartFlow/CancelFlow
- [ ] Refactorizar `understand_node` como orquestador delgado (~50 LOC)
- [ ] Migrar tests existentes y añadir nuevos para cada componente
- [ ] Mantener la API externa sin cambios

### Implementación Detallada

#### Paso 1: Crear DialogueContextBuilder

**Archivo a crear:** `src/soni/dm/nodes/context_builder.py`

```python
"""Builder for constructing dialogue context for NLU."""

from typing import Any

from soni.core.types import DialogueState
from soni.core.context import RuntimeContext


class DialogueContextBuilder:
    """Constructs dialogue context for NLU processing.

    Follows SRP: only responsible for building context objects.
    """

    def __init__(self, context: RuntimeContext) -> None:
        self._context = context

    def build_flow_info(self, state: DialogueState) -> dict[str, Any]:
        """Build flow information for NLU context.

        Returns:
            Dict with active_flow, available_intents, expected_slot, etc.
        """
        flow_manager = self._context.flow_manager
        # ... extract logic from understand_node

    def build_command_info(self, state: DialogueState) -> dict[str, Any]:
        """Build command history information for NLU context.

        Returns:
            Dict with recent commands and their outcomes.
        """
        # ... extract logic from understand_node

    def build_full_context(self, state: DialogueState) -> dict[str, Any]:
        """Build complete dialogue context for NLU.

        Combines flow_info and command_info.
        """
        return {
            "flow_info": self.build_flow_info(state),
            "command_info": self.build_command_info(state),
        }
```

**Principios aplicados:**
- **SRP:** Solo construye contexto
- **OCP:** Nuevos tipos de contexto se añaden con nuevos métodos
- **DIP:** Depende de abstracciones (RuntimeContext)

#### Paso 2: Crear HistoryConverter

**Archivo a crear:** `src/soni/dm/nodes/history_converter.py`

```python
"""Converter for message history formats."""

from typing import Sequence

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from soni.core.types import DialogueState


class HistoryConverter:
    """Converts message history between formats.

    Handles conversion from LangGraph message format to formats
    expected by different NLU components.
    """

    @staticmethod
    def to_nlu_format(
        messages: Sequence[BaseMessage],
        max_history: int = 10
    ) -> list[dict[str, str]]:
        """Convert LangGraph messages to NLU input format.

        Args:
            messages: LangGraph message sequence
            max_history: Maximum number of messages to include

        Returns:
            List of dicts with 'role' and 'content' keys.
        """
        result: list[dict[str, str]] = []
        for msg in messages[-max_history:]:
            if isinstance(msg, HumanMessage):
                result.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                result.append({"role": "assistant", "content": msg.content})
        return result

    @staticmethod
    def get_last_user_message(state: DialogueState) -> str:
        """Extract the last user message from state.

        Returns:
            The content of the last human message.

        Raises:
            ValueError: If no user message found.
        """
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return str(msg.content)
        raise ValueError("No user message found in state")
```

**Principios aplicados:**
- **SRP:** Solo convierte formatos de mensajes
- **Pure functions:** Métodos estáticos sin effectos secundarios

#### Paso 3: Crear FlowCommandProcessor

**Archivo a crear:** `src/soni/dm/nodes/flow_command_processor.py`

```python
"""Processor for flow-related NLU commands."""

from typing import Any

from soni.core.commands import Command, StartFlow, CancelFlow
from soni.core.types import DialogueState
from soni.flow.manager import FlowManager, FlowDelta


class FlowCommandProcessor:
    """Processes flow-related commands from NLU.

    Handles StartFlow and CancelFlow commands, updating
    the flow stack appropriately.
    """

    def __init__(self, flow_manager: FlowManager) -> None:
        self._flow_manager = flow_manager

    def process(
        self,
        commands: list[Command],
        state: DialogueState,
    ) -> tuple[list[Command], FlowDelta | None]:
        """Process flow commands and return remaining commands with delta.

        Args:
            commands: List of NLU commands
            state: Current dialogue state

        Returns:
            Tuple of (non-flow commands, combined flow delta)
        """
        remaining: list[Command] = []
        deltas: list[FlowDelta] = []

        for cmd in commands:
            if isinstance(cmd, StartFlow):
                delta = self._flow_manager.push_flow(state, cmd.flow_name)
                if delta:
                    deltas.append(delta)
            elif isinstance(cmd, CancelFlow):
                delta = self._flow_manager.pop_flow(state)
                if delta:
                    deltas.append(delta)
            else:
                remaining.append(cmd)

        combined_delta = self._merge_deltas(deltas) if deltas else None
        return remaining, combined_delta

    def _merge_deltas(self, deltas: list[FlowDelta]) -> FlowDelta:
        """Merge multiple deltas into one."""
        from soni.core.types import merge_deltas
        return merge_deltas(deltas)
```

**Principios aplicados:**
- **SRP:** Solo procesa comandos de flujo
- **OCP:** Nuevo commands se manejan añadiendo elif branches
- **DIP:** Depende de FlowManager abstraction

#### Paso 4: Refactorizar understand_node

**Archivo a modificar:** `src/soni/dm/nodes/understand.py`

**Antes:** ~264 líneas con toda la lógica mezclada

**Después:** ~50-60 líneas como orquestador

```python
"""Understand node - NLU orchestrator."""

from typing import Any

from soni.core.types import DialogueState
from soni.core.context import RuntimeContext
from soni.dm.nodes.context_builder import DialogueContextBuilder
from soni.dm.nodes.history_converter import HistoryConverter
from soni.dm.nodes.flow_command_processor import FlowCommandProcessor
from soni.flow.manager import merge_delta


async def understand_node(
    state: DialogueState,
    context: RuntimeContext,
) -> dict[str, Any]:
    """Process user input through NLU pipeline.

    Orchestrates:
    1. Context building
    2. NLU Pass 1 (intent detection)
    3. NLU Pass 2 (slot extraction)
    4. Flow command processing
    """
    updates: dict[str, Any] = {}

    # Build context
    context_builder = DialogueContextBuilder(context)
    dialogue_context = context_builder.build_full_context(state)

    # Get user message
    user_message = HistoryConverter.get_last_user_message(state)
    history = HistoryConverter.to_nlu_format(state.get("messages", []))

    # NLU Pass 1: Intent detection
    nlu_result = await context.nlu_provider.acall(
        user_message,
        dialogue_context,
        history,
    )

    # NLU Pass 2: Slot extraction (if needed)
    commands = list(nlu_result.commands)
    if _needs_slot_extraction(commands):
        slot_commands = await context.slot_extractor.acall(
            user_message,
            _get_slot_definitions(context, state),
        )
        commands.extend(slot_commands)

    # Process flow commands
    processor = FlowCommandProcessor(context.flow_manager)
    remaining_commands, delta = processor.process(commands, state)

    # Build result
    updates["nlu_result"] = nlu_result.model_dump()
    updates["pending_commands"] = [c.model_dump() for c in remaining_commands]
    if delta:
        merge_delta(updates, delta)

    return updates


def _needs_slot_extraction(commands: list) -> bool:
    """Check if slot extraction pass is needed."""
    from soni.core.commands import StartFlow
    return any(isinstance(c, StartFlow) for c in commands)


def _get_slot_definitions(context: RuntimeContext, state: DialogueState) -> list:
    """Get slot definitions for active flow."""
    # ... implementation
```

### TDD Cycle

#### Red Phase: Write Failing Tests

**Test files:**
- `tests/unit/dm/nodes/test_context_builder.py`
- `tests/unit/dm/nodes/test_history_converter.py`
- `tests/unit/dm/nodes/test_flow_command_processor.py`

```python
# tests/unit/dm/nodes/test_context_builder.py
import pytest
from soni.dm.nodes.context_builder import DialogueContextBuilder


class TestDialogueContextBuilder:
    """Tests for DialogueContextBuilder."""

    def test_build_flow_info_with_active_flow(self):
        """Test flow info includes active flow details."""
        # Arrange: mock context with active flow
        # Act
        # Assert: flow_info contains expected keys
        pass

    def test_build_flow_info_without_active_flow(self):
        """Test flow info when no flow active."""
        pass

    def test_build_command_info_returns_recent_commands(self):
        """Test command info includes recent command history."""
        pass


# tests/unit/dm/nodes/test_history_converter.py
class TestHistoryConverter:
    """Tests for HistoryConverter."""

    def test_to_nlu_format_converts_messages(self):
        """Test conversion of LangGraph messages to NLU format."""
        pass

    def test_to_nlu_format_respects_max_history(self):
        """Test that only max_history messages are included."""
        pass

    def test_get_last_user_message_finds_message(self):
        """Test extraction of last user message."""
        pass

    def test_get_last_user_message_raises_when_none(self):
        """Test ValueError when no user message exists."""
        pass


# tests/unit/dm/nodes/test_flow_command_processor.py
class TestFlowCommandProcessor:
    """Tests for FlowCommandProcessor."""

    def test_process_start_flow_pushes_to_stack(self):
        """Test StartFlow command pushes flow to stack."""
        pass

    def test_process_cancel_flow_pops_from_stack(self):
        """Test CancelFlow command pops from stack."""
        pass

    def test_process_returns_non_flow_commands(self):
        """Test that non-flow commands are returned unchanged."""
        pass
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/dm/nodes/test_context_builder.py \
    tests/unit/dm/nodes/test_history_converter.py \
    tests/unit/dm/nodes/test_flow_command_processor.py -v
# Expected: FAILED (modules don't exist yet)
```

#### Green Phase: Make Tests Pass

Implement the classes as described in Implementación Detallada.

```bash
uv run pytest tests/unit/dm/nodes/ -v
# Expected: PASSED ✅
```

#### Refactor Phase: Improve Design

- Add comprehensive docstrings
- Optimize any inefficient code
- Ensure type hints are complete
- Tests must still pass!

### Criterios de Éxito

- [ ] `understand_node` reduced to ~50-60 LOC
- [ ] All new classes have single responsibility
- [ ] All existing integration tests pass
- [ ] No changes to external API
- [ ] Code coverage maintained or improved
- [ ] `uv run mypy src/soni/dm/nodes/` passes
- [ ] `uv run ruff check src/soni/dm/nodes/` passes

### Validación Manual

**Comandos para validar:**

```bash
# Verify file sizes
wc -l src/soni/dm/nodes/understand.py
wc -l src/soni/dm/nodes/context_builder.py
wc -l src/soni/dm/nodes/history_converter.py
wc -l src/soni/dm/nodes/flow_command_processor.py

# Run all tests
uv run pytest tests/ -v

# Run integration test
uv run soni chat --config examples/banking/domain

# Type check
uv run mypy src/soni/dm/nodes/

# Lint
uv run ruff check src/soni/dm/nodes/
```

**Resultado esperado:**
- understand.py < 70 LOC
- All tests pass
- Chat functionality works as before

### Referencias

- [Technical Debt Analysis](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/technical-debt-analysis.md#L22-48)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Martin Fowler - Extract Class](https://refactoring.com/catalog/extractClass.html)

### Notas Adicionales

- Mantener backward compatibility - la función `understand_node` debe seguir exportándose
- Considerar si algunas clases deberían ser protocolos para testing
- Los helpers extraídos pueden ser reutilizados en otros nodos
- El refactoring debe ser incremental - commit por cada clase nueva
