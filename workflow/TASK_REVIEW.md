# Revision de Tareas del Backlog

**Fecha de revision**: 2025-12-16
**Revisor**: Claude (AI Assistant)
**Estado**: Analisis completo con recomendaciones

---

## Resumen Ejecutivo

| Categoria | Estado | Puntuacion |
|-----------|--------|------------|
| **Estructura TDD** | Bueno | 8/10 |
| **Formato AAA** | Parcial | 6/10 |
| **Principios SOLID** | Bueno | 7/10 |
| **Patrones de Diseno** | Bueno | 8/10 |
| **DRY** | Necesita mejoras | 5/10 |
| **Claridad de implementacion** | Muy bueno | 9/10 |

**Veredicto General**: Las tareas estan bien estructuradas pero necesitan ajustes para alcanzar la calidad deseada.

---

## Analisis Detallado por Tarea

### Task 000 - Archive Codebase

**Estado**: ✅ Correcto

**Positivo**:
- Justificacion clara de por que no aplica TDD
- Pasos de validacion manual bien definidos
- Referencia a REWRITE_PLAN.md

**Sin problemas significativos** - Es una tarea de setup.

---

### Task 001 - Core Types

**Estado**: ⚠️ Necesita ajustes

**Positivo**:
- TypedDicts correctamente definidos
- Factory function `create_empty_dialogue_state()`
- Tests basicos presentes

**Problemas identificados**:

#### 1. Violacion de SRP en `types.py`

El archivo mezcla:
- TypedDicts (tipos)
- Factory function (comportamiento)
- Reducers de LangGraph (infraestructura)

**Recomendacion**:
```python
# Separar en:
# core/types.py      - Solo TypedDicts
# core/state.py      - Factory functions y helpers
# core/reducers.py   - Reducers de LangGraph (si aplica)
```

#### 2. Tests AAA incompletos

Los tests no siguen AAA estrictamente:

```python
# ACTUAL (001-core-types.md linea 147-154)
def test_create_empty_dialogue_state_returns_valid_structure(self):
    # Act  <-- Falta Arrange
    state = create_empty_dialogue_state()

    # Assert
    assert state["flow_stack"] == []

# RECOMENDADO
def test_create_empty_dialogue_state_returns_valid_structure(self):
    # Arrange
    # (No setup needed - documenting this explicitly)

    # Act
    state = create_empty_dialogue_state()

    # Assert
    assert state["flow_stack"] == []
    assert state["flow_slots"] == {}
    # ... mas assertions
```

#### 3. Falta test de inmutabilidad

```python
# ANADIR
def test_dialogue_state_modifications_are_isolated(self):
    """
    GIVEN two dialogue states created separately
    WHEN one is modified
    THEN the other is not affected
    """
    # Arrange
    state1 = create_empty_dialogue_state()
    state2 = create_empty_dialogue_state()

    # Act
    state1["flow_stack"].append({"flow_id": "test"})

    # Assert
    assert len(state2["flow_stack"]) == 0  # Not affected
```

---

### Task 002 - Commands

**Estado**: ⚠️ Necesita ajustes

**Positivo**:
- Jerarquia de comandos bien definida
- Serializacion/deserializacion implementada
- Discriminator pattern correcto

**Problemas identificados**:

#### 1. Violacion de OCP en `parse_command()`

El map de comandos esta hardcodeado:

```python
# ACTUAL (problematico)
def parse_command(data: dict) -> Command:
    command_map = {
        "start_flow": StartFlow,
        "cancel_flow": CancelFlow,
        # ... cada nuevo comando requiere modificar aqui
    }
```

**Recomendacion** - Usar registro automatico:

```python
# RECOMENDADO - Registry pattern con decorador
from typing import ClassVar

class Command(BaseModel):
    command_type: str = "base"
    _registry: ClassVar[dict[str, type["Command"]]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Auto-registrar subclases
        if hasattr(cls, "command_type") and cls.command_type != "base":
            Command._registry[cls.model_fields["command_type"].default] = cls

    @classmethod
    def parse(cls, data: dict) -> "Command":
        command_type = data.get("type", "base")
        cmd_class = cls._registry.get(command_type, Command)
        return cmd_class(**{k: v for k, v in data.items() if k != "type"})
```

#### 2. Tests no cubren edge cases

