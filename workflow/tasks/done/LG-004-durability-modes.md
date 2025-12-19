## Task: LG-004 - Configure LangGraph Durability Modes

**ID de tarea:** LG-004
**Hito:** LangGraph Modernization
**Dependencias:** Ninguna
**Duración estimada:** 1-2 horas
**Prioridad:** Baja (Performance Optimization)

### Objetivo

Configurar el modo de durabilidad de LangGraph para optimizar la latencia de checkpointing, pasando `durability` a `ainvoke()`/`astream()`.

### Contexto

LangGraph ofrece tres modos de durabilidad para checkpointing:

| Modo | Comportamiento | Latencia | Seguridad |
|------|----------------|----------|-----------|
| `"sync"` | Persiste antes del siguiente paso | Alta | Máxima |
| `"async"` (default) | Persiste mientras el siguiente paso ejecuta | Media | Alta |
| `"exit"` | Persiste solo al finalizar | Baja | Baja |

**NOTA:** El default de LangGraph ya es `"async"` (no `"sync"` como se pensaba).

**Referencia:** Parámetro `durability` en `ainvoke()`/`astream()` - líneas 2415, 2452 de `ref/langgraph/libs/langgraph/langgraph/pregel/main.py`

### Entregables

- [ ] Parámetro `durability` configurable en SoniConfig
- [ ] RuntimeLoop pasa durability a ainvoke/astream
- [ ] Tests unitarios
- [ ] Documentación actualizada

### Implementación Detallada

#### Paso 1: Agregar configuración de durabilidad

**Archivo(s) a modificar:** `src/soni/config/models.py`

```python
from typing import Literal

DurabilityMode = Literal["sync", "async", "exit"]

class SoniConfig(BaseModel):
    # ... existing fields ...

    durability: DurabilityMode = "async"
    """Checkpoint durability mode (passed to LangGraph runtime).

    - sync: Persist before next step (safest, slower)
    - async: Persist while next step runs (default, balanced)
    - exit: Persist only on exit (fastest, risky)
    """
```

#### Paso 2: Pasar durability a ainvoke/astream

**Archivo(s) a modificar:** `src/soni/runtime/loop.py`

```python
async def process_message(
    self,
    user_message: str,
    user_id: str = "default",
) -> str:
    payload = self._hydrator.prepare_input(user_message, current_state)
    run_config = self._build_run_config(user_id)

    result = await self._components.graph.ainvoke(
        payload,
        config=run_config,
        context=self._context,
        durability=self._config.durability,  # ← Add here
    )

    return self._extractor.extract(result, payload, None)
```

**También actualizar streaming (si existe):**

```python
async for chunk in self._components.graph.astream(
    payload,
    config=run_config,
    context=self._context,
    durability=self._config.durability,  # ← Add here
    stream_mode=stream_mode,
):
    yield chunk
```

#### Paso 3: Configuración por entorno

**Ejemplo en YAML:**

```yaml
# config/production.yaml
durability: async  # Default, balanced

# config/development.yaml
durability: sync  # Safer for debugging

# config/high-performance.yaml
durability: exit  # Only if you accept data loss risk
```

**Variable de entorno (opcional):**

```python
durability: DurabilityMode = Field(
    default="async",
    env="SONI_DURABILITY",
)
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/runtime/test_durability.py`

```python
"""Tests for durability configuration."""

import pytest
from unittest.mock import MagicMock, AsyncMock


class TestDurabilityConfig:
    """Tests for durability mode configuration."""

    def test_config_accepts_durability_modes(self):
        """Test that SoniConfig accepts valid durability modes."""
        from soni.config.models import SoniConfig

        for mode in ["sync", "async", "exit"]:
            config = SoniConfig(durability=mode)
            assert config.durability == mode

    def test_config_default_is_async(self):
        """Test that default durability is async."""
        from soni.config.models import SoniConfig

        config = SoniConfig()
        assert config.durability == "async"


class TestRuntimeLoopDurability:
    """Tests for RuntimeLoop durability passing."""

    @pytest.mark.asyncio
    async def test_passes_durability_to_ainvoke(self):
        """Test that RuntimeLoop passes durability to graph.ainvoke."""
        from soni.runtime.loop import RuntimeLoop

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={"last_response": "ok"})
        mock_graph.aget_state = AsyncMock(return_value=MagicMock(values={}))

        mock_config = MagicMock()
        mock_config.durability = "sync"

        loop = RuntimeLoop.__new__(RuntimeLoop)
        loop._components = MagicMock()
        loop._components.graph = mock_graph
        loop._config = mock_config
        loop._context = MagicMock()
        loop._hydrator = MagicMock()
        loop._hydrator.prepare_input.return_value = {}
        loop._extractor = MagicMock()
        loop._extractor.extract.return_value = "ok"
        loop._build_run_config = MagicMock(return_value={})
        loop.get_state = AsyncMock(return_value=None)

        await loop.process_message("hello")

        # Verify durability was passed
        call_kwargs = mock_graph.ainvoke.call_args.kwargs
        assert call_kwargs.get("durability") == "sync"
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/runtime/test_durability.py -v
# Expected: FAILED (durability not configured yet)
```

#### Green Phase: Make Tests Pass

Implement the code from "Implementación Detallada" section.

### Criterios de Éxito

- [ ] `durability` configurable en SoniConfig
- [ ] Default es `"async"`
- [ ] RuntimeLoop pasa durability a ainvoke/astream
- [ ] Tests pasan
- [ ] Sin cambios en comportamiento funcional

### Validación Manual

```bash
# Run tests
uv run pytest tests/unit/runtime/test_durability.py -v

# Manual validation with logging
SONI_LOG_LEVEL=DEBUG uv run soni chat --config examples/banking/domain
# Check logs for durability setting being applied
```

### Referencias

- [LangGraph durability parameter](ref/langgraph/libs/langgraph/langgraph/pregel/main.py#L2415-2458)

### Notas Adicionales

- El default de LangGraph ya es `"async"` - no es necesario cambiar nada si se quiere el default
- `"exit"` mode NO recomendado para producción (pérdida de estado en crash)
- durability solo tiene efecto si hay un checkpointer configurado
- Considerar benchmark antes/después para medir mejora de latencia real
