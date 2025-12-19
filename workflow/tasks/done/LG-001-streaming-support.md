## Task: LG-001 - Implement LangGraph Streaming Support

**ID de tarea:** LG-001
**Hito:** LangGraph Modernization
**Dependencias:** Ninguna
**Duración estimada:** 8-12 horas
**Prioridad:** Alta (High Impact on UX)

### Objetivo

Implementar soporte de streaming en RuntimeLoop usando `astream()` con `stream_mode="updates"` para emitir respuestas parciales nodo-por-nodo, mejorando significativamente la experiencia de usuario.

### Contexto

Actualmente Soni solo usa `graph.ainvoke()` que espera la respuesta completa antes de devolverla. LangGraph ofrece `astream()` con varios modos de streaming que permiten:
- Updates por nodo (`stream_mode="updates"`) - **Recomendado para Soni**
- Token streaming del LLM (`stream_mode="messages"`) - Requiere LangChain LLMs
- Estado completo (`stream_mode="values"`)
- Datos custom (`stream_mode="custom"`) - Usa `get_stream_writer()`

> **Nota:** Soni usa DSPy para NLU, no LangChain LLMs directamente en los nodos. Por tanto, `stream_mode="updates"` es la opción más apropiada ya que emite actualizaciones después de cada nodo del grafo.

**Referencia:** `ref/langgraph/libs/langgraph/langgraph/pregel/main.py` - método `astream()`

**Análisis:** `docs/analysis/LANGGRAPH_USAGE_REVIEW.md` - Sección 3.6

### Entregables

- [ ] Nuevo método `process_message_streaming()` en RuntimeLoop
- [ ] Endpoint SSE en FastAPI server para streaming
- [ ] CLI con soporte de streaming (impresión progresiva)
- [ ] Tests de integración para streaming
- [ ] Documentación actualizada

### Implementación Detallada

#### Paso 1: Agregar método de streaming en RuntimeLoop

**Archivo(s) a modificar:** `src/soni/runtime/loop.py`

**Código específico:**

```python
from collections.abc import AsyncIterator
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.types import StreamMode


class RuntimeLoop:
    # ... existing code ...

    async def process_message_streaming(
        self,
        user_message: str,
        user_id: str = "default",
        stream_mode: StreamMode = "updates",
    ) -> AsyncIterator[dict[str, Any]]:
        """Process a message with streaming output.

        Args:
            user_message: The user's input message
            user_id: User identifier for state persistence
            stream_mode: LangGraph stream mode (updates, values, custom)
                - "updates": Emit state updates after each node (recommended)
                - "values": Emit full state after each node
                - "custom": Emit custom data via get_stream_writer()

        Yields:
            Streaming chunks in format {node_name: {state_updates}}
        """
        if not self._components or not self._components.graph:
            await self.initialize()

        if not self._components or not self._components.graph:
            raise StateError("Graph initialization failed")

        # Create runtime context for dependency injection
        context = RuntimeContext(
            config=self.config,
            flow_manager=self.flow_manager,
            action_handler=self.action_handler,
            du=self.du,
            slot_extractor=self.slot_extractor,
        )

        # Get current state and prepare input
        current_state = await self.get_state(user_id)
        input_payload = self._hydrator.prepare_input(user_message, current_state)

        # Build config with thread and context
        run_config: dict[str, Any] = {
            "configurable": {
                "thread_id": user_id,
                "runtime_context": context,
            }
        }

        async for chunk in self._components.graph.astream(
            input_payload,
            config=cast(RunnableConfig, run_config),
            stream_mode=stream_mode,
        ):
            yield chunk
```

**Explicación:**
- Usa la misma lógica de preparación que `process_message()`
- Incluye `RuntimeContext` para que los nodos funcionen correctamente
- `stream_mode="updates"` emite `{node_name: {state_updates}}` después de cada nodo
- El caller decide cómo procesar los chunks

#### Paso 2: Crear ResponseStreamExtractor

**Archivo(s) a crear:** `src/soni/runtime/stream_extractor.py`

**Código específico:**