```python
# ANADIR tests para:
def test_parse_command_with_missing_required_field_raises_validation_error():
    """StartFlow sin flow_name debe fallar."""

def test_parse_command_with_extra_fields_ignores_them():
    """Campos extra no deben causar errores."""

def test_command_equality_by_value():
    """Dos comandos con mismos valores son iguales."""
```

---

### Task 003 - Errors and Config

**Estado**: ⚠️ Necesita ajustes significativos

**Positivo**:
- Jerarquia de errores clara
- Carga de YAML basica

**Problemas identificados**:

#### 1. Violacion de SRP - Config hace demasiado

`SoniConfig.load()` mezcla:
- Lectura de archivo (I/O)
- Parsing YAML
- Validacion

**Recomendacion** - Separar responsabilidades:

```python
# core/config.py - Solo modelos
class SoniConfig(BaseModel):
    version: str = "1.0"
    flows: dict[str, FlowConfig] = Field(default_factory=dict)

# core/loader.py - Carga de archivos
class ConfigLoader:
    """Loads configuration from various sources."""

    @staticmethod
    def from_yaml(path: Path) -> SoniConfig:
        """Load from YAML file."""
        if not path.exists():
            raise ConfigError(f"Config not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        return SoniConfig.model_validate(data)

    @staticmethod
    def from_dict(data: dict) -> SoniConfig:
        """Load from dictionary (for testing)."""
        return SoniConfig.model_validate(data)
```

#### 2. Errores sin contexto suficiente

```python
# ACTUAL
class FlowStackError(FlowError):
    pass

# RECOMENDADO - Errores con contexto
class FlowStackError(FlowError):
    """Error in flow stack operations."""

    def __init__(
        self,
        message: str,
        stack_size: int = 0,
        operation: str = "unknown",
    ):
        self.stack_size = stack_size
        self.operation = operation
        super().__init__(f"{message} (operation={operation}, stack_size={stack_size})")
```

#### 3. Tests insuficientes para config

```python
# ANADIR
def test_config_with_invalid_step_type_raises_validation_error(tmp_path):
    """Step type desconocido debe fallar con mensaje claro."""

def test_config_with_missing_flow_description_raises_error(tmp_path):
    """Description es requerido."""

def test_config_validates_step_references(tmp_path):
    """jump_to a step inexistente debe advertir/fallar."""
```

---

### Task 004 - Flow Manager

**Estado**: ⚠️ Necesita ajustes

**Positivo**:
- FlowManager bien enfocado
- Operaciones de stack claras
- Tests para casos basicos

**Problemas identificados**:

#### 1. Type hint incorrecto

```python
# ACTUAL (linea 89, 103)
def set_slot(self, state, slot_name: str, value: any) -> None:  # 'any' minuscula!
def get_slot(self, state, slot_name: str) -> any:

# CORRECTO
def set_slot(self, state: DialogueState, slot_name: str, value: Any) -> None:
def get_slot(self, state: DialogueState, slot_name: str) -> Any:
```

#### 2. Falta validacion de step advancement

```python
# ANADIR metodo
def advance_step(self, state: DialogueState) -> bool:
    """Advance to next step in current flow.

    Returns True if advanced, False if flow complete.
    """
    context = self.get_active_context(state)
    if not context:
        return False

    context["step_index"] += 1
    return True
```

#### 3. Tests AAA no consistentes

```python
# ACTUAL (linea 124-134) - Bien estructurado

# PERO linea 149-156 - Falta docstring
def test_pop_flow_on_empty_stack_raises_error(self):
    # Arrange  <-- Falta GIVEN/WHEN/THEN docstring
    state = create_empty_dialogue_state()
    manager = FlowManager()

    # Act & Assert  <-- Combinar Act y Assert es aceptable para excepciones
    with pytest.raises(FlowStackError):
        manager.pop_flow(state)

# RECOMENDADO
def test_pop_flow_on_empty_stack_raises_error(self):
    """
    GIVEN an empty flow stack
    WHEN pop_flow is called
    THEN FlowStackError is raised
    """
    # Arrange
    state = create_empty_dialogue_state()
    manager = FlowManager()

    # Act & Assert
    with pytest.raises(FlowStackError) as exc_info:
        manager.pop_flow(state)

    assert "empty" in str(exc_info.value).lower()
```

#### 4. Falta test de slots aislados por flow

