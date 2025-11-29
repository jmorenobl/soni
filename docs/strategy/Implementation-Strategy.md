# Estrategia de Implementación - Soni Framework

**Proyecto:** Soni - Framework Open Source para Asistentes Conversacionales
**Documento:** Estrategia de Implementación por Hitos
**Fecha:** 29 de Noviembre de 2025
**Versión:** 1.0
**Estado:** Aprobado

---

## Resumen Ejecutivo

Este documento define la estrategia de implementación incremental de Soni Framework, organizada en **hitos medibles** con dependencias claras, validaciones técnicas y criterios de éxito. La estrategia sigue el principio de **MVP First** y **validación temprana** para minimizar riesgos y maximizar aprendizaje.

**Filosofía:** Implementar de forma incremental, validando cada hito antes de avanzar al siguiente.

**Duración Total Estimada:** 11-13 meses hasta v1.0.0

---

## Principios de Implementación

### 1. MVP First
- Priorizar funcionalidad sobre perfección
- Validar con usuarios reales cuanto antes
- Iterar basado en feedback

### 2. Validación Continua
- Cada hito debe tener criterios de éxito medibles
- Tests automatizados desde el inicio
- Experimentos de validación técnica antes de implementar

### 3. Dependencias Explícitas
- No avanzar a un hito si sus dependencias no están validadas
- Documentar bloqueadores claramente
- Tener alternativas para dependencias críticas

### 4. Documentación en Paralelo
- Documentar mientras se implementa
- README actualizado en cada hito
- Ejemplos funcionales como tests

---

## Mapa de Hitos

### Visión General

```
v0.1.0 (MVP) → v0.2.0 (Performance) → v0.3.0 (DSL) → v0.4.0 (Zero-Leakage) → v1.0.0 (Stable)
    3 meses         2 meses             2 meses           3 meses             1-2 meses
```

### Dependencias entre Versiones

```
v0.1.0 ──┐
         ├──> v0.2.0 ──┐
v0.1.0 ──┘             ├──> v0.3.0 ──┐
                       └──> v0.3.0 ──┘
                                         ├──> v0.4.0 ──┐
                                         └──> v0.4.0 ──┘
                                                         └──> v1.0.0
```

---

## Hito 0: Validación Técnica Pre-Desarrollo

**Duración:** 1-2 semanas
**Estado:** ⚠️ **CRÍTICO - HACER PRIMERO**

### Objetivo
Validar que las tecnologías core (DSPy, LangGraph) funcionan para el caso de uso antes de invertir meses de desarrollo.

### Tareas

#### 0.1 Validación DSPy Optimization
**Objetivo:** Confirmar que MIPROv2 mejora accuracy en extracción de intents/entities

**Experimento:**
```python
# experiments/01_dspy_validation.py
# Ver sección 6.1 del Viability Analysis
```

**Criterios de Éxito:**
- [ ] Optimización completa sin errores
- [ ] Mejora medible en accuracy (≥5%)
- [ ] Tiempo de optimización < 10 minutos
- [ ] Módulo optimizado serializable (`.save()`)

**Bloqueador:** Si DSPy no mejora accuracy, reconsiderar arquitectura.

#### 0.2 Validación LangGraph Streaming
**Objetivo:** Confirmar streaming async funciona con FastAPI

**Experimento:**
```python
# experiments/02_langgraph_streaming.py
# Ver sección 6.2 del Viability Analysis
```

**Criterios de Éxito:**
- [ ] Streaming funciona sin errores
- [ ] Chunks llegan en orden correcto
- [ ] Compatible con SSE (Server-Sent Events)
- [ ] Latencia first-token < 500ms

**Bloqueador:** Si streaming no funciona, buscar alternativas.

#### 0.3 Validación Persistencia Async
**Objetivo:** Confirmar checkpointing con aiosqlite funciona

**Experimento:**
```python
# experiments/03_async_persistence.py
# Ver sección 6.3 del Viability Analysis
```

**Criterios de Éxito:**
- [ ] Estado persiste entre invocaciones
- [ ] Múltiples conversaciones simultáneas funcionan
- [ ] No hay race conditions
- [ ] Performance aceptable (<100ms por operación)

**Bloqueador:** Si persistencia falla, evaluar alternativas (PostgreSQL, Redis).

### Deliverables
- [ ] 3 scripts de validación ejecutados y documentados
- [ ] Reporte de resultados con métricas
- [ ] Decisión GO/NO-GO documentada

### Decisión de Continuación
**GO si:**
- Las 3 validaciones pasan
- Métricas cumplen criterios

**NO-GO si:**
- Alguna validación crítica falla
- No hay alternativa viable

---

## Hito 1: Setup de Proyecto y Arquitectura Base

**Duración:** 1 semana
**Dependencias:** Hito 0 completado
**Versión Objetivo:** Pre-v0.1.0

### Objetivo
Establecer estructura del proyecto, tooling básico y arquitectura de paquetes.

### Tareas

#### 1.1 Setup de Repositorio
- [ ] Crear repo GitHub (`soni-framework`)
- [ ] Configurar `.gitignore` (Python, IDEs, OS)
- [ ] Licencia MIT
- [ ] README básico con visión

#### 1.2 Gestión de Dependencias
- [ ] Inicializar el proyecto con `uv` (creación de `pyproject.toml` y paquete `soni`)
  - Desde la carpeta raíz del repo (donde solo tienes `docs/` y metadatos, pero aún no código):
    `uv init --lib soni`
  - Esto creará la estructura base tipo librería bajo `src/soni/` y un `pyproject.toml` preparado para publicar el framework.
