## Task: 006 - Migrate StepConfig to Discriminated Unions

**ID de tarea:** 006
**Hito:** 2 - Quality Improvements
**Dependencias:** Task-005 (validation utilities)
**Duración estimada:** 8 horas
**Prioridad:** MEDIA

### Objetivo

Migrar de `GenericStepConfig` (que acepta todos los campos opcionalmente) a un sistema de discriminated unions con Pydantic v2, proporcionando type safety completo y validación en tiempo de configuración.

### Contexto

El archivo `config/steps.py` contiene un comentario de deuda técnica documentando un intento fallido:

```python
# TODO(tech-debt): Eliminate GenericStepConfig in favor of pure discriminated unions
# ATTEMPTED: 2024-12-18
# RESULT: 226 mypy errors, reverted to maintain functionality.
```

**Problema actual:**
```python
class GenericStepConfig(BaseModel):
    step: str
    type: str
    slot: str | None = None      # Solo para collect, set
    message: str | None = None   # Solo para say
    call: str | None = None      # Solo para action
    cases: dict | None = None    # Solo para branch
    # ... 11 más campos opcionales
```

**Por qué es problemático:**
1. No hay validación de campos requeridos por tipo
2. Sin autocompletado IDE específico por tipo
3. Errores se descubren en runtime, no en parsing
4. Todos los campos son opcionales aunque sean requeridos

### Entregables

- [ ] Crear modelos específicos por tipo de step (SayStepConfig, CollectStepConfig, etc.)
- [ ] Implementar discriminated union con `Literal` type
- [ ] Migrar SubgraphBuilder para usar type narrowing
- [ ] Actualizar todos los imports y usos
- [ ] Mantener backward compatibility en parsing YAML
- [ ] Resolver errores de mypy

### Implementación Detallada

#### Paso 1: Crear modelos específicos por tipo

**Archivo a modificar:** `src/soni/config/steps.py`

**Código específico:**

```python
"""Step configuration models with discriminated unions.

Each step type has its own model with required fields properly typed.
The StepConfig union allows Pydantic to discriminate based on 'type' field.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class BaseStepConfig(BaseModel):
    """Base configuration shared by all step types."""

    step: str = Field(description="Unique step identifier within the flow")
    jump_to: str | None = Field(default=None, description="Step to jump to after this one")


class SayStepConfig(BaseStepConfig):
    """Configuration for 'say' steps that display messages."""

    type: Literal["say"]
    message: str = Field(description="Message template to display (supports {slot} interpolation)")


class CollectStepConfig(BaseStepConfig):
    """Configuration for 'collect' steps that gather slot values."""

    type: Literal["collect"]
    slot: str = Field(description="Name of the slot to fill")
    prompt: str | None = Field(default=None, description="Prompt message for the slot")
    utter: str | None = Field(default=None, description="Alternative to prompt")
    validation: str | None = Field(default=None, description="Validation function name")


class ActionStepConfig(BaseStepConfig):
    """Configuration for 'action' steps that execute Python functions."""

    type: Literal["action"]
    call: str = Field(description="Action function name to execute")
    args: dict[str, Any] | None = Field(default=None, description="Arguments to pass")
    result_slot: str | None = Field(default=None, description="Slot to store result")


class BranchStepConfig(BaseStepConfig):
    """Configuration for 'branch' steps that implement conditional logic."""

    type: Literal["branch"]
    evaluate: str = Field(description="Expression to evaluate")
    cases: dict[str, str] = Field(description="Mapping of values to target steps")
    default: str | None = Field(default=None, description="Default step if no case matches")


class SetStepConfig(BaseStepConfig):
    """Configuration for 'set' steps that assign slot values."""

    type: Literal["set"]
    slot: str = Field(description="Slot name to set")
    value: Any = Field(description="Value to assign (can be expression)")


class ConfirmStepConfig(BaseStepConfig):
    """Configuration for 'confirm' steps that request user confirmation."""

    type: Literal["confirm"]
    prompt: str = Field(description="Confirmation prompt message")
    confirm: str | None = Field(default=None, description="Step on confirmation")
    deny: str | None = Field(default=None, description="Step on denial")


class WhileStepConfig(BaseStepConfig):
    """Configuration for 'while' steps that implement loops."""

    type: Literal["while"]
    condition: str = Field(description="Loop condition expression")
    do: list[str] = Field(description="Steps to execute in loop body")
    exit_to: str | None = Field(default=None, description="Step after loop exits")


# Discriminated Union - Pydantic will parse based on 'type' field
StepConfig = Annotated[
    SayStepConfig
    | CollectStepConfig
    | ActionStepConfig
    | BranchStepConfig
    | SetStepConfig
    | ConfirmStepConfig
    | WhileStepConfig,
    Field(discriminator="type"),
]

# Type alias for list of steps (common pattern)
StepList = list[StepConfig]


# Backward compatibility - will be removed in future version
GenericStepConfig = BaseStepConfig  # Deprecated alias
```

