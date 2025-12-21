# Estrategia de Refactorización: Flujos Interactivos (Enhanced)

> [!NOTE]
> Esta es una versión mejorada de `workflow/strategy/Interactive-Flow-Refactoring-Strategy.md`, enriquecida con detalles técnicos específicos y estándares de ingeniería.

## Contexto

El sistema actual ejecuta los flujos de principio a fin sin detenerse, lo que causa que se salten pasos de recolección de información cuando el NLU extrae valores incorrectos o incompletos.

**Objetivo**: Transformar el motor de ejecución en una **Máquina de Estados Interactiva** que se detenga determinísticamente cuando se requiera input del usuario.

## Principios de Ingeniería

1.  **SOLID**: Responsabilidad única para el Router (separado del GraphBuilder).
2.  **Determinismo**: La decisión de detenerse debe basarse puramente en el estado actual.
3.  **Zero-Trust**: Los nodos no deben confiar ciegamente en el NLU; deben validar y limpiar el estado si es necesario.
4.  **Testability**: Cada componente (Router, Nodos, Grafo) debe ser testeable aisladamente.

---

## Fases de Implementación

### Fase 1: Preparación y Definiciones

**Objetivo**: Establecer las bases y contratos sin modificar el comportamiento runtime aún.

#### 1.1 Definición de Eventos

**Ubicación**: `src/soni/core/events.py` (Nuevo)

**Tareas**:
- [ ] Definir constantes para eventos de traza para evitar "magic strings".

```python
# src/soni/core/events.py
EVENT_SLOT_COLLECTION = "slot_collection"
EVENT_VALIDATION_ERROR = "validation_error"
EVENT_ACTION_EXECUTED = "action_executed"
```

#### 1.2 Análisis de Impacto

- [ ] Verificar si `DialogueState` necesita cambios (parece que no, `trace` es suficiente).

---

### Fase 2: Implementación del Router (Core)

**Objetivo**: Introducir aristas condicionales en el grafo para detener la ejecución cuando sea necesario.

#### 2.1 Implementar Lógica de Routing

**Ubicación**: `src/soni/dm/routing.py` (Nuevo módulo)

**Tareas**:
- [ ] Implementar función pura `should_continue_flow`.
- [ ] **Estándar**: Uso estricto de Type Hints y Docstrings.

**Código propuesto**:
```python
# src/soni/dm/routing.py
from typing import Literal
from soni.core.state import DialogueState
from soni.core.events import EVENT_SLOT_COLLECTION, EVENT_VALIDATION_ERROR

def should_continue_flow(state: DialogueState) -> Literal["next", "end"]:
    """
    Determines if the flow should continue to the next node or stop.

    Args:
        state: Current dialogue state

    Returns:
        "end" if the flow should stop (wait for user input), "next" otherwise.
    """
    if not state.trace:
        return "next"

    last_event = state.trace[-1]
    event_type = last_event.get("event")

    # Stop if we just asked for a slot or encountered a validation error
    if event_type in [EVENT_SLOT_COLLECTION, EVENT_VALIDATION_ERROR]:
        return "end"

    return "next"
```

**Tests Unitarios**:
- [ ] `test_router_stops_on_slot_collection`: Verificar retorno "end".
- [ ] `test_router_stops_on_validation_error`: Verificar retorno "end".
- [ ] `test_router_continues_on_action`: Verificar retorno "next".
- [ ] `test_router_continues_on_empty_trace`: Verificar retorno "next".

#### 2.2 Integrar Router en GraphBuilder

**Ubicación**: `src/soni/dm/graph.py`

**Tareas**:
- [ ] Modificar `_build_from_dag` para usar `add_conditional_edges`.
- [ ] Importar `should_continue_flow` y constantes.

**Código propuesto (Conceptual)**:
```python
# En _build_from_dag
from soni.dm.routing import should_continue_flow

for edge in dag.edges:
    if edge.target == "__end__":
        graph.add_edge(edge.source, END)
    else:
        # Conditional edge: Check if we should stop or continue to target
        graph.add_conditional_edges(
            edge.source,
            should_continue_flow,
            {
                "next": edge.target,
                "end": END
            }
        )
```

---

### Fase 3: Corrección de Nodos (State Hygiene)

**Objetivo**: Asegurar que el estado refleje la realidad (si pedimos un slot, ese slot no debe tener valor).

#### 3.1 Limpieza de Estado en `collect_slot_node`

**Ubicación**: `src/soni/dm/nodes.py`

**Problema**: Actualmente `collect_slot_node` detecta que debe preguntar, pero no borra el valor "sucio" del NLU del estado global.

**Solución**:
```python
if force_explicit_collection:
    logger.info(...)
    # CRITICAL: Clear the incorrect value from state explicitly
    return {
        "slots": {slot_name: None},  # Clear invalid value
        "last_response": prompt,
        "trace": state.trace + [...]
    }
```

**Tests Unitarios**:
- [ ] `test_collect_node_clears_invalid_slot`: Simular estado con slot sucio y verificar que el output incluye `slots: {name: None}`.

---

### Fase 4: Integración y Verificación

**Objetivo**: Validar el sistema completo.

#### 4.1 Test End-to-End (El que falla actualmente)

**Test**: `test_e2e_flight_booking_complete_flow`

**Flujo Esperado**:
1. User: "Book flight" -> System: "Where from?" (STOP)
2. User: "NYC" -> System: "Where to?" (STOP)
   ...

**Verificación**:
- El test debe pasar sin modificaciones (o con mínimas adaptaciones si el comportamiento de error cambia).

#### 4.2 Tests de Regresión

- Ejecutar toda la suite de tests para asegurar que no rompimos flujos existentes (aunque este cambio es profundo, debería ser transparente para flujos bien formados).

---

## Plan de Trabajo Inmediato

1.  Crear `src/soni/core/events.py`.
2.  Crear `src/soni/dm/routing.py` con tests.
3.  Modificar `src/soni/dm/graph.py`.
4.  Modificar `src/soni/dm/nodes.py`.
5.  Ejecutar tests.
