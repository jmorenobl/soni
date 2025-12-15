# Soni Framework - Plan de Reescritura v3.0

**Documento**: Propuesta de Reescritura Arquitectónica
**Fecha**: 2025-12-15
**Versión**: 1.0
**Estado**: Propuesta para Aprobación

---

## Resumen Ejecutivo

Se propone archivar el código actual del framework Soni y reescribirlo desde cero aplicando:
- **TDD** (Test-Driven Development)
- **Principios SOLID**
- **Patrones de diseño** apropiados
- **Clean Architecture**

Esta decisión se basa en que el diseño arquitectónico ya ha sido validado con una implementación funcional de subgrafos de LangGraph, y el código actual presenta deuda técnica significativa que dificulta la evolución del framework.

**Tiempo estimado**: 2-3 semanas
**Riesgo**: Medio (mitigado por diseño ya validado)
**Beneficio**: Código mantenible, extensible y testeable

---

## 1. Situación Actual

### 1.1 Estado del Código

| Métrica | Valor |
|---------|-------|
| Líneas de código Python | ~16,125 |
| Archivos Python | ~80 |
| Cobertura de tests | Baja (tests desactualizados) |
| Arquitecturas coexistentes | 2 (v2 interpretada + v3 subgrafos) |

### 1.2 Problemas Identificados

#### Deuda Técnica Crítica

1. **Dos arquitecturas coexistiendo**
   - `dm/graph.py`: Grafo monolítico con nodos genéricos (arquitectura v2)
   - `dm/orchestrator.py`: Subgrafos compilados (arquitectura v3)
   - Ambas funcionan pero el código está duplicado y es confuso

2. **Código muerto**
   - `compiler/builder.py` (676 líneas) no se usa en runtime
   - `flow/step_manager.py` tiene lógica duplicada con `subgraph_builder.py`
   - Nodos en `dm/nodes/` para arquitectura antigua

3. **Tests desactualizados**
   - Tests eliminados en commits recientes por incompatibilidad
   - Sin cobertura para la nueva arquitectura de subgrafos
   - Difícil añadir tests sin refactorizar

4. **Violaciones de SOLID**
   - Clases con múltiples responsabilidades
   - Dependencias hardcodeadas
   - Interfaces no segregadas

### 1.3 Diagrama de Arquitectura Actual

```
ESTADO ACTUAL (Confuso - dos arquitecturas mezcladas)

┌─────────────────────────────────────────────────────────────────┐
│                         runtime.py                               │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  Puede usar:                                            │   │
│   │  - build_orchestrator_graph() ← Nueva (subgrafos)       │   │
│   │  - build_graph()              ← Vieja (monolítico)      │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
┌───────────────────┐                    ┌───────────────────┐
│  dm/orchestrator  │                    │    dm/graph.py    │
│   (v3 - nuevo)    │                    │   (v2 - viejo)    │
│                   │                    │                   │
│  - Subgrafos      │                    │  - Nodos genéricos│
│  - Compilación    │                    │  - Interpretación │
└───────────────────┘                    └───────────────────┘
        │                                           │
        ▼                                           ▼
┌───────────────────┐                    ┌───────────────────┐
│ subgraph_builder  │                    │   dm/nodes/step   │
│   (396 líneas)    │                    │   (186 líneas)    │
│                   │                    │                   │
│  Lógica duplicada │◄──────────────────►│  Lógica duplicada │
└───────────────────┘                    └───────────────────┘
```

---

## 2. Propuesta de Solución

### 2.1 Estrategia: Archive & Rewrite

```
ANTES                              DESPUÉS
─────────────────────────────────────────────────────────
soni/                              soni/
├── src/soni/    (16k líneas)      ├── archive/
├── tests/       (desactualizados) │   ├── src/     ← Referencia
│                                  │   └── tests/   ← Referencia
│                                  │
│                                  ├── src/soni/    ← Nuevo (TDD)
│                                  └── tests/       ← Nuevo (AAA)
```