```python
# ANADIR
def test_slots_are_isolated_between_flows(self):
    """
    GIVEN two flows on the stack
    WHEN setting a slot in the top flow
    THEN the bottom flow's slots are not affected
    """
    # Arrange
    state = create_empty_dialogue_state()
    manager = FlowManager()
    flow_id_1 = manager.push_flow(state, "flow_1")
    flow_id_2 = manager.push_flow(state, "flow_2")

    # Act
    manager.set_slot(state, "origin", "Madrid")

    # Assert
    assert state["flow_slots"][flow_id_2]["origin"] == "Madrid"
    assert "origin" not in state["flow_slots"].get(flow_id_1, {})
```

---

### Task 005 - Node Factories

**Estado**: ✅ Mayormente correcto

**Positivo**:
- Protocol pattern para NodeFactory
- Una factory por tipo (SRP)
- Dependency Injection via Runtime

**Problemas identificados**:

#### 1. Inconsistencia en signature de `create()`

```python
# base.py dice:
def create(self, step: StepConfig, context: Any) -> NodeFunction:

# collect.py dice:
def create(self, step: StepConfig) -> NodeFunction:  # Sin context!

# RECOMENDACION: Unificar
def create(self, step: StepConfig) -> NodeFunction:
    # Context se inyecta via Runtime en el nodo, no en create()
```

#### 2. Test mock incompleto

```python
# ACTUAL (linea 100-101)
mock_context = {"flow_manager": MockFlowManager(slots={})}

# PROBLEMA: MockFlowManager no esta definido en la tarea

# ANADIR en tests/conftest.py o tests/mocks.py
class MockFlowManager:
    def __init__(self, slots: dict | None = None):
        self._slots = slots or {}

    def get_slot(self, state, slot_name: str) -> Any:
        return self._slots.get(slot_name)

    def set_slot(self, state, slot_name: str, value: Any) -> None:
        self._slots[slot_name] = value
```

---

### Task 006 - Subgraph Builder

**Estado**: ⚠️ Necesita ajustes

**Positivo**:
- Estructura clara
- Manejo de diferentes tipos de edges

**Problemas identificados**:

#### 1. Metodos privados sin implementar

```python
# ACTUAL - Referencias a metodos no definidos:
self._add_branch_edges(builder, name, step, next_step)
self._add_while_edges(builder, name, step, next_step)
self._add_waiting_edges(builder, name, next_step)

# NECESARIO: Implementar estos metodos en la tarea
```

#### 2. Funcion `get_factory_for_step` no definida

```python
# ACTUAL (linea 54)
factory = get_factory_for_step(step.type)

# NECESARIO: Definir en compiler/nodes/__init__.py
def get_factory_for_step(step_type: str) -> NodeFactory:
    """Get the appropriate factory for a step type."""
    factories = {
        "collect": CollectNodeFactory(),
        "action": ActionNodeFactory(),
        "branch": BranchNodeFactory(),
        "confirm": ConfirmNodeFactory(),
        "say": SayNodeFactory(),
        "while": WhileNodeFactory(),
    }

    factory = factories.get(step_type)
    if not factory:
        raise ValueError(f"Unknown step type: {step_type}")

    return factory
```

#### 3. Tests no verifican estructura del grafo

```python
# ACTUAL - Solo verifica que compila
compiled = graph.compile()
assert compiled is not None

# RECOMENDADO - Verificar estructura
def test_build_linear_flow_creates_sequential_edges(self):
    # ...
    graph = builder.build(config)
    compiled = graph.compile()

    # Verificar nodos existen
    assert "a" in compiled.nodes
    assert "b" in compiled.nodes

    # Verificar edges (si LangGraph lo permite)
    # O ejecutar el grafo y verificar orden de ejecucion
```

---

### Task 007 - Orchestrator

**Estado**: ⚠️ Necesita ajustes

**Positivo**:
- Arquitectura correcta (understand -> execute -> flow -> respond)
- Uso de context_schema para DI

**Problemas identificados**:

#### 1. Mezcla de responsabilidades

El OrchestratorGraph hace:
- Compilar flows
- Construir grafo
- Definir routing

**Recomendacion** - Separar:

```python
# dm/orchestrator.py - Solo orquestacion
class OrchestratorGraph:
    def __init__(self, flow_subgraphs: dict[str, StateGraph]):
        self.flow_subgraphs = flow_subgraphs  # Ya compilados

    def build(self) -> StateGraph:
        # Solo construir el grafo orquestador

# dm/builder.py - Construccion completa
def build_orchestrator(config: SoniConfig, context: RuntimeContext) -> CompiledGraph:
    # 1. Compilar flows
    compiler = SubgraphBuilder(context)
    subgraphs = {name: compiler.build(flow) for name, flow in config.flows.items()}

    # 2. Construir orquestador
    orchestrator = OrchestratorGraph(subgraphs)
    return orchestrator.build().compile()
```