#### Paso 2: Actualizar FlowConfig para usar nueva union

**Archivo a modificar:** `src/soni/config/models.py`

```python
from soni.config.steps import StepConfig, StepList

class FlowConfig(BaseModel):
    """Configuration for a single flow."""

    name: str
    description: str | None = None
    trigger_examples: list[str] = Field(default_factory=list)
    steps: StepList  # Usa el type alias
```

#### Paso 3: Actualizar SubgraphBuilder con type narrowing

**Archivo a modificar:** `src/soni/compiler/subgraph.py`

```python
from soni.config.steps import (
    StepConfig,
    SayStepConfig,
    CollectStepConfig,
    ActionStepConfig,
    BranchStepConfig,
    SetStepConfig,
    ConfirmStepConfig,
    WhileStepConfig,
)


def _transform_while_loops(
    self, steps: list[StepConfig]
) -> tuple[list[StepConfig], dict[str, str]]:
    """Transform while loops into branch + jump_to patterns."""
    result: list[StepConfig] = []
    name_mappings: dict[str, str] = {}

    for step in steps:
        if isinstance(step, WhileStepConfig):
            # Type narrowing: step is now WhileStepConfig
            # All fields are available with proper types
            guard_name = f"__{step.step}_guard"
            body_name = f"__{step.step}_body"

            # Create guard step
            guard = BranchStepConfig(
                step=guard_name,
                type="branch",
                evaluate=step.condition,  # Now typed as str, not str | None
                cases={"true": body_name, "false": step.exit_to or "END"},
            )
            # ... resto de la transformación
        else:
            result.append(step)

    return result, name_mappings
```

#### Paso 4: Actualizar node factories con type narrowing

**Ejemplo para SayNodeFactory:**

```python
from soni.config.steps import SayStepConfig, StepConfig


class SayNodeFactory(NodeFactory):
    def create(
        self,
        step: StepConfig,  # Union type
        all_steps: list[StepConfig],
        step_index: int
    ):
        # Type guard - narrow to specific type
        if not isinstance(step, SayStepConfig):
            raise ValidationError(
                f"SayNodeFactory received wrong step type: {type(step).__name__}"
            )

        # Now step is SayStepConfig - message is str, not str | None
        message = step.message  # No validation needed!

        async def say_node(state: DialogueState, config: RunnableConfig) -> dict[str, Any]:
            # ... implementation
            pass

        return say_node
```

#### Paso 5: Actualizar ConfigLoader para manejar parsing

**Archivo a modificar:** `src/soni/config/loader.py`

El parsing debería funcionar automáticamente gracias al discriminator de Pydantic. Verificar que errores de parsing son claros:

```python
def from_yaml(self, path: Path) -> SoniConfig:
    """Load configuration from YAML file."""
    data = self._load(path)

    try:
        return SoniConfig(**data)
    except ValidationError as e:
        # Improve error message for step type issues
        for error in e.errors():
            if "discriminator" in str(error.get("type", "")):
                raise ConfigError(
                    f"Invalid step type in flow configuration. "
                    f"Each step must have a valid 'type' field. "
                    f"Error: {error['msg']}"
                ) from e
        raise ConfigError(f"Configuration validation failed: {e}") from e
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/config/test_step_discriminated_union.py`

```python
import pytest
from pydantic import ValidationError as PydanticValidationError

from soni.config.steps import (
    StepConfig,
    SayStepConfig,
    CollectStepConfig,
    ActionStepConfig,
    BranchStepConfig,
)


class TestStepConfigDiscriminator:
    """Tests for discriminated union step parsing."""

    def test_say_step_parses_correctly(self):
        """Test that say step with message parses to SayStepConfig."""
        data = {"step": "greet", "type": "say", "message": "Hello!"}

        # Parse through Pydantic adapter
        from pydantic import TypeAdapter
        adapter = TypeAdapter(StepConfig)
        result = adapter.validate_python(data)

        assert isinstance(result, SayStepConfig)
        assert result.message == "Hello!"

    def test_collect_step_parses_correctly(self):
        """Test that collect step parses to CollectStepConfig."""
        data = {"step": "get_name", "type": "collect", "slot": "name"}

        from pydantic import TypeAdapter
        adapter = TypeAdapter(StepConfig)
        result = adapter.validate_python(data)

        assert isinstance(result, CollectStepConfig)
        assert result.slot == "name"

    def test_say_step_requires_message(self):
        """Test that say step without message raises validation error."""
        data = {"step": "greet", "type": "say"}  # Missing message!

        from pydantic import TypeAdapter
        adapter = TypeAdapter(StepConfig)

        with pytest.raises(PydanticValidationError) as exc_info:
            adapter.validate_python(data)

        assert "message" in str(exc_info.value)

    def test_collect_step_requires_slot(self):
        """Test that collect step without slot raises validation error."""
        data = {"step": "get_name", "type": "collect"}  # Missing slot!

        from pydantic import TypeAdapter
        adapter = TypeAdapter(StepConfig)

        with pytest.raises(PydanticValidationError) as exc_info:
            adapter.validate_python(data)

        assert "slot" in str(exc_info.value)

    def test_unknown_type_raises_error(self):
        """Test that unknown step type raises validation error."""
        data = {"step": "invalid", "type": "nonexistent"}

        from pydantic import TypeAdapter
        adapter = TypeAdapter(StepConfig)

        with pytest.raises(PydanticValidationError) as exc_info:
            adapter.validate_python(data)

        # Should mention discriminator issue
        assert "type" in str(exc_info.value).lower()

    def test_branch_step_requires_cases(self):
        """Test that branch step requires cases dict."""
        data = {
            "step": "check",
            "type": "branch",
            "evaluate": "slots.value > 0",
            # Missing cases!
        }

        from pydantic import TypeAdapter
        adapter = TypeAdapter(StepConfig)

        with pytest.raises(PydanticValidationError) as exc_info:
            adapter.validate_python(data)

        assert "cases" in str(exc_info.value)


class TestStepConfigTypeNarrowing:
    """Tests for type narrowing with isinstance."""

    def test_isinstance_say_step(self):
        """Test that parsed say step passes isinstance check."""
        step = SayStepConfig(step="greet", type="say", message="Hello")

        assert isinstance(step, SayStepConfig)
        # IDE should know step.message is str, not str | None

    def test_isinstance_in_loop(self):
        """Test type narrowing in a processing loop."""
        steps: list[StepConfig] = [
            SayStepConfig(step="greet", type="say", message="Hello"),
            CollectStepConfig(step="get_name", type="collect", slot="name"),
        ]

        for step in steps:
            if isinstance(step, SayStepConfig):
                # Type narrowed to SayStepConfig
                assert step.message is not None
            elif isinstance(step, CollectStepConfig):
                # Type narrowed to CollectStepConfig
                assert step.slot is not None


class TestFlowConfigWithDiscriminatedSteps:
    """Tests for FlowConfig using discriminated steps."""

    def test_flow_config_parses_mixed_steps(self):
        """Test that FlowConfig correctly parses mixed step types."""
        from soni.config.models import FlowConfig

        data = {
            "name": "greeting_flow",
            "steps": [
                {"step": "greet", "type": "say", "message": "Hello!"},
                {"step": "get_name", "type": "collect", "slot": "name"},
                {"step": "farewell", "type": "say", "message": "Goodbye {name}!"},
            ],
        }

        flow = FlowConfig(**data)

        assert len(flow.steps) == 3
        assert isinstance(flow.steps[0], SayStepConfig)
        assert isinstance(flow.steps[1], CollectStepConfig)
        assert isinstance(flow.steps[2], SayStepConfig)

    def test_flow_config_rejects_invalid_step(self):
        """Test that FlowConfig rejects flow with invalid step."""
        from soni.config.models import FlowConfig

        data = {
            "name": "bad_flow",
            "steps": [
                {"step": "greet", "type": "say"},  # Missing message!
            ],
        }

        with pytest.raises(PydanticValidationError):
            FlowConfig(**data)
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/config/test_step_discriminated_union.py -v
# Expected: FAILED (GenericStepConfig doesn't validate properly)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for discriminated union step config"
```

