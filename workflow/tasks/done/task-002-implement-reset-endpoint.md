## Task: 002 - Implement /reset Endpoint Correctly

**ID de tarea:** 002
**Hito:** 1 - Critical Fixes
**Dependencias:** Ninguna
**Duración estimada:** 3 horas
**Prioridad:** CRÍTICA

### Objetivo

Implementar correctamente el endpoint `/reset/{user_id}` que actualmente no ejecuta ningún reset real. El endpoint debe limpiar el estado de conversación del usuario especificado, usando el checkpointer si está disponible o manejando apropiadamente el caso sin persistencia.

### Contexto

El endpoint actual en `server/api.py:193-217` promete resetear el estado pero no lo hace:

```python
@app.post("/reset/{user_id}", response_model=ResetResponse)
async def reset_conversation(user_id: str, runtime: RuntimeDep) -> ResetResponse:
    # Note: Full reset requires checkpointer support
    # For now, we just confirm the intent - state will reset on next message
    _ = runtime  # Used for dependency validation

    return ResetResponse(
        success=True,
        message=f"Conversation state for user '{user_id}' will be reset on next interaction.",
    )
```

**Problemas:**
1. El endpoint dice "success=True" pero no hace nada
2. El mensaje promete reset "on next interaction" pero no hay garantía
3. La variable `runtime` no se usa (marca `_ = runtime`)
4. No hay manejo para diferentes backends de persistencia

### Entregables

- [ ] Implementar reset real usando RuntimeLoop
- [ ] Agregar método `reset_state()` a RuntimeLoop si no existe
- [ ] Manejar caso sin checkpointer (retornar 501 o usar estado in-memory)
- [ ] Actualizar ResetResponse con información útil
- [ ] Tests unitarios y de integración

### Implementación Detallada

#### Paso 1: Agregar método reset_state a RuntimeLoop

**Archivo(s) a modificar:** `src/soni/runtime/loop.py`

**Código específico:**

```python
async def reset_state(self, user_id: str) -> bool:
    """Reset conversation state for a user.

    Args:
        user_id: The user/thread ID to reset

    Returns:
        True if state was reset, False if no state existed

    Raises:
        StateError: If reset fails due to persistence error
    """
    if not self._components:
        logger.warning("reset_state called before initialization")
        return False

    checkpointer = self._components.checkpointer

    if checkpointer is None:
        # No persistence - state is already ephemeral
        logger.info(f"No checkpointer configured, state for {user_id} is ephemeral")
        return True

    try:
        # LangGraph checkpointer API for clearing state
        config = {"configurable": {"thread_id": user_id}}

        # Check if state exists first
        current = await self.get_state(user_id)
        if current is None:
            logger.debug(f"No state to reset for user {user_id}")
            return False

        # Delete the checkpoint for this thread
        # Note: LangGraph checkpointer API varies by implementation
        if hasattr(checkpointer, "adelete"):
            await checkpointer.adelete(config)
        elif hasattr(checkpointer, "delete"):
            checkpointer.delete(config)
        else:
            # Fallback: Write empty state
            from soni.core.state import create_empty_dialogue_state
            empty_state = create_empty_dialogue_state()
            await self._write_state(user_id, empty_state)

        logger.info(f"Reset state for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to reset state for {user_id}: {e}")
        raise StateError(f"Reset failed: {e}") from e
```

**Explicación:**
- Verifica que el runtime esté inicializado
- Maneja el caso sin checkpointer (estado efímero)
- Intenta usar la API del checkpointer para borrar
- Fallback a escribir estado vacío si no hay método delete

#### Paso 2: Actualizar el endpoint /reset

**Archivo(s) a modificar:** `src/soni/server/api.py`

**Código específico:**