```python
"""Extract and format streaming chunks from LangGraph."""

from typing import Any
from dataclasses import dataclass


@dataclass
class StreamChunk:
    """Normalized streaming chunk."""

    content: str
    node: str | None = None
    is_final: bool = False
    metadata: dict[str, Any] | None = None


class ResponseStreamExtractor:
    """Extract response content from LangGraph stream chunks.

    Handles different stream_mode formats and normalizes output.
    """

    def extract(self, chunk: Any, stream_mode: str) -> StreamChunk | None:
        """Extract content from a stream chunk.

        Args:
            chunk: Raw chunk from LangGraph astream()
            stream_mode: The stream mode used

        Returns:
            Normalized StreamChunk or None if chunk should be skipped
        """
        match stream_mode:
            case "updates":
                return self._extract_updates(chunk)
            case "values":
                return self._extract_values(chunk)
            case "custom":
                return self._extract_custom(chunk)
            case _:
                return StreamChunk(content=str(chunk))

    def _extract_updates(self, chunk: dict[str, Any]) -> StreamChunk | None:
        """Extract from updates stream mode (per-node updates).

        Updates mode yields {node_name: {state_updates}}
        We look for 'last_response' or other response fields.
        """
        for node, updates in chunk.items():
            # Skip internal nodes
            if node.startswith("__"):
                continue

            # Check for response content
            if isinstance(updates, dict):
                if "last_response" in updates:
                    return StreamChunk(
                        content=updates["last_response"],
                        node=node,
                        is_final=True,
                    )
                # Could also check for 'messages' with AIMessage
        return None

    def _extract_values(self, chunk: dict[str, Any]) -> StreamChunk | None:
        """Extract from values stream mode (full state)."""
        if "last_response" in chunk:
            return StreamChunk(
                content=chunk["last_response"],
                is_final=True,
            )
        return None

    def _extract_custom(self, chunk: Any) -> StreamChunk | None:
        """Extract from custom stream mode (user-defined data)."""
        if isinstance(chunk, str):
            return StreamChunk(content=chunk)
        elif isinstance(chunk, dict) and "content" in chunk:
            return StreamChunk(
                content=chunk["content"],
                metadata=chunk.get("metadata"),
            )
        return StreamChunk(content=str(chunk))
```

**Explicación:**
- Normaliza los diferentes formatos de chunk según `stream_mode`
- Para `updates`, extrae contenido de `last_response` del estado
- Facilita el manejo en CLI y server
- Extensible para otros campos de respuesta

#### Paso 3: Agregar endpoint SSE en el servidor FastAPI

**Archivo(s) a modificar:** `src/soni/server/api.py`

**Código específico:**