#### Green Phase: Make Tests Pass

See "Implementación Detallada" section.

**Verify tests pass:**
```bash
uv run pytest tests/unit/config/test_step_discriminated_union.py -v
uv run mypy src/soni/config/steps.py
# Expected: PASSED, 0 errors
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: implement discriminated union for StepConfig

- Create specific models per step type (SayStepConfig, etc.)
- Implement Pydantic v2 discriminated union with Literal types
- Required fields now validated at parse time
- Full type safety with isinstance narrowing"
```

#### Refactor Phase: Improve Design

- Update all imports across codebase
- Add migration guide in docstring
- Remove deprecated GenericStepConfig
- Tests must still pass!

**Commit:**
```bash
git add src/
git commit -m "refactor: update codebase to use discriminated step configs"
```

### Criterios de Éxito

- [ ] Cada tipo de step tiene su propio modelo con campos requeridos
- [ ] Pydantic valida campos requeridos durante parsing
- [ ] `mypy` pasa sin errores (0 errores vs 226 previos)
- [ ] Type narrowing funciona con `isinstance()`
- [ ] YAML existentes siguen funcionando
- [ ] Todos los tests pasan
- [ ] Linting pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Verificar mypy
uv run mypy src/soni/config/steps.py src/soni/compiler/
# Esperado: 0 errores

# Verificar que YAML existentes funcionan
uv run soni chat --config examples/banking/soni.yaml --module examples.banking.handlers
# Esperado: inicia sin errores

# Verificar que errores de config son claros
echo "flows:
  test:
    name: test
    steps:
      - step: greet
        type: say
        # message missing!
" | uv run python -c "
from soni.config.loader import ConfigLoader
import sys
import yaml
data = yaml.safe_load(sys.stdin)
ConfigLoader().validate(data)
"
# Esperado: Error claro sobre campo 'message' faltante
```

### Referencias

- `src/soni/config/steps.py` - Archivo principal a modificar
- Pydantic v2 discriminated unions: https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions
- PR con intento previo (si existe)

### Notas Adicionales

**Estrategia de migración:**
1. Agregar nuevos modelos junto a GenericStepConfig
2. Actualizar imports gradualmente
3. Ejecutar mypy después de cada cambio
4. Eliminar GenericStepConfig cuando todo esté migrado

**Riesgos:**
- 226 errores mypy en intento previo
- Posibles breaking changes en configs existentes
- Necesita coordinación con otros PRs

**Mitigación:**
- Hacer cambios incrementales
- Mantener backward compatibility temporal
- Tests exhaustivos de parsing YAML