### 2.2 Por Qué Rewrite y No Refactor Incremental

| Factor | Refactor Incremental | Rewrite |
|--------|---------------------|---------|
| Tiempo estimado | 4-6 semanas | 2-3 semanas |
| Riesgo de regresiones | Alto | Bajo (TDD) |
| Deuda técnica resultante | Media | Ninguna |
| Cobertura de tests | Parcial | 100% desde inicio |
| Complejidad del proceso | Alta (mantener compatibilidad) | Baja (empezar limpio) |

**Justificación**: El refactor incremental requeriría mantener compatibilidad con código que sabemos que no queremos. Es más eficiente empezar limpio con el diseño ya validado.

### 2.3 Arquitectura Objetivo

```
ARQUITECTURA OBJETIVO (Clean Architecture + Subgrafos)

┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                        │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│   │   CLI       │  │  REST API   │  │  WebSocket  │            │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
└──────────┼────────────────┼────────────────┼────────────────────┘
           │                │                │
           └────────────────┼────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                           │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    RuntimeLoop                           │   │
│   │         (Orquesta el ciclo de conversación)              │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  ORCHESTRATOR   │ │    COMPILER     │ │       DU        │
│                 │ │                 │ │                 │
│ - Route flows   │ │ - YAML → Graph  │ │ - NLU (DSPy)    │
│ - Manage state  │ │ - Node factories│ │ - Commands      │
│ - Subgraph exec │ │ - Edge building │ │ - Optimization  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
           │                │                │
           └────────────────┼────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DOMAIN LAYER                              │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │
│   │  Commands │  │   State   │  │   Flows   │  │  Actions  │   │
│   │           │  │           │  │           │  │           │   │
│   │ StartFlow │  │ Dialogue  │  │ FlowConfig│  │ IAction   │   │
│   │ SetSlot   │  │ Flow      │  │ StepConfig│  │ Handler   │   │
│   │ Cancel    │  │ Runtime   │  │           │  │           │   │
│   └───────────┘  └───────────┘  └───────────┘  └───────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE LAYER                         │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │
│   │ LangGraph │  │   DSPy    │  │  SQLite   │  │   YAML    │   │
│   │ Adapter   │  │  Adapter  │  │ Checkpoint│  │  Loader   │   │
│   └───────────┘  └───────────┘  └───────────┘  └───────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Plan de Implementación

### 3.1 Estructura de Directorios Objetivo

```
src/soni/
├── __init__.py
│
├── core/                          # FASE 1: Fundamentos
│   ├── __init__.py
│   ├── types.py                   # TypedDicts: DialogueState, FlowContext
│   ├── commands.py                # Command hierarchy (Pydantic)
│   ├── errors.py                  # Exception hierarchy
│   ├── config.py                  # SoniConfig, FlowConfig, StepConfig
│   └── interfaces.py              # Protocols/ABCs
│
├── flow/                          # FASE 2: Flow Management
│   ├── __init__.py
│   ├── manager.py                 # FlowManager (stack operations)
│   ├── state.py                   # Flow state helpers
│   └── context.py                 # FlowContext operations
│
├── compiler/                      # FASE 3: Compilation
│   ├── __init__.py
│   ├── nodes/                     # Node factories (one per step type)
│   │   ├── __init__.py
│   │   ├── base.py                # NodeFactory protocol
│   │   ├── collect.py             # CollectNodeFactory
│   │   ├── action.py              # ActionNodeFactory
│   │   ├── branch.py              # BranchNodeFactory
│   │   ├── confirm.py             # ConfirmNodeFactory
│   │   ├── say.py                 # SayNodeFactory
│   │   └── while_loop.py          # WhileNodeFactory
│   ├── edges.py                   # EdgeBuilder
│   └── subgraph.py                # SubgraphBuilder
│
├── dm/                            # FASE 4: Dialogue Management
│   ├── __init__.py
│   ├── orchestrator.py            # OrchestratorGraph
│   ├── routing.py                 # Routing logic
│   └── nodes/                     # Orchestrator nodes only
│       ├── __init__.py
│       ├── understand.py
│       ├── execute.py
│       └── respond.py
│
├── du/                            # FASE 5: Dialogue Understanding
│   ├── __init__.py
│   ├── signatures.py              # DSPy signatures
│   ├── modules.py                 # SoniDU module
│   └── optimizer.py               # MIPROv2 wrapper
│
├── runtime/                       # FASE 6: Runtime
│   ├── __init__.py
│   ├── loop.py                    # RuntimeLoop
│   └── checkpointer.py            # Checkpointer factory
│
├── actions/                       # FASE 7: Actions
│   ├── __init__.py
│   ├── registry.py                # ActionRegistry
│   └── handler.py                 # ActionHandler
│
└── server/                        # FASE 8: Server (opcional)
    ├── __init__.py
    └── api.py                     # FastAPI endpoints