```python
from fastapi.responses import StreamingResponse
import json


@app.post("/chat/stream")
async def chat_stream(
    request: MessageRequest,
    runtime: RuntimeDep,
) -> StreamingResponse:
    """Stream chat responses via Server-Sent Events.

    Emits incremental updates as each node in the graph completes.
    """
    from soni.runtime.stream_extractor import ResponseStreamExtractor

    extractor = ResponseStreamExtractor()

    async def event_generator():
        async for chunk in runtime.process_message_streaming(
            request.message,
            user_id=request.user_id,
            stream_mode="updates",
        ):
            # Extract response content
            stream_chunk = extractor.extract(chunk, "updates")
            if stream_chunk and stream_chunk.content:
                data = json.dumps({
                    "content": stream_chunk.content,
                    "node": stream_chunk.node,
                    "is_final": stream_chunk.is_final,
                }, default=str)
                yield f"data: {data}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

**Explicación:**
- Endpoint separado para streaming (`/chat/stream`)
- Usa Server-Sent Events (SSE) estándar
- Compatible con EventSource del browser
- Señal `[DONE]` al finalizar (patrón OpenAI)
- Usa `ResponseStreamExtractor` para normalizar chunks

#### Paso 4: Agregar soporte de streaming en CLI

**Archivo(s) a modificar:** `src/soni/cli/commands/chat.py`

**Código específico:**

```python
class SoniChatCLI:
    """Interactive CLI for Soni conversations."""

    def __init__(
        self,
        runtime: RuntimeLoop,
        user_id: str = "cli_user",
        streaming: bool = False,
    ):
        self.console = Console()
        self.runtime = runtime
        self.user_id = user_id
        self.streaming = streaming

    async def start(self) -> None:
        """Start the interactive session."""
        from soni.runtime.stream_extractor import ResponseStreamExtractor

        self.console.print(BANNER_ART, style="bold blue")
        self.console.print(f"Session ID: [green]{self.user_id}[/]")
        if self.streaming:
            self.console.print("[dim]Streaming mode enabled[/]")
        self.console.print("Type 'exit' or 'quit' to end session.\n")

        extractor = ResponseStreamExtractor()

        while True:
            try:
                user_input = self.console.input("[bold green]You > [/]")
                if user_input.lower() in ("exit", "quit"):
                    self.console.print("\n[yellow]Goodbye![/]")
                    break

                if not user_input.strip():
                    continue

                if self.streaming:
                    # Streaming mode
                    self.console.print("[bold blue]Soni > [/]", end="")
                    last_response = ""

                    async for chunk in self.runtime.process_message_streaming(
                        user_input,
                        user_id=self.user_id,
                        stream_mode="updates",
                    ):
                        stream_chunk = extractor.extract(chunk, "updates")
                        if stream_chunk and stream_chunk.content:
                            # Print new content (avoid duplicates)
                            if stream_chunk.content != last_response:
                                print(stream_chunk.content, end="", flush=True)
                                last_response = stream_chunk.content

                    print()  # Newline after response
                else:
                    # Non-streaming mode (existing behavior)
                    with self.console.status("[bold blue]Thinking...[/]"):
                        response = await self.runtime.process_message(
                            user_input, user_id=self.user_id
                        )

                    if response:
                        text = (
                            response.get("response", "...")
                            if isinstance(response, dict)
                            else str(response)
                        )
                        self.console.print(f"[bold blue]Soni > [/]{text}\n")

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Goodbye![/]")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/]")
```

**También agregar flag `--streaming` al comando:**

```python
@app.callback(invoke_without_command=True)
def run_chat(
    config: Path = typer.Option(..., "--config", "-c", help="Path to soni.yaml", exists=True),
    user_id: str | None = typer.Option(None, "--user-id", "-u", help="User ID for session"),
    streaming: bool = typer.Option(False, "--streaming", "-s", help="Enable streaming mode"),
    # ... other options ...
):
    # ...
    chat = SoniChatCLI(
        runtime,
        user_id=user_id or f"cli_{uuid.uuid4().hex[:6]}",
        streaming=streaming,
    )
    await chat.start()
```

**Explicación:**
- Flag `--streaming` / `-s` para activar modo streaming
- En streaming, imprime respuestas progresivamente
- En modo normal, mantiene comportamiento existente con spinner

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/runtime/test_loop_streaming.py`

**Failing tests to write FIRST:**