#### 2. Edges desde flows incompletos

```python
# ACTUAL (linea 79-80)
for flow_name in self.flow_subgraphs:
    builder.add_edge(f"flow_{flow_name}", "respond")

# PROBLEMA: Los flows pueden necesitar routing condicional
# (ej: flow completo -> respond, flow esperando input -> END temporal)

# RECOMENDADO: Conditional edges desde flows
def _route_after_flow(state: DialogueState) -> str:
    if state.get("flow_state") == "waiting_input":
        return END  # Pausar para input
    return "respond"

for flow_name in self.flow_subgraphs:
    builder.add_conditional_edges(
        f"flow_{flow_name}",
        _route_after_flow,
        {END: END, "respond": "respond"}
    )
```

---

### Task 008 - Dialogue Understanding

**Estado**: ✅ Muy bien estructurado

**Positivo**:
- Modelos Pydantic bien definidos
- Uso de `.acall()` nativo (no asyncify)
- Rich descriptions en InputFields
- MIPROv2 optimizer incluido
- Tests con Mock LM

**Problemas menores**:

#### 1. Falta `available_commands` en tests

```python
# ACTUAL - Tests no incluyen available_commands en contexto
context = DialogueContext(
    available_flows=[...],
    conversation_state="idle",
)

# RECOMENDADO - Incluir para ser mas realista
context = DialogueContext(
    available_flows=[...],
    available_commands=[
        CommandInfo(
            command_type="start_flow",
            description="Start a new flow",
            required_fields=["flow_name"],
        ),
        CommandInfo(
            command_type="set_slot",
            description="Set a slot value",
            required_fields=["slot_name", "slot_value"],
        ),
    ],
    conversation_state="idle",
)
```

#### 2. Tests dependen de LLM real

```python
# RECOMENDADO - Configurar Mock LM en conftest.py
@pytest.fixture
def mock_lm():
    """Configure DSPy with mock LM for testing."""
    import dspy

    class MockLM(dspy.LM):
        def __call__(self, prompt, **kwargs):
            # Return structured response based on input patterns
            if "book a flight" in prompt.lower():
                return '{"commands": [{"command_type": "start_flow", "flow_name": "book_flight"}]}'
            # ...

    dspy.configure(lm=MockLM())
    yield
    dspy.configure(lm=None)
```

---

### Task 009 - Runtime Loop

**Estado**: ⚠️ Necesita ajustes

**Positivo**:
- Estructura basica correcta
- Multi-user support planificado

**Problemas identificados**:

#### 1. Mezcla de inicializacion lazy y eager

```python
# ACTUAL - Inconsistente
def __init__(self, config):
    self.du = SoniDU()  # Eager - crea inmediatamente
    self.graph = None   # Lazy - crea despues

# RECOMENDADO - Todo lazy o todo eager
class RuntimeLoop:
    def __init__(self, config: SoniConfig):
        self.config = config
        self._graph: CompiledGraph | None = None
        self._du: SoniDU | None = None
        self._flow_manager: FlowManager | None = None

    @property
    def graph(self) -> CompiledGraph:
        if self._graph is None:
            raise RuntimeError("Call initialize() first")
        return self._graph
```

#### 2. `_get_or_create_state` incompleto

```python
# ACTUAL (linea 87-92)
async def _get_or_create_state(self, user_id: str) -> DialogueState:
    if self.checkpointer:
        # Try to load from checkpointer
        pass  # <-- No implementado!
    return create_empty_dialogue_state()

# NECESARIO implementar o marcar como TODO explicito
```

#### 3. Tests no verifican estado real

```python
# ACTUAL (linea 132-134)
state = await runtime._get_or_create_state("user1")
# State should persist  <-- Comentario, no assertion!

# RECOMENDADO
async def test_state_persists_between_messages(self):
    # Arrange
    config = SoniConfig(flows={})
    runtime = RuntimeLoop(config)
    await runtime.initialize()

    # Act
    await runtime.process_message("First", user_id="user1")
    await runtime.process_message("Second", user_id="user1")

    # Assert - Verificar turn_count
    state = await runtime.graph.aget_state({"configurable": {"thread_id": "user1"}})
    assert state.values.get("turn_count", 0) == 2
```

---