- [ ] Añadir dependencias core con `uv add` (DSPy, LangGraph, FastAPI, etc.)
  - Ejemplo: `uv add dspy langgraph fastapi uvicorn[standard] httpx pyyaml aiosqlite`
- [ ] Añadir dependencias de desarrollo con `uv add --dev`
  - Ejemplo: `uv add --dev pytest pytest-asyncio anyio ruff mypy`
- [ ] Version pinning estricto en `pyproject.toml` (ver sección 4.1.3 del Viability)

#### 1.3 Estructura de Paquetes
```
soni/
├── pyproject.toml
├── README.md
├── soni/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── interfaces.py      # Protocolos SOLID
│   │   ├── state.py           # DialogueState
│   │   └── errors.py          # Excepciones
│   ├── du/                     # Dialogue Understanding
│   │   ├── __init__.py
│   │   ├── signatures.py       # DSPy Signatures
│   │   └── modules.py          # SoniDU
│   ├── dm/                     # Dialogue Management
│   │   ├── __init__.py
│   │   └── graph.py           # LangGraph builder
│   └── cli/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   └── unit/
├── examples/
│   └── flight_booking/
└── docs/
```

#### 1.4 Tooling de Desarrollo
- [ ] Pre-commit hooks (ruff, mypy)
- [ ] Setup pytest con pytest-asyncio
- [ ] Configurar coverage (target: 60% para MVP)
- [ ] GitHub Actions CI básico (lint + tests)

#### 1.5 Documentación Inicial
- [ ] README con quickstart placeholder
- [ ] CONTRIBUTING.md básico
- [ ] CHANGELOG.md inicial

### Criterios de Éxito
- [ ] Repo público en GitHub
- [ ] CI pasa en branch main
- [ ] Estructura de paquetes definida
- [ ] Dependencias instalables y sincronizadas (`uv sync`)

### Validación
```bash
# Verificar setup
uv sync
uv run pytest tests/  # Debe pasar (aunque tests vacíos)
uv run ruff check soni/
uv run mypy soni/
```

---

## Hito 2: Core Interfaces y State Management

**Duración:** 1 semana
**Dependencias:** Hito 1 completado
**Versión Objetivo:** Pre-v0.1.0

### Objetivo
Definir interfaces SOLID y modelo de estado base que serán usados por todo el framework.

### Tareas

#### 2.1 Definir Protocolos (Interfaces SOLID)
**Archivo:** `soni/core/interfaces.py`

```python
# Implementar según ADR sección 4.1
- INLUProvider (Protocol)
- IDialogueManager (Protocol)
- INormalizer (Protocol)
- IScopeManager (Protocol)
```

**Criterios:**
- [ ] Todos los protocolos definidos con `Protocol`
- [ ] Métodos async marcados con `async def`
- [ ] Type hints completos
- [ ] Docstrings en todos los métodos

#### 2.2 DialogueState
**Archivo:** `soni/core/state.py`

```python
@dataclass
class DialogueState:
    messages: List[Dict]
    current_flow: str
    slots: Dict[str, Any]
    pending_action: str | None
    last_response: str
    turn_count: int
    trace: List[Dict]
    summary: str | None = None
```

**Criterios:**
- [ ] Dataclass inmutable donde sea posible
- [ ] Type hints completos
- [ ] Métodos helper para acceso común
- [ ] Serializable a JSON

#### 2.3 Excepciones del Dominio
**Archivo:** `soni/core/errors.py`

```python
- SoniError (base)
- NLUError
- ValidationError
- ActionNotFoundError
- CompilationError
```

**Criterios:**
- [ ] Jerarquía de excepciones clara
- [ ] Mensajes de error informativos
- [ ] Contexto suficiente para debugging

### Tests Unitarios
- [ ] Test de DialogueState serialización
- [ ] Test de interfaces con mocks
- [ ] Test de excepciones

### Criterios de Éxito
- [ ] Interfaces definidas y documentadas
- [ ] DialogueState funcional
- [ ] Tests pasando (coverage > 60%)
- [ ] Type checking pasa (`mypy soni/core/`)

### Validación
```python
# Verificar que interfaces son correctas
from soni.core.interfaces import INLUProvider
from soni.core.state import DialogueState

# Debe compilar sin errores
state = DialogueState(...)
```

---

## Hito 3: SoniDU - Módulo DSPy Base

**Duración:** 2 semanas
**Dependencias:** Hito 2 completado
**Versión Objetivo:** Pre-v0.1.0

### Objetivo
Implementar el módulo de Dialogue Understanding como `dspy.Module` optimizable.

### Tareas

#### 3.1 DSPy Signature
**Archivo:** `soni/du/signatures.py`

```python
class DialogueUnderstanding(dspy.Signature):
    # Según ADR sección 4.3
    user_message: str = dspy.InputField(...)
    dialogue_history: str = dspy.InputField(...)
    current_slots: dict = dspy.InputField(...)
    available_actions: list[str] = dspy.InputField(...)
    current_flow: str = dspy.InputField(...)

    structured_command: str = dspy.OutputField(...)
    extracted_slots: dict = dspy.OutputField(...)
    confidence: float = dspy.OutputField(...)
    reasoning: str = dspy.OutputField(...)
```

**Criterios:**
- [ ] Signature completa según ADR
- [ ] Descripciones claras en InputField/OutputField
- [ ] Type hints correctos

#### 3.2 SoniDU Module
**Archivo:** `soni/du/modules.py`