```python
from soni.core.errors import StateError

@app.post("/reset/{user_id}", response_model=ResetResponse)
async def reset_conversation(
    user_id: str,
    runtime: RuntimeDep,
) -> ResetResponse:
    """Reset the conversation state for a user.

    Clears all conversation history, flow state, and slot values
    for the specified user. The next message will start a fresh
    conversation.
    """
    try:
        was_reset = await runtime.reset_state(user_id)

        if was_reset:
            return ResetResponse(
                success=True,
                message=f"Conversation state for user '{user_id}' has been reset.",
            )
        else:
            return ResetResponse(
                success=True,
                message=f"No existing state found for user '{user_id}'.",
            )

    except StateError as e:
        raise create_error_response(
            exception=e,
            user_id=user_id,
            endpoint="/reset",
        ) from e
```

**Explicación:**
- Llama a `runtime.reset_state()` que hace el trabajo real
- Diferencia entre "reset exitoso" y "no había estado"
- Maneja errores apropiadamente con create_error_response

#### Paso 3: Actualizar ResetResponse model si es necesario

**Archivo(s) a modificar:** `src/soni/server/models.py`

**Verificar que ResetResponse tenga campos útiles:**

```python
class ResetResponse(BaseModel):
    """Response model for reset operations."""
    success: bool = Field(description="Whether the reset operation succeeded")
    message: str = Field(description="Human-readable result message")
    user_id: str | None = Field(default=None, description="The user ID that was reset")
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/runtime/test_reset_state.py`

**Failing tests to write FIRST:**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from soni.runtime.loop import RuntimeLoop
from soni.core.errors import StateError


class TestResetState:
    """Tests for RuntimeLoop.reset_state()."""

    @pytest.fixture
    def mock_config(self):
        """Create mock SoniConfig."""
        config = MagicMock()
        config.settings.persistence.backend = "memory"
        return config

    @pytest.mark.asyncio
    async def test_reset_state_returns_true_when_state_exists(self, mock_config):
        """Test that reset_state returns True when state was cleared."""
        runtime = RuntimeLoop(config=mock_config)
        # Setup: create some state first
        await runtime.initialize()
        await runtime.process_message("hello", user_id="test_user")

        # Act
        result = await runtime.reset_state("test_user")

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_reset_state_returns_false_when_no_state(self, mock_config):
        """Test that reset_state returns False when no state existed."""
        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Act - reset for user that never interacted
        result = await runtime.reset_state("nonexistent_user")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_reset_state_clears_flow_stack(self, mock_config):
        """Test that reset_state clears the flow stack."""
        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Setup: create state with active flow
        await runtime.process_message("start transfer", user_id="test_user")
        state_before = await runtime.get_state("test_user")
        assert len(state_before.get("flow_stack", [])) > 0

        # Act
        await runtime.reset_state("test_user")

        # Assert
        state_after = await runtime.get_state("test_user")
        assert state_after is None or len(state_after.get("flow_stack", [])) == 0

    @pytest.mark.asyncio
    async def test_reset_state_clears_slots(self, mock_config):
        """Test that reset_state clears all slot values."""
        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Setup: create state with slots
        await runtime.process_message("transfer 100 euros", user_id="test_user")
        state_before = await runtime.get_state("test_user")
        assert len(state_before.get("flow_slots", {})) > 0

        # Act
        await runtime.reset_state("test_user")

        # Assert
        state_after = await runtime.get_state("test_user")
        assert state_after is None or len(state_after.get("flow_slots", {})) == 0

    @pytest.mark.asyncio
    async def test_reset_state_before_init_returns_false(self, mock_config):
        """Test that reset_state returns False if called before init."""
        runtime = RuntimeLoop(config=mock_config)
        # Don't initialize

        result = await runtime.reset_state("test_user")

        assert result is False

    @pytest.mark.asyncio
    async def test_reset_state_with_checkpointer_error_raises(self, mock_config):
        """Test that checkpointer errors are propagated as StateError."""
        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Mock checkpointer to raise error
        runtime._components.checkpointer.adelete = AsyncMock(
            side_effect=Exception("DB connection lost")
        )

        with pytest.raises(StateError) as exc_info:
            await runtime.reset_state("test_user")

        assert "Reset failed" in str(exc_info.value)
