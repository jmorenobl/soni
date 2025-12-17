## Task: 008 - Remove Deprecated process Field from FlowConfig

**ID de tarea:** 008
**Hito:** Code Cleanup
**Dependencias:** Ninguna
**Duración estimada:** 30 minutos

### Objetivo

Eliminar el campo `process` deprecated de `FlowConfig` que existe solo por retrocompatibilidad.

### Contexto

En `core/config.py`:

```python
class FlowConfig(BaseModel):
    steps: list[StepConfig] = Field(default_factory=list)
    process: list[StepConfig] | None = None  # Keep for backward compatibility if needed

    @property
    def steps_or_process(self) -> list[StepConfig]:
        return self.process or self.steps or []
```

El campo `process` ya no se usa y añade complejidad.

### Entregables

- [ ] Verificar que ningún YAML usa `process` en lugar de `steps`
- [ ] Eliminar campo `process` de FlowConfig
- [ ] Eliminar property `steps_or_process`, usar `steps` directamente
- [ ] Actualizar usos de `steps_or_process`
- [ ] Tests verificando que funciona

### Implementación Detallada

#### Paso 1: Verificar no hay uso de process

```bash
grep -r "process:" examples/ --include="*.yaml"
# Debe estar vacío
```

#### Paso 2: Simplificar FlowConfig

**Archivo(s) a modificar:** `src/soni/core/config.py`

```python
class FlowConfig(BaseModel):
    """Configuration for a single flow."""

    description: str
    steps: list[StepConfig] = Field(default_factory=list)
    trigger: TriggerConfig | None = None

    # ELIMINAR: process field
    # ELIMINAR: steps_or_process property
```

#### Paso 3: Actualizar usos

**Archivos a modificar:**
- `src/soni/compiler/subgraph.py:47` - Cambiar `steps_or_process` a `steps`

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/core/test_config_cleanup.py`

```python
import pytest
from soni.core.config import FlowConfig, StepConfig


class TestFlowConfigCleanup:
    """Tests for FlowConfig after process removal."""

    def test_steps_field_exists(self):
        """Test that steps field works."""
        # Arrange
        steps = [StepConfig(step="test", type="say", message="hi")]

        # Act
        flow = FlowConfig(description="Test", steps=steps)

        # Assert
        assert flow.steps == steps

    def test_no_process_field(self):
        """Test that process field doesn't exist."""
        # Arrange & Act
        flow = FlowConfig(description="Test")

        # Assert
        assert not hasattr(flow, "process") or flow.model_fields.get("process") is None

    def test_no_steps_or_process_property(self):
        """Test that deprecated property is removed."""
        # Arrange
        flow = FlowConfig(description="Test")

        # Assert
        assert not hasattr(flow, "steps_or_process")
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/core/test_config_cleanup.py -v
# Expected: FAILED (process/steps_or_process still exist)
```

#### Green Phase: Make Tests Pass

Eliminar campos deprecated.

```bash
uv run pytest tests/unit/core/test_config_cleanup.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] Campo `process` eliminado de FlowConfig
- [ ] Property `steps_or_process` eliminada
- [ ] Usos actualizados a `.steps`
- [ ] `uv run pytest` pasa
- [ ] `uv run ruff check .` sin errores
- [ ] `uv run mypy src/soni` sin errores

### Validación Manual

```bash
# Verificar no queda process en código
grep -r "steps_or_process" src/soni/ --include="*.py"
# Debería estar vacío

uv run pytest tests/ -v
```

### Referencias

- `src/soni/core/config.py:48-55` - Código actual
- `src/soni/compiler/subgraph.py:47` - Uso de steps_or_process
