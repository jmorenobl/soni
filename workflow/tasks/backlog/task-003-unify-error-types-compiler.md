## Task: 003 - Unify Error Types in Compiler Module

**ID de tarea:** 003
**Hito:** 1 - Critical Fixes
**Dependencias:** Ninguna
**Duración estimada:** 2 horas
**Prioridad:** ALTA

### Objetivo

Reemplazar todos los usos de `ValueError` en el módulo compiler con los tipos de error específicos del dominio (`GraphBuildError`, `ConfigError`, `ValidationError`) para permitir un manejo de errores más granular y consistente con el resto del sistema.

### Contexto

El módulo `soni.core.errors` define una jerarquía de errores específicos del dominio:
- `ConfigError` - Errores de configuración YAML
- `GraphBuildError` - Errores durante compilación del grafo
- `ValidationError` - Errores de validación de datos

Sin embargo, el módulo compiler usa `ValueError` genérico:

**Ubicaciones del problema:**
- `compiler/factory.py:28` - `raise ValueError(f"Unknown step type: {step_type}")`
- `compiler/subgraph.py:121` - `raise ValueError(f"While step '{original_name}' missing condition")`
- `compiler/subgraph.py:123` - `raise ValueError(f"While step '{original_name}' missing do block")`
- `compiler/nodes/*.py` - Múltiples archivos usan `ValueError`

**Problema:**
```python
try:
    graph = compiler.build(config)
except ValueError as e:  # Captura errores del compiler
    ...  # Pero también cualquier otro ValueError!
except ConfigError as e:  # No captura errores del compiler
    ...
```

### Entregables