```python
class SoniDU(dspy.Module):
    def __init__(self, scope_manager: IScopeManager = None):
        super().__init__()
        self.predictor = dspy.ChainOfThought(DialogueUnderstanding)
        self.scope_manager = scope_manager

    def forward(self, ...) -> dspy.Prediction:
        # Sync para optimizadores
        pass

    async def aforward(self, ...) -> dspy.Prediction:
        # Async para runtime
        pass

    async def predict(self, message: str, state: Dict) -> NLUResult:
        # Wrapper de conveniencia
        pass
```

**Criterios:**
- [ ] Hereda de `dspy.Module` correctamente
- [ ] `forward()` implementado (sync)
- [ ] `aforward()` implementado (async)
- [ ] `predict()` wrapper funcional
- [ ] Integración con ScopeManager (si existe)

#### 3.3 NLUResult Dataclass
```python
@dataclass
class NLUResult:
    command: str
    slots: Dict[str, Any]
    confidence: float
    reasoning: str
```

### Tests
- [ ] Test de SoniDU.forward() con mock LM
- [ ] Test de SoniDU.aforward() async
- [ ] Test de integración con DSPy real (usar gpt-4o-mini)
- [ ] Test de serialización (`.save()` / `.load()`)

### Criterios de Éxito
- [ ] Módulo compila sin errores
- [ ] `forward()` funciona con optimizadores
- [ ] `aforward()` funciona en runtime async
- [ ] Tests pasando (coverage > 70%)
- [ ] Ejemplo funcional con LLM real

### Validación
```python
# Test manual
import dspy
dspy.configure(lm=dspy.LM('openai/gpt-4o-mini'))

du = SoniDU()
result = await du.aforward(
    user_message="I want to book a flight",
    dialogue_history="",
    current_slots={},
    available_actions=["book_flight", "help"],
    current_flow="none"
)
assert result.structured_command is not None
```

---

## Hito 4: Optimización DSPy (MIPROv2)

**Duración:** 1 semana
**Dependencias:** Hito 3 completado
**Versión Objetivo:** Pre-v0.1.0

### Objetivo
Implementar pipeline de optimización con MIPROv2 para mejorar prompts automáticamente.

### Tareas

#### 4.1 Métricas de Evaluación
**Archivo:** `soni/du/metrics.py`

```python
def intent_accuracy_metric(example, prediction, trace=None) -> float:
    # Según ADR sección 4.4
    pass
```

**Criterios:**
- [ ] Métrica calcula accuracy correctamente
- [ ] Maneja casos edge (predicciones vacías, etc.)
- [ ] Retorna float entre 0.0 y 1.0

#### 4.2 Pipeline de Optimización
**Archivo:** `soni/du/optimizers.py`

```python
def optimize_soni_du(
    base_module: SoniDU,
    trainset: list[dspy.Example],
    optimizer_type: str = "MIPROv2",
    auto_config: str = "light"
) -> SoniDU:
    # Según ADR sección 4.4
    pass
```

**Criterios:**
- [ ] Soporta MIPROv2 (light mode para MVP)
- [ ] Crea trainset desde YAML triggers
- [ ] Evalúa baseline vs optimized
- [ ] Serializa módulo optimizado

#### 4.3 CLI de Optimización (Básico)
**Archivo:** `soni/cli/optimize.py`

```python
@click.command()
@click.option('--config', default='soni.yaml')
@click.option('--output', default='optimized_du.json')
def optimize(config, output):
    # Cargar YAML
    # Crear trainset
    # Optimizar
    # Guardar
    pass
```

**Criterios:**
- [ ] Comando `soni optimize` funciona
- [ ] Lee configuración desde YAML
- [ ] Genera módulo optimizado
- [ ] Muestra métricas de mejora

### Tests
- [ ] Test de métrica con ejemplos conocidos
- [ ] Test de optimización con dataset pequeño (10 ejemplos)
- [ ] Test de serialización de módulo optimizado

### Criterios de Éxito
- [ ] Optimización completa sin errores
- [ ] Mejora medible en accuracy (≥5%)
- [ ] Módulo optimizado guardable/cargable
- [ ] CLI funcional

### Validación
```bash
# Ejecutar optimización
uv run soni optimize --config examples/flight_booking/soni.yaml

# Verificar que se genera optimized_du.json
ls optimized_du.json

# Cargar y usar
python -c "from soni.du.modules import SoniDU; du = SoniDU(); du.load('optimized_du.json')"
```

---

## Hito 5: YAML Parser y Configuración

**Duración:** 1 semana
**Dependencias:** Hito 4 completado
**Versión Objetivo:** Pre-v0.1.0

### Objetivo
Implementar parser de YAML simplificado (MVP) y validación básica.

### Tareas

#### 5.1 Schema YAML Simplificado (MVP)
**Formato:**
```yaml
version: "0.1"
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini

flows:
  book_flight:
    description: "Book a flight"
    steps:
      - collect: origin
      - collect: destination
      - action: search_flights

slots:
  origin:
    type: string
    prompt: "Which city?"
  destination:
    type: string
    prompt: "Where to?"

actions:
  search_flights:
    handler: "handlers.flights.search"
```

#### 5.2 Parser YAML
**Archivo:** `soni/core/config.py`

```python
class ConfigLoader:
    @staticmethod
    def load(path: str) -> dict:
        # Cargar y validar YAML
        pass

    @staticmethod
    def validate(config: dict) -> List[ValidationError]:
        # Validación básica
        pass
```

**Criterios:**
- [ ] Carga YAML correctamente
- [ ] Validación de campos requeridos
- [ ] Mensajes de error claros
- [ ] Soporta includes/imports básicos

#### 5.3 Modelo de Configuración (Pydantic)
```python
class SoniConfig(BaseModel):
    version: str
    settings: Settings
    flows: Dict[str, FlowConfig]
    slots: Dict[str, SlotConfig]
    actions: Dict[str, ActionConfig]
```