```python
"""Tests for RuntimeLoop streaming functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestRuntimeLoopStreaming:
    """Tests for process_message_streaming method."""

    @pytest.fixture
    def mock_graph(self):
        """Create mock compiled graph with astream."""
        graph = MagicMock()
        graph.astream = AsyncMock()
        return graph

    @pytest.fixture
    def runtime_loop(self, mock_graph):
        """Create RuntimeLoop with mocked graph."""
        from soni.runtime.loop import RuntimeLoop
        from soni.runtime.initializer import RuntimeComponents

        loop = RuntimeLoop.__new__(RuntimeLoop)
        loop._components = MagicMock(spec=RuntimeComponents)
        loop._components.graph = mock_graph
        loop._components.flow_manager = MagicMock()
        loop._components.action_handler = MagicMock()
        loop._components.du = MagicMock()
        loop._components.slot_extractor = None
        loop._hydrator = MagicMock()
        loop._hydrator.prepare_input.return_value = {"user_message": "test"}
        loop.config = MagicMock()
        return loop

    @pytest.mark.asyncio
    async def test_process_message_streaming_yields_chunks(
        self, runtime_loop, mock_graph
    ):
        """Test that streaming yields chunks from graph.astream()."""
        # Arrange
        expected_chunks = [
            {"understand": {"nlu_result": "parsed"}},
            {"respond": {"last_response": "Hello!"}},
        ]

        async def mock_astream(*args, **kwargs):
            for chunk in expected_chunks:
                yield chunk

        mock_graph.astream = mock_astream

        with patch.object(runtime_loop, 'get_state', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            # Act
            chunks = []
            async for chunk in runtime_loop.process_message_streaming("Hi"):
                chunks.append(chunk)

        # Assert
        assert chunks == expected_chunks

    @pytest.mark.asyncio
    async def test_process_message_streaming_uses_updates_mode_by_default(
        self, runtime_loop, mock_graph
    ):
        """Test that default stream_mode is 'updates'."""
        # Arrange
        captured_kwargs = {}

        async def mock_astream(*args, **kwargs):
            captured_kwargs.update(kwargs)
            yield {"node": {"data": "test"}}

        mock_graph.astream = mock_astream

        with patch.object(runtime_loop, 'get_state', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            # Act
            async for _ in runtime_loop.process_message_streaming("test"):
                pass

        # Assert
        assert captured_kwargs.get("stream_mode") == "updates"

    @pytest.mark.asyncio
    async def test_process_message_streaming_accepts_custom_stream_mode(
        self, runtime_loop, mock_graph
    ):
        """Test that custom stream_mode is passed to graph."""
        # Arrange
        captured_kwargs = {}

        async def mock_astream(*args, **kwargs):
            captured_kwargs.update(kwargs)
            yield {"state": "full"}

        mock_graph.astream = mock_astream

        with patch.object(runtime_loop, 'get_state', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            # Act
            async for _ in runtime_loop.process_message_streaming(
                "test", stream_mode="values"
            ):
                pass

        # Assert
        assert captured_kwargs.get("stream_mode") == "values"

    @pytest.mark.asyncio
    async def test_process_message_streaming_includes_runtime_context(
        self, runtime_loop, mock_graph
    ):
        """Test that RuntimeContext is included in config."""
        # Arrange
        captured_config = {}

        async def mock_astream(*args, **kwargs):
            captured_config.update(kwargs.get("config", {}))
            yield {"node": {}}

        mock_graph.astream = mock_astream

        with patch.object(runtime_loop, 'get_state', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            # Act
            async for _ in runtime_loop.process_message_streaming("test", user_id="user1"):
                pass

        # Assert
        assert "configurable" in captured_config
        assert "runtime_context" in captured_config["configurable"]
        assert captured_config["configurable"]["thread_id"] == "user1"


class TestResponseStreamExtractor:
    """Tests for ResponseStreamExtractor."""

    def test_extract_updates_mode_with_last_response(self):
        """Test extraction from updates mode with last_response."""
        from soni.runtime.stream_extractor import ResponseStreamExtractor

        extractor = ResponseStreamExtractor()
        chunk = {"respond": {"last_response": "Hello world!"}}

        result = extractor.extract(chunk, "updates")

        assert result is not None
        assert result.content == "Hello world!"
        assert result.node == "respond"
        assert result.is_final is True

    def test_extract_updates_mode_skips_internal_nodes(self):
        """Test that internal nodes are skipped."""
        from soni.runtime.stream_extractor import ResponseStreamExtractor

        extractor = ResponseStreamExtractor()
        chunk = {"__start__": {"data": "internal"}}

        result = extractor.extract(chunk, "updates")

        assert result is None

    def test_extract_updates_mode_no_response_field(self):
        """Test extraction when no response field present."""
        from soni.runtime.stream_extractor import ResponseStreamExtractor

        extractor = ResponseStreamExtractor()
        chunk = {"understand": {"nlu_result": "parsed"}}

        result = extractor.extract(chunk, "updates")

        assert result is None

    def test_extract_values_mode(self):
        """Test extraction from values mode."""
        from soni.runtime.stream_extractor import ResponseStreamExtractor

        extractor = ResponseStreamExtractor()
        chunk = {"last_response": "Full state response", "other": "data"}

        result = extractor.extract(chunk, "values")

        assert result is not None
        assert result.content == "Full state response"
        assert result.is_final is True

    def test_extract_custom_mode_string(self):
        """Test extraction from custom mode with string."""
        from soni.runtime.stream_extractor import ResponseStreamExtractor

        extractor = ResponseStreamExtractor()
        chunk = "Custom progress update"

        result = extractor.extract(chunk, "custom")

        assert result is not None
        assert result.content == "Custom progress update"
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/runtime/test_loop_streaming.py -v
# Expected: FAILED (feature not implemented yet)
```