### Task 010 - Actions and Integration

**Estado**: ⚠️ Necesita ajustes

**Positivo**:
- Registry pattern correcto
- Decorator para registro
- E2E test planificado

**Problemas identificados**:

#### 1. Falta validacion de inputs en ActionHandler

```python
# ACTUAL - Pasa todos los inputs directamente
result = await action(**inputs)

# PROBLEMA: Puede fallar con KeyError si faltan inputs

# RECOMENDADO - Validar o usar signature inspection
async def execute(self, action_name: str, inputs: dict) -> dict:
    action = self.registry.get(action_name)
    if not action:
        raise ActionError(f"Action '{action_name}' not found")

    # Opcion 1: Let Pydantic validate if action uses typed params
    # Opcion 2: Inspect signature and validate
    import inspect
    sig = inspect.signature(action)
    required_params = [
        p.name for p in sig.parameters.values()
        if p.default is inspect.Parameter.empty and p.name not in ("self", "kwargs")
    ]

    missing = [p for p in required_params if p not in inputs]
    if missing:
        raise ActionError(f"Action '{action_name}' missing required inputs: {missing}")

    # Filter to only pass known parameters
    valid_inputs = {k: v for k, v in inputs.items() if k in sig.parameters}
    return await action(**valid_inputs)
```

#### 2. E2E test demasiado vago

```python
# ACTUAL (linea 111)
assert "Paris" in r3 or "flight" in r3.lower()  # Muy permisivo

# RECOMENDADO - Mas especifico
async def test_complete_booking_flow(self):
    # ... setup ...

    # Act - Flujo completo
    r1 = await framework.run_async("Book a flight to Paris")
    assert "where" in r1.lower() or "origin" in r1.lower()  # Pide origen

    r2 = await framework.run_async("From Madrid")
    assert "when" in r2.lower() or "date" in r2.lower()  # Pide fecha

    r3 = await framework.run_async("Tomorrow")
    assert "confirm" in r3.lower()  # Pide confirmacion

    r4 = await framework.run_async("Yes")
    assert "booked" in r4.lower() or "confirmed" in r4.lower()
```

---

## Problemas Transversales (DRY)

### 1. Duplicacion de factory functions

Cada test crea estados manualmente:

```python
# Aparece en multiples tareas:
state = {
    "flow_stack": [],
    "flow_slots": {},
    # ... misma estructura repetida
}
```

**Solucion**: Centralizar en `tests/factories.py` (ya propuesto en 000 pero no usado consistentemente)

### 2. Duplicacion de mocks

MockFlowManager, MockActionHandler, etc. no estan centralizados.

**Solucion**: Crear `tests/mocks/` con mocks reutilizables:

```
tests/
├── mocks/
│   ├── __init__.py
│   ├── flow_manager.py
│   ├── action_handler.py
│   └── du.py
```

### 3. Configuraciones de test repetidas

```python
# Repetido en cada test async
@pytest.mark.asyncio
async def test_...
```

**Solucion**: Configurar en `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"  # Todos los tests async automaticamente
```

---

## Recomendaciones Finales

### Prioridad Alta (Hacer antes de implementar)

1. **Corregir type hints** (`any` -> `Any`) en Task 004
2. **Implementar metodos faltantes** en Task 006
3. **Centralizar mocks y factories** para DRY
4. **Completar `_get_or_create_state`** en Task 009

### Prioridad Media (Mejora de calidad)

5. **Separar SRP** en Tasks 001, 003, 007
6. **Usar registry pattern** para Commands (Task 002)
7. **Anadir tests de edge cases** en todas las tareas
8. **Docstrings GIVEN/WHEN/THEN** consistentes

### Prioridad Baja (Nice to have)

9. **Errores con contexto** (Task 003)
10. **Validacion de inputs en Actions** (Task 010)
11. **Configurar asyncio_mode auto** en pytest

---

## Checklist de Revision Pre-Implementacion

Antes de empezar cada tarea, verificar:

- [ ] Type hints correctos (Any, not any)
- [ ] Tests siguen formato AAA estricto
- [ ] Docstrings con GIVEN/WHEN/THEN
- [ ] Mocks definidos o referenciados
- [ ] Edge cases cubiertos
- [ ] No hay codigo duplicado con otras tareas
- [ ] Metodos privados estan implementados
- [ ] Imports explicitamente listados

---

**Documento generado por**: Claude (AI Assistant)
**Para**: Revision de calidad pre-implementacion