**Criterios:**
- [ ] Modelos Pydantic para validación
- [ ] Type hints completos
- [ ] Valores por defecto donde aplica

### Tests
- [ ] Test de carga de YAML válido
- [ ] Test de validación de YAML inválido
- [ ] Test de valores por defecto
- [ ] Test de errores informativos

### Criterios de Éxito
- [ ] Parser carga YAML sin errores
- [ ] Validación detecta errores comunes
- [ ] Mensajes de error accionables
- [ ] Tests pasando

### Validación
```python
from soni.core.config import ConfigLoader

config = ConfigLoader.load("examples/flight_booking/soni.yaml")
assert config['version'] == "0.1"
assert 'book_flight' in config['flows']
```

---

## Hito 6: LangGraph Runtime Básico

**Duración:** 2 semanas
**Dependencias:** Hitos 3, 5 completados
**Versión Objetivo:** Pre-v0.1.0

### Objetivo
Implementar runtime básico con LangGraph para ejecutar flujos de diálogo (sin compiler todavía).

### Tareas

#### 6.1 Graph Builder Manual
**Archivo:** `soni/dm/graph.py`

```python
class SoniGraphBuilder:
    def __init__(self, config: dict):
        self.config = config
        self.graph = StateGraph(DialogueState)

    def build_manual(self) -> CompiledGraph:
        # Construir grafo manualmente desde YAML
        # Para MVP: solo steps lineales
        pass
```

**Criterios:**
- [ ] Crea StateGraph desde configuración
- [ ] Soporta steps lineales (collect, action)
- [ ] Nodos async implementados
- [ ] Checkpointing básico (SQLite)

#### 6.2 Nodos del Grafo
```python
async def understand_node(state: DialogueState) -> Dict:
    # NLU usando SoniDU
    pass

async def collect_slot_node(state: DialogueState, slot_name: str) -> Dict:
    # Slot filling
    pass

async def action_node(state: DialogueState, action_name: str) -> Dict:
    # Ejecutar acción
    pass
```

**Criterios:**
- [ ] Todos los nodos son `async def`
- [ ] Manejo de errores robusto
- [ ] Logging para debugging

#### 6.3 Action Handler Básico
**Archivo:** `soni/actions/base.py`

```python
class ActionHandler:
    @staticmethod
    async def execute(action_name: str, slots: dict) -> dict:
        # Cargar handler desde Python path
        # Ejecutar función
        pass
```

**Criterios:**
- [ ] Carga handlers desde string path
- [ ] Ejecuta funciones async
- [ ] Manejo de errores

### Tests
- [ ] Test de construcción de grafo
- [ ] Test de ejecución de flujo simple
- [ ] Test de persistencia de estado
- [ ] Test de manejo de errores

### Criterios de Éxito
- [ ] Grafo se construye correctamente
- [ ] Flujo ejecuta end-to-end
- [ ] Estado persiste entre turnos
- [ ] Tests pasando

### Validación
```python
from soni.dm.graph import SoniGraphBuilder

builder = SoniGraphBuilder(config)
graph = builder.build_manual()

# Ejecutar flujo
result = await graph.ainvoke(
    {"messages": [{"role": "user", "content": "I want to book a flight"}]},
    config={"configurable": {"thread_id": "test-1"}}
)
assert result['current_flow'] == 'book_flight'
```

---

## Hito 7: Runtime Loop y FastAPI Integration

**Duración:** 1 semana
**Dependencias:** Hito 6 completado
**Versión Objetivo:** v0.1.0 (MVP)

### Objetivo
Implementar runtime loop principal e integración con FastAPI para exponer API REST.

### Tareas

#### 7.1 Runtime Loop
**Archivo:** `soni/runtime.py`

```python
class RuntimeLoop:
    def __init__(self, config_path: str, optimized_du_path: str = None):
        # Inicializar grafo, DU, etc.
        pass

    async def process_message(
        self,
        user_msg: str,
        user_id: str
    ) -> str:
        # Procesar mensaje y retornar respuesta
        pass
```

**Criterios:**
- [ ] Carga configuración y módulo optimizado
- [ ] Procesa mensajes async
- [ ] Maneja múltiples conversaciones
- [ ] Persistencia de estado funcional

#### 7.2 FastAPI Endpoints
**Archivo:** `soni/server/api.py`

```python
app = FastAPI()

@app.post("/chat/{user_id}")
async def chat(user_id: str, message: str):
    # Procesar mensaje
    response = await runtime.process_message(message, user_id)
    return {"response": response}

@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Criterios:**
- [ ] Endpoint `/chat/{user_id}` funcional
- [ ] Endpoint `/health` para monitoring
- [ ] Manejo de errores con HTTP codes apropiados
- [ ] OpenAPI docs generadas automáticamente

#### 7.3 CLI de Servidor
**Archivo:** `soni/cli/server.py`

```python
@click.command()
@click.option('--config', default='soni.yaml')
@click.option('--host', default='0.0.0.0')
@click.option('--port', default=8000)
def server(config, host, port):
    # Inicializar runtime
    # Iniciar FastAPI
    pass
```

**Criterios:**
- [ ] Comando `soni server` funciona
- [ ] Servidor inicia sin errores
- [ ] Endpoints accesibles

### Tests
- [ ] Test de runtime loop con mensaje simple
- [ ] Test de FastAPI endpoints (TestClient)
- [ ] Test de persistencia entre requests
- [ ] Test de manejo de errores

### Criterios de Éxito
- [ ] Runtime procesa mensajes correctamente
- [ ] API REST funcional
- [ ] Múltiples usuarios simultáneos soportados
- [ ] Tests pasando

### Validación
```bash
# Iniciar servidor
uv run soni server --config examples/flight_booking/soni.yaml