```

### 3.2 Estructura de Tests

```
tests/
├── conftest.py                    # Fixtures compartidos
├── factories.py                   # Test factories (estados, configs)
│
├── unit/                          # Tests unitarios (aislados)
│   ├── core/
│   │   ├── test_types.py
│   │   ├── test_commands.py
│   │   ├── test_errors.py
│   │   └── test_config.py
│   ├── flow/
│   │   ├── test_manager.py
│   │   └── test_state.py
│   ├── compiler/
│   │   ├── test_node_factories.py
│   │   ├── test_edges.py
│   │   └── test_subgraph.py
│   ├── dm/
│   │   ├── test_orchestrator.py
│   │   └── test_routing.py
│   └── du/
│       ├── test_signatures.py
│       └── test_modules.py
│
├── integration/                   # Tests de integración
│   ├── test_flow_execution.py     # Flow completo sin LLM
│   ├── test_subgraph_routing.py   # Routing entre subgrafos
│   └── test_state_persistence.py  # Checkpointing
│
└── e2e/                           # Tests end-to-end
    ├── test_booking_flow.py       # Flujo de reserva completo
    └── test_multi_turn.py         # Conversación multi-turno
```

### 3.3 Fases de Desarrollo

#### FASE 1: Core (Días 1-3)

**Objetivo**: Establecer los tipos y estructuras de datos fundamentales.

**Entregables**:
- `core/types.py` - TypedDicts para estado
- `core/commands.py` - Jerarquía de comandos
- `core/errors.py` - Excepciones custom
- `core/config.py` - Configuración del sistema

**Tests requeridos** (mínimo):
- Test de creación de DialogueState vacío
- Test de serialización/deserialización de Commands
- Test de carga de configuración YAML
- Test de validación de configuración inválida

**Criterio de éxito**:
```bash
pytest tests/unit/core/ -v  # 100% passing
```

#### FASE 2: Flow Management (Días 4-6)

**Objetivo**: Implementar la gestión del stack de flows.

**Entregables**:
- `flow/manager.py` - FlowManager con push/pop/get
- `flow/state.py` - Helpers para manipular estado
- `flow/context.py` - Operaciones de contexto

**Tests requeridos** (mínimo):
- Test push_flow crea contexto nuevo
- Test pop_flow retorna a flow anterior
- Test get_active_context retorna flow activo
- Test set_slot almacena valor correctamente
- Test flows anidados (3+ niveles)

**Criterio de éxito**:
```bash
pytest tests/unit/flow/ -v  # 100% passing
```

#### FASE 3: Compiler (Días 7-10)

**Objetivo**: Implementar la compilación de YAML a subgrafos.

**Entregables**:
- `compiler/nodes/*.py` - Factory por cada tipo de step
- `compiler/edges.py` - Construcción de edges
- `compiler/subgraph.py` - SubgraphBuilder

**Tests requeridos** (mínimo):
- Test CollectNodeFactory genera nodo correcto
- Test ActionNodeFactory ejecuta action handler
- Test BranchNodeFactory evalúa condiciones
- Test WhileNodeFactory maneja loops
- Test SubgraphBuilder conecta nodos secuencialmente
- Test SubgraphBuilder maneja jump_to
- Test SubgraphBuilder maneja branch cases

**Criterio de éxito**:
```bash
pytest tests/unit/compiler/ -v  # 100% passing
```

#### FASE 4: Orchestrator (Días 11-13)

**Objetivo**: Implementar el grafo orquestador que coordina subgrafos.

**Entregables**:
- `dm/orchestrator.py` - OrchestratorGraph
- `dm/routing.py` - Lógica de routing
- `dm/nodes/` - Nodos del orquestador

**Tests requeridos** (mínimo):
- Test routing a flow correcto según comando
- Test routing a respond cuando no hay flow activo
- Test subgraph se ejecuta y retorna
- Test cambio de flow mid-conversation
- Test flow stack se mantiene entre turnos

**Criterio de éxito**:
```bash
pytest tests/unit/dm/ tests/integration/ -v  # 100% passing
```

#### FASE 5: Dialogue Understanding (Días 14-16)

**Objetivo**: Implementar el módulo de NLU con DSPy.

**Entregables**:
- `du/signatures.py` - Signatures de DSPy
- `du/modules.py` - SoniDU module
- `du/optimizer.py` - Wrapper de MIPROv2

**Tests requeridos** (mínimo):
- Test extracción de StartFlow command
- Test extracción de SetSlot command
- Test manejo de confirmación (Affirm/Deny)
- Test extracción de múltiples comandos

**Criterio de éxito**:
```bash
pytest tests/unit/du/ -v  # 100% passing
```

#### FASE 6: Runtime (Días 17-18)

**Objetivo**: Implementar el loop principal de ejecución.

**Entregables**:
- `runtime/loop.py` - RuntimeLoop
- `runtime/checkpointer.py` - Factory de checkpointers

**Tests requeridos** (mínimo):
- Test process_message retorna respuesta
- Test estado persiste entre mensajes
- Test múltiples usuarios concurrentes
- Test cleanup libera recursos

**Criterio de éxito**:
```bash
pytest tests/unit/runtime/ tests/e2e/ -v  # 100% passing
```

#### FASE 7: Actions (Día 19)

**Objetivo**: Implementar el sistema de acciones.

**Entregables**:
- `actions/registry.py` - Registro de acciones
- `actions/handler.py` - Ejecución de acciones

**Tests requeridos** (mínimo):
- Test registro de action
- Test ejecución de action con inputs
- Test manejo de error en action

#### FASE 8: Integración Final (Días 20-21)

**Objetivo**: Tests e2e y documentación.

**Entregables**:
- Tests e2e completos
- README actualizado
- Ejemplos funcionando

---

## 4. Metodología TDD

### 4.1 Ciclo Red-Green-Refactor

```
┌─────────────────────────────────────────────────────────────────┐
│                         TDD CYCLE                                │
│                                                                  │
│    ┌──────────┐         ┌──────────┐         ┌──────────┐       │
│    │   RED    │────────▶│  GREEN   │────────▶│ REFACTOR │       │
│    │          │         │          │         │          │       │
│    │ Write    │         │ Write    │         │ Improve  │       │
│    │ failing  │         │ minimal  │         │ code     │       │
│    │ test     │         │ code to  │         │ quality  │       │
│    │          │         │ pass     │         │          │       │
│    └──────────┘         └──────────┘         └────┬─────┘       │
│          ▲                                        │              │
│          └────────────────────────────────────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Formato de Test AAA (Arrange-Act-Assert)

Todos los tests seguirán estrictamente el formato AAA:

```python
class TestFlowManager:
    """Tests for FlowManager."""

    def test_push_flow_creates_new_context_on_empty_stack(self):
        """
        GIVEN an empty dialogue state
        WHEN push_flow is called with a flow name
        THEN a new flow context is created on the stack
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        flow_id = manager.push_flow(state, flow_name="book_flight")

        # Assert
        assert len(state["flow_stack"]) == 1
        assert state["flow_stack"][0]["flow_name"] == "book_flight"
        assert state["flow_stack"][0]["flow_id"] == flow_id
        assert state["flow_stack"][0]["flow_state"] == "active"

    def test_push_flow_preserves_existing_flows_on_stack(self):
        """
        GIVEN a state with one active flow
        WHEN push_flow is called with a new flow
        THEN both flows are on the stack with new flow on top
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        manager.push_flow(state, flow_name="main_flow")

        # Act
        manager.push_flow(state, flow_name="sub_flow")

        # Assert
        assert len(state["flow_stack"]) == 2
        assert state["flow_stack"][0]["flow_name"] == "main_flow"
        assert state["flow_stack"][1]["flow_name"] == "sub_flow"
```

### 4.3 Convenciones de Naming

```python
# Test files
test_<module_name>.py

# Test classes
class Test<ClassName>:

# Test methods (descriptivos)
def test_<method>_<scenario>_<expected_result>(self):

# Ejemplos:
def test_push_flow_with_initial_slots_stores_slots_in_state(self):
def test_pop_flow_on_empty_stack_raises_error(self):
def test_set_slot_with_invalid_value_returns_validation_error(self):
```

---

## 5. Gestión de Riesgos

### 5.1 Riesgos Identificados

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Tiempo subestimado | Media | Alto | Buffer de 1 semana incluido |
| Pérdida de edge cases | Baja | Medio | Archive como referencia |
| Scope creep | Media | Alto | Fases definidas estrictamente |
| Bugs en código nuevo | Media | Bajo | TDD garantiza cobertura |
| Dependencias externas cambian | Baja | Medio | Pinear versiones |

### 5.2 Plan de Contingencia

**Si el rewrite excede 3 semanas**:
1. Evaluar qué fases están completas
2. Considerar usar código del archive para fases pendientes
3. Priorizar runtime funcional sobre features completas

**Si se descubren edge cases críticos no contemplados**:
1. Documentar el edge case
2. Buscar en archive cómo se manejaba
3. Añadir test específico
4. Implementar solución

---

## 6. Criterios de Éxito

### 6.1 Métricas Objetivo

| Métrica | Valor Objetivo |
|---------|---------------|
| Cobertura de tests | > 90% |
| Tests pasando | 100% |
| Complejidad ciclomática máxima | < 10 |
| Líneas por función máximo | < 50 |
| Duplicación de código | < 5% |
| Type hints | 100% |

### 6.2 Checklist de Completitud

```markdown
## Fase 1: Core
- [ ] DialogueState TypedDict implementado y testeado
- [ ] FlowContext TypedDict implementado y testeado
- [ ] 10 Commands implementados y testeados
- [ ] SoniConfig carga YAML correctamente
- [ ] Validación de config con errores claros

## Fase 2: Flow Management
- [ ] FlowManager.push_flow funciona
- [ ] FlowManager.pop_flow funciona
- [ ] FlowManager.get_active_context funciona
- [ ] FlowManager.set_slot funciona
- [ ] Slots aislados por flow_id

## Fase 3: Compiler
- [ ] CollectNodeFactory genera nodos correctos
- [ ] ActionNodeFactory genera nodos correctos
- [ ] BranchNodeFactory genera nodos con routing
- [ ] ConfirmNodeFactory genera nodos correctos
- [ ] SayNodeFactory genera nodos correctos
- [ ] WhileNodeFactory genera nodos con loops
- [ ] SubgraphBuilder compila flow simple
- [ ] SubgraphBuilder maneja jump_to
- [ ] SubgraphBuilder maneja branches

## Fase 4: Orchestrator
- [ ] OrchestratorGraph compila todos los flows
- [ ] Routing funciona según flow_stack
- [ ] Subgrafos se ejecutan correctamente
- [ ] Estado se sincroniza entre orchestrator y subgrafos

## Fase 5: DU
- [ ] SoniDU extrae comandos correctamente
- [ ] Signatures definidas para todos los casos
- [ ] Integración con DSPy funciona

## Fase 6: Runtime
- [ ] RuntimeLoop procesa mensajes
- [ ] Estado persiste entre turnos
- [ ] Checkpointing funciona
- [ ] Cleanup libera recursos

## Fase 7: Actions
- [ ] ActionRegistry registra acciones
- [ ] ActionHandler ejecuta acciones
- [ ] Errores se manejan correctamente

## Fase 8: Integración
- [ ] Ejemplo flight_booking funciona e2e
- [ ] Tests e2e pasan
- [ ] Documentación actualizada
```

---

## 7. Cronograma

```
Semana 1: Fundamentos
├── Día 1: Setup + Core types
├── Día 2: Commands + Errors
├── Día 3: Config + Validation
├── Día 4: FlowManager basics
└── Día 5: FlowManager advanced + State helpers

Semana 2: Compilación + Orchestration
├── Día 6: Node factories (collect, action)
├── Día 7: Node factories (branch, while, confirm, say)
├── Día 8: EdgeBuilder + SubgraphBuilder
├── Día 9: OrchestratorGraph
└── Día 10: Routing + Integration tests

Semana 3: DU + Runtime + Polish
├── Día 11: DSPy signatures + SoniDU
├── Día 12: RuntimeLoop
├── Día 13: Actions + Checkpointing
├── Día 14: E2E tests + Bug fixes
└── Día 15: Documentación + Cleanup
```

---

## 8. Recursos Necesarios

### 8.1 Humanos
- 1 desarrollador senior (tiempo completo, 3 semanas)

### 8.2 Herramientas
- Python 3.11+
- pytest + pytest-cov
- ruff (linting)
- mypy (type checking)
- LangGraph
- DSPy

### 8.3 Infraestructura
- Repositorio Git (existente)
- CI/CD (GitHub Actions existente)

---

## 9. Beneficios Esperados

### 9.1 Técnicos

1. **Código limpio y mantenible**
   - Sin duplicación
   - Responsabilidades claras
   - Fácil de entender

2. **Extensibilidad**
   - Nuevo step type = nuevo NodeFactory
   - Nuevo command = nueva clase + handler
   - Nuevo action = registro en ActionRegistry

3. **Testabilidad**
   - 90%+ cobertura desde el inicio
   - Tests como documentación
   - Refactoring sin miedo

4. **Performance**
   - Compilación en startup (no runtime)
   - Sin código muerto ejecutándose
   - Paths de ejecución claros

### 9.2 De Negocio

1. **Reducción de bugs** - TDD previene regresiones
2. **Velocidad de desarrollo** - Código predecible
3. **Onboarding más rápido** - Código autodocumentado
4. **Menos deuda técnica** - Empezar limpio

---

## 10. Aprobación

| Rol | Nombre | Firma | Fecha |
|-----|--------|-------|-------|
| Tech Lead | | | |
| Product Owner | | | |
| Engineering Manager | | | |

---

## Anexos

### Anexo A: Referencias

- `ideas.md` - Visión original del framework
- `ideas_architecture.md` - Diseño técnico detallado
- `docs/design/` - Documentación de diseño existente
- `archive/` - Código actual (después de mover)

### Anexo B: Dependencias

```toml
[project]
dependencies = [
    "langgraph>=1.0.5,<2.0.0",
    "dspy>=3.0.0,<4.0.0",
    "pydantic>=2.0.0,<3.0.0",
    "pyyaml>=6.0.0,<7.0.0",
    "fastapi>=0.115.0,<1.0.0",  # opcional, para server
    "uvicorn>=0.32.0,<1.0.0",   # opcional, para server
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0,<9.0.0",
    "pytest-cov>=6.0.0,<7.0.0",
    "pytest-asyncio>=0.24.0,<1.0.0",
    "pytest-mock>=3.14.0,<4.0.0",
    "ruff>=0.8.0,<1.0.0",
    "mypy>=1.13.0,<2.0.0",
]
```

### Anexo C: Ejemplo de Test Completo

```python
"""
tests/unit/flow/test_manager.py

Unit tests for FlowManager following AAA pattern.
"""
import pytest
from soni.core.types import DialogueState
from soni.flow.manager import FlowManager


class TestFlowManagerPushFlow:
    """Tests for FlowManager.push_flow method."""

    def test_push_flow_on_empty_stack_creates_single_context(self):
        """
        GIVEN an empty dialogue state with no flows
        WHEN push_flow is called with 'book_flight'
        THEN the flow stack contains exactly one flow context
        AND the flow context has the correct flow_name
        """
        # Arrange
        state: DialogueState = {
            "flow_stack": [],
            "flow_slots": {},
            "user_message": "",
            "last_response": "",
            "messages": [],
            "flow_state": "idle",
            "waiting_for_slot": None,
            "commands": [],
            "response": None,
            "action_result": None,
            "turn_count": 0,
            "metadata": {},
        }
        manager = FlowManager()

        # Act
        flow_id = manager.push_flow(state, "book_flight")

        # Assert
        assert len(state["flow_stack"]) == 1
        assert state["flow_stack"][0]["flow_name"] == "book_flight"
        assert state["flow_stack"][0]["flow_id"] == flow_id
        assert state["flow_stack"][0]["flow_state"] == "active"
        assert flow_id in state["flow_slots"]

    def test_push_flow_with_initial_slots_stores_slots(self):
        """
        GIVEN an empty dialogue state
        WHEN push_flow is called with initial slots
        THEN the slots are stored in flow_slots under the flow_id
        """
        # Arrange
        state: DialogueState = {
            "flow_stack": [],
            "flow_slots": {},
            # ... other fields
        }
        manager = FlowManager()
        initial_slots = {"origin": "NYC", "destination": "LAX"}

        # Act
        flow_id = manager.push_flow(
            state,
            "book_flight",
            inputs=initial_slots
        )

        # Assert
        assert state["flow_slots"][flow_id]["origin"] == "NYC"
        assert state["flow_slots"][flow_id]["destination"] == "LAX"


class TestFlowManagerPopFlow:
    """Tests for FlowManager.pop_flow method."""

    def test_pop_flow_removes_top_flow_from_stack(self):
        """
        GIVEN a state with two flows on the stack
        WHEN pop_flow is called
        THEN the top flow is removed
        AND the previous flow becomes active
        """
        # Arrange
        state: DialogueState = {
            "flow_stack": [
                {"flow_id": "f1", "flow_name": "main", "flow_state": "active"},
                {"flow_id": "f2", "flow_name": "sub", "flow_state": "active"},
            ],
            "flow_slots": {"f1": {}, "f2": {}},
        }
        manager = FlowManager()

        # Act
        manager.pop_flow(state, result="completed")

        # Assert
        assert len(state["flow_stack"]) == 1
        assert state["flow_stack"][0]["flow_name"] == "main"

    def test_pop_flow_on_empty_stack_raises_error(self):
        """
        GIVEN an empty flow stack
        WHEN pop_flow is called
        THEN a FlowStackError is raised
        """
        # Arrange
        state: DialogueState = {"flow_stack": [], "flow_slots": {}}
        manager = FlowManager()

        # Act & Assert
        with pytest.raises(FlowStackError) as exc_info:
            manager.pop_flow(state)

        assert "empty" in str(exc_info.value).lower()
```

---

**Documento preparado por**: Claude (AI Assistant)
**Para revisión de**: [Tu nombre / Tu jefe]
**Fecha de creación**: 2025-12-15