- [ ] Reemplazar `ValueError` con `GraphBuildError` en factory.py y subgraph.py
- [ ] Reemplazar `ValueError` con `ValidationError` en nodes/*.py para campos faltantes
- [ ] Actualizar imports en todos los archivos afectados
- [ ] Agregar tests que verifiquen los tipos de error correctos

### Implementación Detallada

#### Paso 1: Actualizar factory.py

**Archivo(s) a modificar:** `src/soni/compiler/factory.py`

**Cambios:**

```python
# ANTES (línea 1-5)
"""Node factory registry."""

# DESPUÉS
"""Node factory registry."""
from soni.core.errors import GraphBuildError
```

```python
# ANTES (línea 28)
raise ValueError(f"Unknown step type: {step_type}")

# DESPUÉS
raise GraphBuildError(f"Unknown step type: '{step_type}'. Available types: {list(cls._factories.keys())}")
```

**Explicación:**
- Usar `GraphBuildError` porque es un error durante la construcción del grafo
- Mejorar el mensaje de error incluyendo tipos disponibles

#### Paso 2: Actualizar subgraph.py

**Archivo(s) a modificar:** `src/soni/compiler/subgraph.py`

**Agregar import:**

```python
from soni.core.errors import GraphBuildError
```

**Reemplazar errores:**

```python
# ANTES (línea ~121)
if not step.condition:
    raise ValueError(f"While step '{original_name}' missing condition")

# DESPUÉS
if not step.condition:
    raise GraphBuildError(
        f"While step '{original_name}' missing required field 'condition'. "
        f"While loops must have a condition to evaluate."
    )
```

```python
# ANTES (línea ~123)
if not step.do:
    raise ValueError(f"While step '{original_name}' missing do block")

# DESPUÉS
if not step.do:
    raise GraphBuildError(
        f"While step '{original_name}' missing required field 'do'. "
        f"While loops must have a 'do' block with steps to execute."
    )
```

#### Paso 3: Actualizar node factories

**Archivos a modificar:**
- `src/soni/compiler/nodes/say.py`
- `src/soni/compiler/nodes/collect.py`
- `src/soni/compiler/nodes/action.py`
- `src/soni/compiler/nodes/branch.py`
- `src/soni/compiler/nodes/set.py`
- `src/soni/compiler/nodes/confirm.py`

**Patrón a seguir en cada archivo:**

```python
# Agregar import
from soni.core.errors import ValidationError

# Reemplazar ValueError por ValidationError
# ANTES
if not step.message:
    raise ValueError(f"Step {step.step} of type 'say' missing required field 'message'")

# DESPUÉS
if not step.message:
    raise ValidationError(
        f"Step '{step.step}' of type 'say' is missing required field 'message'"
    )
```

**Nota:** Usar `ValidationError` para campos faltantes porque es un error de validación de la configuración, no de la construcción del grafo.

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/compiler/test_error_types.py`

**Failing tests to write FIRST:**

```python
import pytest
from soni.core.errors import GraphBuildError, ValidationError
from soni.compiler.factory import NodeFactoryRegistry
from soni.compiler.subgraph import SubgraphBuilder
from soni.config.steps import StepConfig


class TestFactoryErrorTypes:
    """Tests for error types in factory module."""

    def test_unknown_step_type_raises_graph_build_error(self):
        """Test that unknown step type raises GraphBuildError, not ValueError."""
        with pytest.raises(GraphBuildError) as exc_info:
            NodeFactoryRegistry.get("nonexistent_type")

        assert "Unknown step type" in str(exc_info.value)
        assert "nonexistent_type" in str(exc_info.value)

    def test_unknown_step_type_includes_available_types(self):
        """Test that error message includes available step types."""
        with pytest.raises(GraphBuildError) as exc_info:
            NodeFactoryRegistry.get("invalid")

        # Should mention some valid types
        error_msg = str(exc_info.value)
        assert "say" in error_msg or "collect" in error_msg


class TestSubgraphErrorTypes:
    """Tests for error types in subgraph module."""

    def test_while_missing_condition_raises_graph_build_error(self):
        """Test that while step without condition raises GraphBuildError."""
        from soni.config.models import FlowConfig

        # Create flow with invalid while step
        flow_config = FlowConfig(
            name="test_flow",
            description="Test",
            steps=[
                StepConfig(step="loop", type="while", do=["say_hello"])
                # Missing condition!
            ]
        )

        builder = SubgraphBuilder(config=None)

        with pytest.raises(GraphBuildError) as exc_info:
            builder.build(flow_config)

        assert "condition" in str(exc_info.value).lower()

    def test_while_missing_do_raises_graph_build_error(self):
        """Test that while step without do block raises GraphBuildError."""
        from soni.config.models import FlowConfig

        flow_config = FlowConfig(
            name="test_flow",
            description="Test",
            steps=[
                StepConfig(step="loop", type="while", condition="slots.count < 3")
                # Missing do!
            ]
        )

        builder = SubgraphBuilder(config=None)

        with pytest.raises(GraphBuildError) as exc_info:
            builder.build(flow_config)

        assert "do" in str(exc_info.value).lower()


class TestNodeFactoryErrorTypes:
    """Tests for error types in individual node factories."""

    def test_say_missing_message_raises_validation_error(self):
        """Test that say step without message raises ValidationError."""
        from soni.compiler.nodes.say import SayNodeFactory

        step = StepConfig(step="greet", type="say")  # Missing message
        factory = SayNodeFactory()

        with pytest.raises(ValidationError) as exc_info:
            factory.create(step, all_steps=[], step_index=0)

        assert "message" in str(exc_info.value).lower()

    def test_collect_missing_slot_raises_validation_error(self):
        """Test that collect step without slot raises ValidationError."""
        from soni.compiler.nodes.collect import CollectNodeFactory

        step = StepConfig(step="get_name", type="collect")  # Missing slot
        factory = CollectNodeFactory()

        with pytest.raises(ValidationError) as exc_info:
            factory.create(step, all_steps=[], step_index=0)

        assert "slot" in str(exc_info.value).lower()

    def test_action_missing_call_raises_validation_error(self):
        """Test that action step without call raises ValidationError."""
        from soni.compiler.nodes.action import ActionNodeFactory

        step = StepConfig(step="do_something", type="action")  # Missing call
        factory = ActionNodeFactory()

        with pytest.raises(ValidationError) as exc_info:
            factory.create(step, all_steps=[], step_index=0)

        assert "call" in str(exc_info.value).lower()

    def test_branch_missing_cases_raises_validation_error(self):
        """Test that branch step without cases raises ValidationError."""
        from soni.compiler.nodes.branch import BranchNodeFactory

        step = StepConfig(step="check", type="branch", evaluate="slots.value")
        # Missing cases!
        factory = BranchNodeFactory()

        with pytest.raises(ValidationError) as exc_info:
            factory.create(step, all_steps=[], step_index=0)

        assert "cases" in str(exc_info.value).lower()
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/compiler/test_error_types.py -v
# Expected: FAILED (raises ValueError instead of specific types)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for compiler error types"
```

#### Green Phase: Make Tests Pass

See "Implementación Detallada" section for implementation steps.

**Verify tests pass:**
```bash
uv run pytest tests/unit/compiler/test_error_types.py -v
# Expected: PASSED
```

**Commit:**
```bash
git add src/ tests/
git commit -m "fix: use domain-specific error types in compiler module

- Replace ValueError with GraphBuildError in factory.py
- Replace ValueError with GraphBuildError in subgraph.py
- Replace ValueError with ValidationError in node factories
- Improve error messages with more context"
```

#### Refactor Phase: Improve Design

- Ensure error messages are consistent in format
- Consider creating error message templates
- Tests must still pass!

**Commit:**
```bash
git add src/
git commit -m "refactor: standardize error messages in compiler"
```

### Criterios de Éxito

- [ ] No hay `raise ValueError` en el módulo compiler
- [ ] `GraphBuildError` usado para errores de construcción de grafo
- [ ] `ValidationError` usado para campos faltantes/inválidos
- [ ] Mensajes de error son descriptivos e incluyen contexto
- [ ] Todos los tests pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Verificar que no hay ValueError en compiler
grep -r "raise ValueError" src/soni/compiler/
# Esperado: ningún resultado

# Verificar que los imports están correctos
uv run python -c "from soni.compiler.factory import NodeFactoryRegistry; NodeFactoryRegistry.get('invalid')"
# Esperado: GraphBuildError

# Ejecutar tests del compiler
uv run pytest tests/unit/compiler/ -v
```

**Resultado esperado:**
- grep no encuentra ValueError
- Import test muestra GraphBuildError
- Todos los tests pasan

### Referencias

- `src/soni/core/errors.py` - Definición de errores del dominio
- `src/soni/compiler/` - Módulo a modificar
- Python Exception Hierarchy best practices

### Notas Adicionales

**Patrón de mensajes de error:**
```
"{ComponentType} '{name}' {problem}. {suggestion/context}."

Ejemplos:
- "Step 'greet' of type 'say' is missing required field 'message'"
- "Unknown step type: 'invalid'. Available types: ['say', 'collect', 'action', 'branch']"
- "While step 'loop' missing required field 'condition'. While loops must have a condition to evaluate."
```

**Beneficios:**
- Manejo de errores más específico posible
- Mensajes de error más útiles para debugging
- Consistencia con el resto del sistema