# En otra terminal, probar API
curl -X POST http://localhost:8000/chat/user-1 \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to book a flight"}'
```

---

## Hito 8: Ejemplo End-to-End y Documentación MVP

**Duración:** 1 semana
**Dependencias:** Hito 7 completado
**Versión Objetivo:** v0.1.0 (MVP Release)

### Objetivo
Crear ejemplo funcional completo y documentación suficiente para que otros puedan usar el framework.

### Tareas

#### 8.1 Ejemplo Flight Booking
**Directorio:** `examples/flight_booking/`

**Archivos:**
- `soni.yaml` - Configuración completa
- `handlers.py` - Action handlers
- `README.md` - Guía del ejemplo
- `test_conversation.md` - Conversación de prueba

**Criterios:**
- [ ] Ejemplo funcional end-to-end
- [ ] Conversación completa de booking
- [ ] Handlers reales (pueden ser mocks)
- [ ] Optimización funciona

#### 8.2 Documentación MVP
**Archivos:**
- `README.md` - Quickstart y visión
- `docs/quickstart.md` - Guía paso a paso
- `docs/architecture.md` - Arquitectura básica
- `CHANGELOG.md` - Historial de cambios

**Criterios:**
- [ ] Quickstart funcional (< 10 minutos)
- [ ] Instrucciones claras de instalación
- [ ] Ejemplo copiable y ejecutable
- [ ] Arquitectura explicada

#### 8.3 Tests de Integración E2E
**Archivo:** `tests/integration/test_e2e.py`

```python
async def test_flight_booking_flow():
    # Test completo de flujo de booking
    pass
```

**Criterios:**
- [ ] Test E2E pasa
- [ ] Cubre flujo completo
- [ ] Usa configuración real

### Criterios de Éxito
- [ ] Ejemplo funciona de principio a fin
- [ ] Documentación suficiente para empezar
- [ ] Tests E2E pasando
- [ ] README atractivo y claro

### Validación
```bash
# Seguir quickstart desde cero
# Debe funcionar sin problemas
cd examples/flight_booking
uv run soni optimize --config soni.yaml
uv run soni server --config soni.yaml
# Probar conversación completa
```

---

## Hito 9: Release v0.1.0 (MVP)

**Duración:** 3 días
**Dependencias:** Hito 8 completado

### Objetivo
Preparar y publicar primera versión alpha del framework.

### Tareas

#### 9.1 Preparación de Release
- [ ] Versionar en `pyproject.toml` (0.1.0)
- [ ] Actualizar CHANGELOG.md
- [ ] Tag en Git (`v0.1.0`)
- [ ] Release notes en GitHub

#### 9.2 Validación Final
- [ ] Todos los tests pasando
- [ ] Coverage > 60%
- [ ] Linting pasa
- [ ] Type checking pasa
- [ ] Ejemplo funciona

#### 9.3 Publicación
- [ ] Build de paquete (`uv build`)
- [ ] Publicar en PyPI (opcional para alpha)
- [ ] Crear GitHub Release
- [ ] Post en Reddit/HN (opcional)

### Criterios de Éxito
- [ ] Release publicado
- [ ] Instalable desde PyPI o GitHub
- [ ] Documentación accesible
- [ ] Ejemplo funcional

### Métricas de Éxito MVP
- [ ] Intent accuracy > 85% (post-optimization)
- [ ] Latencia p95 < 3s
- [ ] 0 crashes en 100 conversaciones de prueba
- [ ] Quickstart funciona en < 10 minutos

---

## Hito 10: Async Everything y Dynamic Scoping

**Duración:** 2 semanas
**Dependencias:** Hito 9 completado
**Versión Objetivo:** v0.2.0

### Objetivo
Migrar todo a async y implementar scoping dinámico para mejorar performance.

### Tareas

#### 10.1 Migración a Async
- [ ] Persistencia async (aiosqlite)
- [ ] Todos los nodos async
- [ ] Handlers async
- [ ] Tests async

#### 10.2 ScopeManager
**Archivo:** `soni/core/scope.py`

```python
class ScopeManager(IScopeManager):
    def get_available_actions(self, state: DialogueState) -> List[str]:
        # Filtrado de acciones según contexto
        pass
```

**Criterios:**
- [ ] Filtra acciones por flujo actual
- [ ] Incluye acciones globales siempre
- [ ] Considera slots completados
- [ ] Tests unitarios

#### 10.3 Integración con SoniDU
- [ ] SoniDU usa scoped actions
- [ ] Reducción medible de tokens
- [ ] Mejora en accuracy

### Tests
- [ ] Test de scoping con diferentes estados
- [ ] Test de reducción de tokens
- [ ] Test de mejora en accuracy

### Criterios de Éxito
- [ ] Todo es async
- [ ] Scoping funciona correctamente
- [ ] Reducción de tokens > 30%
- [ ] Mejora en accuracy > 5%

---

## Hito 11: Normalization Layer

**Duración:** 1 semana
**Dependencias:** Hito 10 completado
**Versión Objetivo:** v0.2.0

### Objetivo
Implementar capa de normalización para limpiar datos antes de validación.

### Tareas

#### 11.1 SlotNormalizer
**Archivo:** `soni/du/normalizer.py`

```python
class SlotNormalizer(INormalizer):
    async def normalize(self, value: Any, entity_config: Dict) -> Any:
        # Estrategias: trim, lowercase, llm_correction
        pass