#### Green Phase: Make Tests Pass

Implement the code from "Implementación Detallada" section.

**Verify tests pass:**
```bash
uv run pytest tests/unit/runtime/test_loop_streaming.py -v
# Expected: PASSED
```

#### Refactor Phase: Improve Design

- Add comprehensive docstrings
- Ensure type hints are complete
- Consider adding logging for debugging
- Verify mypy passes

### Tests Requeridos

**Archivo de tests adicionales:** `tests/integration/test_streaming.py`

```python
"""Integration tests for streaming functionality."""

import pytest


@pytest.mark.integration
class TestStreamingIntegration:
    """End-to-end streaming tests."""

    @pytest.mark.asyncio
    async def test_full_conversation_streaming(self, runtime_loop):
        """Test streaming through full conversation flow."""
        chunks = []
        async for chunk in runtime_loop.process_message_streaming(
            "Hello, how are you?"
        ):
            chunks.append(chunk)

        # Should receive multiple chunks (one per node)
        assert len(chunks) > 0

        # At least one chunk should have response content
        has_response = any(
            isinstance(c, dict) and
            any("last_response" in v for v in c.values() if isinstance(v, dict))
            for c in chunks
        )
        assert has_response

    @pytest.mark.asyncio
    async def test_streaming_maintains_state(self, runtime_loop):
        """Test that streaming maintains conversation state."""
        # First message
        async for _ in runtime_loop.process_message_streaming("Start a transfer"):
            pass

        # Second message should continue context
        async for chunk in runtime_loop.process_message_streaming("100 euros"):
            pass

        # State should reflect both messages
        state = await runtime_loop.get_state("default")
        assert state is not None
        assert state.get("turn_count", 0) >= 2
```

### Criterios de Éxito

- [ ] `process_message_streaming()` disponible en RuntimeLoop
- [ ] Endpoint `/chat/stream` funcional con SSE
- [ ] CLI con flag `--streaming` imprime respuestas progresivamente
- [ ] ResponseStreamExtractor maneja `updates`, `values`, `custom` modes
- [ ] Tests unitarios pasan
- [ ] Tests de integración pasan
- [ ] Linting pasa sin errores (`ruff check`)
- [ ] Type checking pasa sin errores (`mypy`)
- [ ] Latencia percibida reducida (respuesta visible antes del final)

### Validación Manual

**Comandos para validar:**

```bash
# Test unitarios
uv run pytest tests/unit/runtime/test_loop_streaming.py -v

# Test de integración
uv run pytest tests/integration/test_streaming.py -v

# Validación manual CLI (modo streaming)
uv run soni chat --config examples/banking/domain --streaming

# Validación manual CLI (modo normal para comparar)
uv run soni chat --config examples/banking/domain

# Validación manual server
uv run soni server --config examples/banking/domain &
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "user_id": "test"}'
```

**Resultado esperado:**
- CLI con `--streaming` muestra respuestas apareciendo progresivamente
- curl muestra eventos SSE llegando incrementalmente
- Cada nodo que actualiza `last_response` genera un evento
- No hay errores en logs

### Referencias

- [LangGraph Streaming Docs](ref/langgraph/docs/docs/how-tos/streaming.md)
- [Pregel astream implementation](ref/langgraph/libs/langgraph/langgraph/pregel/main.py)
- [StreamMode Type](ref/langgraph/libs/langgraph/langgraph/types.py) - línea 76

### Notas Adicionales

- **`stream_mode="updates"` es el modo recomendado** para Soni ya que no usa LangChain LLMs
- El modo `"messages"` requiere integración de LangChain LLMs en los nodos (futuro)
- SSE es más compatible que WebSockets para este caso de uso
- Verificar comportamiento con checkpointer activo
- Considerar añadir `--no-stream` como alias explícito del modo por defecto