```

**Test file:** `tests/unit/server/test_reset_endpoint.py`

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock


class TestResetEndpoint:
    """Tests for POST /reset/{user_id} endpoint."""

    @pytest.fixture
    def client_with_runtime(self):
        """Create test client with mocked runtime."""
        from soni.server.api import app

        mock_runtime = MagicMock()
        mock_runtime.reset_state = AsyncMock(return_value=True)
        app.state.runtime = mock_runtime

        return TestClient(app), mock_runtime

    def test_reset_returns_success_when_state_cleared(self, client_with_runtime):
        """Test that reset returns success=True when state was cleared."""
        client, mock_runtime = client_with_runtime
        mock_runtime.reset_state = AsyncMock(return_value=True)

        response = client.post("/reset/test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "has been reset" in data["message"]

    def test_reset_returns_success_when_no_state(self, client_with_runtime):
        """Test that reset returns success with appropriate message when no state."""
        client, mock_runtime = client_with_runtime
        mock_runtime.reset_state = AsyncMock(return_value=False)

        response = client.post("/reset/unknown_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "No existing state" in data["message"]

    def test_reset_returns_error_on_failure(self, client_with_runtime):
        """Test that reset returns error when operation fails."""
        from soni.core.errors import StateError

        client, mock_runtime = client_with_runtime
        mock_runtime.reset_state = AsyncMock(
            side_effect=StateError("Database unavailable")
        )

        response = client.post("/reset/test_user")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data["detail"]
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/runtime/test_reset_state.py tests/unit/server/test_reset_endpoint.py -v
# Expected: FAILED (feature not implemented yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for /reset endpoint implementation"
```

#### Green Phase: Make Tests Pass

See "Implementación Detallada" section for implementation steps.

**Verify tests pass:**
```bash
uv run pytest tests/unit/runtime/test_reset_state.py tests/unit/server/test_reset_endpoint.py -v
# Expected: PASSED
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: implement /reset endpoint with actual state clearing

- Add RuntimeLoop.reset_state() method
- Support checkpointer deletion and fallback
- Update /reset endpoint to use reset_state()
- Handle no-state and error cases appropriately"
```

#### Refactor Phase: Improve Design

- Add docstrings and type hints
- Consider adding reset confirmation in response
- Tests must still pass!

**Commit:**
```bash
git add src/
git commit -m "refactor: improve reset endpoint implementation"
```

### Criterios de Éxito

- [ ] Endpoint `/reset/{user_id}` ejecuta un reset real del estado
- [ ] RuntimeLoop tiene método `reset_state()` funcional
- [ ] Maneja correctamente el caso sin checkpointer
- [ ] Maneja correctamente errores de persistencia
- [ ] Respuesta indica claramente qué sucedió
- [ ] Todos los tests pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Iniciar servidor
uv run soni server --config examples/banking/soni.yaml &

# Crear estado
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test123", "message": "I want to transfer money"}'

# Verificar estado existe
curl http://localhost:8000/state/test123

# Resetear
curl -X POST http://localhost:8000/reset/test123

# Verificar estado fue limpiado
curl http://localhost:8000/state/test123
```

**Resultado esperado:**
- Primer GET muestra estado con flow activo
- POST /reset retorna success=True
- Segundo GET muestra estado vacío o 404

### Referencias

- `src/soni/server/api.py` - Endpoint actual
- `src/soni/runtime/loop.py` - RuntimeLoop
- `src/soni/runtime/checkpointer.py` - Checkpointer factory
- LangGraph checkpointer documentation

### Notas Adicionales

**Consideraciones de seguridad:**
- No exponer información sobre qué datos fueron borrados
- Considerar rate limiting para prevenir abuse
- Loggear resets para auditoría

**Edge Cases:**
- Reset de usuario que nunca existió
- Reset durante conversación activa
- Reset con checkpointer en error state