```

**Criterios:**
- [ ] Soporta estrategias básicas (trim, lowercase)
- [ ] LLM correction async
- [ ] Cache de normalizaciones
- [ ] Tests unitarios

#### 11.2 Integración en Pipeline
- [ ] Normalizer en runtime loop
- [ ] Antes de validación
- [ ] Logging de normalizaciones

### Tests
- [ ] Test de estrategias básicas
- [ ] Test de LLM correction
- [ ] Test de cache
- [ ] Test de integración

### Criterios de Éxito
- [ ] Normalización funciona
- [ ] Mejora en tasa de validación > 10%
- [ ] Latencia aceptable (< 200ms)

---

## Hito 12: Streaming y Performance

**Duración:** 1 semana
**Dependencias:** Hito 11 completado
**Versión Objetivo:** v0.2.0

### Objetivo
Implementar streaming de tokens y optimizar performance.

### Tareas

#### 12.1 Streaming en Runtime
**Archivo:** `soni/runtime.py`

```python
async def process_message_stream(
    self,
    user_msg: str,
    user_id: str
) -> AsyncGenerator[str, None]:
    # Streaming de tokens
    pass
```

**Criterios:**
- [ ] Streaming funcional
- [ ] Compatible con SSE
- [ ] Latencia first-token < 500ms

#### 12.2 FastAPI Streaming Endpoint
```python
@app.post("/chat/{user_id}/stream")
async def chat_stream(user_id: str, message: str):
    async def generate():
        async for token in runtime.process_message_stream(message, user_id):
            yield f"data: {token}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Criterios:**
- [ ] Endpoint funcional
- [ ] Compatible con frontend SSE
- [ ] Tests de integración

#### 12.3 Optimizaciones de Performance
- [ ] Connection pooling
- [ ] Caching agresivo
- [ ] Batch processing donde aplica

### Tests
- [ ] Test de streaming
- [ ] Test de latencia
- [ ] Test de throughput

### Criterios de Éxito
- [ ] Streaming funcional
- [ ] Latencia p95 < 1.5s
- [ ] Throughput > 10 conversaciones/segundo
- [ ] Streaming latency to first token < 500ms

---

## Hito 13: Release v0.2.0

**Duración:** 3 días
**Dependencias:** Hito 12 completado

### Objetivo
Publicar versión beta con mejoras de performance.

### Tareas
- [ ] Versionar (0.2.0)
- [ ] Actualizar CHANGELOG
- [ ] Release notes
- [ ] Validación final

### Criterios de Éxito
- [ ] Release publicado
- [ ] Todas las métricas cumplidas
- [ ] Documentación actualizada

---

## Hito 14: Step Compiler (Parte 1 - Lineal)

**Duración:** 2 semanas
**Dependencias:** Hito 13 completado
**Versión Objetivo:** v0.3.0

### Objetivo
Implementar compilador de YAML procedural a LangGraph (solo steps lineales primero).

### Tareas

#### 14.1 Parser de Steps
**Archivo:** `soni/compiler/parser.py`

```python
class StepParser:
    def parse(self, steps: List[dict]) -> List[Step]:
        # Parsear steps desde YAML
        pass
```

**Criterios:**
- [ ] Parsea steps lineales
- [ ] Valida sintaxis
- [ ] Errores claros

#### 14.2 Graph Builder desde Steps
**Archivo:** `soni/compiler/builder.py`

```python
class StepCompiler:
    def compile(self, flow_name: str, steps: List[Step]) -> StateGraph:
        # Construir grafo desde steps lineales
        pass
```

**Criterios:**
- [ ] Genera grafo válido
- [ ] Conecta nodos secuencialmente
- [ ] Valida grafo resultante

### Tests
- [ ] Test de parsing
- [ ] Test de compilación
- [ ] Test de grafo generado

### Criterios de Éxito
- [ ] Compiler funciona para steps lineales
- [ ] Grafos generados son válidos
- [ ] Errores de compilación claros

---

## Hito 15: Step Compiler (Parte 2 - Condicionales)

**Duración:** 2 semanas
**Dependencias:** Hito 14 completado
**Versión Objetivo:** v0.3.0

### Objetivo
Añadir soporte para branches, jumps y condicionales.

### Tareas

#### 15.1 Soporte de Branches
```python
# YAML
- step: decide_path
  type: branch
  input: status
  cases:
    success: continue
    error: jump_to_error
```

**Criterios:**
- [ ] Parsea branches
- [ ] Genera conditional_edges
- [ ] Resuelve saltos correctamente

#### 15.2 Soporte de Jumps
```python
- step: error_handler
  type: say
  message: "Error occurred"
  # jump_to implícito o explícito
```

**Criterios:**
- [ ] Resuelve jump_to
- [ ] Valida targets existen
- [ ] Maneja loops

#### 15.3 Validación de Grafo
- [ ] Detecta ciclos inválidos
- [ ] Valida todos los targets
- [ ] Errores informativos

### Tests
- [ ] Test de branches
- [ ] Test de jumps
- [ ] Test de validación
- [ ] Test de loops

### Criterios de Éxito
- [ ] Compiler soporta condicionales
- [ ] 95% de casos de uso compilan
- [ ] Errores accionables

---

## Hito 16: Release v0.3.0

**Duración:** 3 días
**Dependencias:** Hito 15 completado

### Objetivo
Publicar versión con DSL Compiler completo.

### Tareas
- [ ] Versionar (0.3.0)
- [ ] Documentación de DSL
- [ ] Ejemplos avanzados
- [ ] Release

### Criterios de Éxito
- [ ] Compiler robusto
- [ ] Documentación completa
- [ ] Ejemplos funcionan

---

## Hito 17: Action Registry (Zero-Leakage Part 1)

**Duración:** 2 semanas
**Dependencias:** Hito 16 completado
**Versión Objetivo:** v0.4.0

### Objetivo
Implementar sistema de registro de acciones para desacoplar YAML de implementación.

### Tareas

#### 17.1 Action Registry
**Archivo:** `soni/actions/registry.py`

```python
class ActionRegistry:
    @classmethod
    def register(cls, name: str):
        # Decorador
        pass

    @classmethod
    def get(cls, name: str) -> Callable:
        # Obtener acción
        pass
```

**Criterios:**
- [ ] Decorador funcional
- [ ] Lookup por nombre
- [ ] Manejo de errores
- [ ] Tests unitarios

#### 17.2 Integración en Compiler
- [ ] Compiler usa registry
- [ ] Validación de acciones registradas
- [ ] Errores claros si falta acción

#### 17.3 YAML Semántico
```yaml
actions:
  search_flights:
    description: "Search for flights"
    inputs: [origin, destination, date]
    outputs: [count, cheapest]
```

**Criterios:**
- [ ] YAML sin detalles técnicos
- [ ] Contratos claros
- [ ] Validación de contratos

### Tests
- [ ] Test de registry
- [ ] Test de decorador
- [ ] Test de integración
- [ ] Test de validación

### Criterios de Éxito
- [ ] Registry funcional
- [ ] YAML puramente semántico
- [ ] Cambios en API no requieren cambio de YAML

---

## Hito 18: Validator Registry (Zero-Leakage Part 2)

**Duración:** 1 semana
**Dependencias:** Hito 17 completado
**Versión Objetivo:** v0.4.0

### Objetivo
Implementar sistema de validadores semánticos.

### Tareas

#### 18.1 Validator Registry
**Archivo:** `soni/validation/registry.py`

```python
class ValidatorRegistry:
    @classmethod
    def register(cls, name: str):
        # Decorador
        pass
```

**Criterios:**
- [ ] Similar a Action Registry
- [ ] Validadores por nombre
- [ ] Tests unitarios

#### 18.2 Integración
- [ ] Validadores en pipeline
- [ ] YAML usa nombres semánticos
- [ ] Errores claros

### Tests
- [ ] Test de registry
- [ ] Test de validación
- [ ] Test de integración

### Criterios de Éxito
- [ ] Validadores funcionan
- [ ] YAML sin regex
- [ ] Validación robusta

---

## Hito 19: Output Mapping (Zero-Leakage Part 3)

**Duración:** 1 semana
**Dependencias:** Hito 18 completado
**Versión Objetivo:** v0.4.0

### Objetivo
Implementar mapeo de outputs para desacoplar estructuras de datos.

### Tareas

#### 19.1 Output Mapping en Compiler
```python
# En _create_action_node
map_outputs = step.get('map_outputs', {})
# Aplicar mapeo
```

**Criterios:**
- [ ] Mapeo funcional
- [ ] Variables planas en estado
- [ ] Validación de mapeos

#### 19.2 Integración
- [ ] Compiler maneja map_outputs
- [ ] Variables accesibles en flujo
- [ ] Tests

### Tests
- [ ] Test de mapeo
- [ ] Test de variables planas
- [ ] Test de integración

### Criterios de Éxito
- [ ] Mapeo funciona
- [ ] Flujo usa variables planas
- [ ] Cambios en estructura no rompen YAML

---

## Hito 20: Release v0.4.0

**Duración:** 3 días
**Dependencias:** Hito 19 completado

### Objetivo
Publicar versión con arquitectura Zero-Leakage completa.

### Tareas
- [ ] Versionar (0.4.0)
- [ ] Documentación completa
- [ ] Ejemplos Zero-Leakage
- [ ] Release

### Criterios de Éxito
- [ ] Zero-Leakage completo
- [ ] Documentación clara
- [ ] Ejemplos funcionan

---

## Hito 21: Validación y Polish para v1.0.0

**Duración:** 1-2 meses
**Dependencias:** Hito 20 completado
**Versión Objetivo:** v1.0.0

### Objetivo
Validar completamente el ADR y preparar release estable.

### Tareas

#### 21.1 Auditoría Completa
- [ ] Revisar ADR vs implementación
- [ ] Checklist de features
- [ ] Identificar gaps

#### 21.2 Testing Exhaustivo
- [ ] Coverage > 80%
- [ ] Tests E2E completos
- [ ] Performance tests
- [ ] Security audit

#### 21.3 Documentación Final
- [ ] Docs site completo
- [ ] API reference
- [ ] Tutoriales
- [ ] Migration guide

#### 21.4 Caso de Uso Real
- [ ] Deployment en producción
- [ ] Validación con usuarios
- [ ] Métricas reales

### Criterios de Éxito
- [ ] ADR completamente implementado
- [ ] Tests pasando
- [ ] Documentación completa
- [ ] Caso de uso validado
- [ ] Performance cumplida

---

## Hito 22: Release v1.0.0

**Duración:** 1 semana
**Dependencias:** Hito 21 completado

### Objetivo
Publicar versión estable 1.0.0.

### Tareas
- [ ] Versionar (1.0.0)
- [ ] Release notes completos
- [ ] Publicación en PyPI
- [ ] Community announcement
- [ ] Blog post

### Criterios de Éxito
- [ ] Release estable publicado
- [ ] Comunidad informada
- [ ] Documentación accesible

---

## Resumen de Hitos

| Hito | Versión | Duración | Dependencias | Estado Objetivo |
|------|---------|----------|--------------|-----------------|
| 0 | Pre-dev | 1-2 sem | - | Validación técnica |
| 1 | Pre-0.1 | 1 sem | 0 | Setup proyecto |
| 2 | Pre-0.1 | 1 sem | 1 | Interfaces y State |
| 3 | Pre-0.1 | 2 sem | 2 | SoniDU Module |
| 4 | Pre-0.1 | 1 sem | 3 | Optimización DSPy |
| 5 | Pre-0.1 | 1 sem | 4 | YAML Parser |
| 6 | Pre-0.1 | 2 sem | 3,5 | LangGraph Runtime |
| 7 | 0.1.0 | 1 sem | 6 | Runtime Loop + API |
| 8 | 0.1.0 | 1 sem | 7 | Ejemplo E2E |
| 9 | 0.1.0 | 3 días | 8 | **Release MVP** |
| 10 | 0.2.0 | 2 sem | 9 | Async + Scoping |
| 11 | 0.2.0 | 1 sem | 10 | Normalization |
| 12 | 0.2.0 | 1 sem | 11 | Streaming |
| 13 | 0.2.0 | 3 días | 12 | **Release Beta** |
| 14 | 0.3.0 | 2 sem | 13 | Step Compiler (1) |
| 15 | 0.3.0 | 2 sem | 14 | Step Compiler (2) |
| 16 | 0.3.0 | 3 días | 15 | **Release Beta Avanzado** |
| 17 | 0.4.0 | 2 sem | 16 | Action Registry |
| 18 | 0.4.0 | 1 sem | 17 | Validator Registry |
| 19 | 0.4.0 | 1 sem | 18 | Output Mapping |
| 20 | 0.4.0 | 3 días | 19 | **Release RC** |
| 21 | 1.0.0 | 1-2 mes | 20 | Validación completa |
| 22 | 1.0.0 | 1 sem | 21 | **Release Stable** |

**Total Estimado:** 11-13 meses

---

## Criterios de "Definition of Done"

Cada hito se considera completado cuando:

1. ✅ **Código Implementado**
   - Funcionalidad completa según especificación
   - Sin TODOs críticos
   - Code review (si aplica)

2. ✅ **Tests Pasando**
   - Tests unitarios con coverage adecuado
   - Tests de integración donde aplica
   - Tests E2E para hitos de release

3. ✅ **Documentación Actualizada**
   - README actualizado
   - Docstrings en código
   - Ejemplos funcionan

4. ✅ **Validación Técnica**
   - Criterios de éxito cumplidos
   - Métricas dentro de rangos aceptables
   - Sin bugs críticos conocidos

5. ✅ **Preparación para Siguiente Hito**
   - Dependencias resueltas
   - Bloqueadores identificados
   - Plan para siguiente hito claro

---

## Gestión de Riesgos por Hito

### Hitos Críticos (Bloqueadores)

**Hito 0 (Validación Técnica):**
- **Riesgo:** DSPy/LangGraph no funcionan para el caso
- **Mitigación:** Tener alternativas listas (LangChain, custom)

**Hito 3 (SoniDU Module):**
- **Riesgo:** DSPy Module no optimizable
- **Mitigación:** Validar con experimento pequeño primero

**Hito 6 (LangGraph Runtime):**
- **Riesgo:** Grafo no funciona correctamente
- **Mitigación:** Tests exhaustivos, debugging tools

**Hito 14-15 (Step Compiler):**
- **Riesgo:** Compilación demasiado compleja
- **Mitigación:** Empezar simple, iterar

### Hitos de Alto Riesgo

**Hito 17-19 (Zero-Leakage):**
- **Riesgo:** Over-engineering
- **Mitigación:** Validar necesidad con usuarios primero

**Hito 21 (Validación v1.0.0):**
- **Riesgo:** Gaps en implementación
- **Mitigación:** Checklist exhaustivo, auditoría temprana

---

## Métricas de Progreso

### Métricas por Versión

**v0.1.0 (MVP):**
- Intent accuracy > 85%
- Latencia p95 < 3s
- Coverage > 60%

**v0.2.0 (Beta):**
- Latencia p95 < 1.5s
- Throughput > 10 conv/seg
- Streaming latency < 500ms

**v0.3.0 (Beta Avanzado):**
- Compilation success > 95%
- Errores accionables

**v0.4.0 (RC):**
- 0 detalles técnicos en YAML
- Cambios API no requieren cambio YAML

**v1.0.0 (Stable):**
- Todas las métricas anteriores
- Coverage > 80%
- 1 deployment producción

### Tracking

- [ ] Dashboard de métricas (opcional)
- [ ] CI/CD con métricas automáticas
- [ ] Reportes semanales de progreso

---

## Comunicación y Transparencia

### Updates Regulares

- **Semanal:** Status update (qué se completó, qué sigue)
- **Por Hito:** Release notes y documentación
- **Mensual:** Roadmap review y ajustes

### Canales

- GitHub Issues para tracking
- GitHub Discussions para Q&A
- CHANGELOG.md para historial
- Releases en GitHub para versiones

---

## Conclusión

Esta estrategia de implementación proporciona un camino claro y ejecutable desde el inicio hasta v1.0.0, con hitos medibles, dependencias explícitas y criterios de éxito definidos.

**Principios clave:**
- ✅ Validación temprana (Hito 0)
- ✅ MVP primero (v0.1.0)
- ✅ Iteración incremental
- ✅ Criterios claros de éxito
- ✅ Gestión de riesgos proactiva

**Próximos Pasos:**
1. Ejecutar Hito 0 (Validación Técnica)
2. Si GO, proceder con Hito 1 (Setup)
3. Seguir hitos secuencialmente
4. Ajustar roadmap basado en aprendizaje

---

**Fin del Documento**
