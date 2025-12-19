## Task: LG-005 - Evaluate LangGraph Store API for Cross-Session Memory

**ID de tarea:** LG-005
**Hito:** LangGraph Modernization
**Dependencias:** LG-002 (context_schema adoption)
**Duración estimada:** 4-6 horas (research + spike)
**Prioridad:** Baja (Future Enhancement)

### Objetivo

Evaluar el Store API de LangGraph para implementar memoria cross-session (preferencias de usuario, historial persistente, perfil) y determinar si es apropiado para las necesidades de Soni.

### Contexto

LangGraph ofrece un Store API para persistencia de datos fuera del estado del grafo:

```python
from langgraph.config import get_store

def my_node(state: State):
    store = get_store()
    user_prefs = store.get(("users", state["user_id"]), "preferences")
    store.put(("users", state["user_id"]), "last_seen", datetime.now())
```

**Casos de uso potenciales en Soni:**
- Preferencias de usuario (idioma, formato, etc.)
- Historial de conversaciones pasadas
- Perfil de usuario (nombre, datos frecuentes)
- Cache de información externa

**Estado actual:**
- Soni almacena todo en `flow_slots` dentro del estado
- Los slots se pierden al finalizar el flow
- No hay persistencia cross-session

**Referencia:** `ref/langgraph/libs/langgraph/langgraph/config.py` - `get_store()`

**Análisis:** `docs/analysis/LANGGRAPH_USAGE_REVIEW.md` - Sección 3.7

### Entregables

- [ ] Spike de implementación con Store API
- [ ] Documento de evaluación con pros/cons
- [ ] Decisión: adoptar o no adoptar
- [ ] Si se adopta: plan de implementación detallado

### Implementación (Spike)

#### Paso 1: Crear spike básico

**Archivo:** `spikes/langgraph_store_spike.py`

```python
"""Spike to evaluate LangGraph Store API."""

from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.config import get_store
from typing import TypedDict


class State(TypedDict):
    user_id: str
    message: str


def node_with_store(state: State):
    """Node that uses Store API."""
    store = get_store()

    # Read user preferences
    # Note: store.get() returns an Item object, access .value for data
    namespace = ("users", state["user_id"])
    prefs_item = store.get(namespace, "preferences")

    if prefs_item is None:
        prefs = {"language": "en", "timezone": "UTC"}
        store.put(namespace, "preferences", prefs)
    else:
        prefs = prefs_item.value

    # Read visit count
    visits_item = store.get(namespace, "visit_count")
    visits = visits_item.value if visits_item else 0
    store.put(namespace, "visit_count", visits + 1)

    return {
        "message": f"Hello! Visit #{visits + 1}. Lang: {prefs['language']}"
    }


def main():
    """Run the spike."""
    builder = StateGraph(State)
    builder.add_node("greet", node_with_store)
    builder.set_entry_point("greet")
    builder.set_finish_point("greet")

    # Create store and checkpointer
    store = InMemoryStore()
    checkpointer = MemorySaver()

    graph = builder.compile(
        checkpointer=checkpointer,
        store=store,  # Attach store to graph
    )

    # First invocation
    config = {"configurable": {"thread_id": "user123"}}
    result1 = graph.invoke({"user_id": "user123", "message": ""}, config)
    print(f"First: {result1}")

    # Second invocation - should remember visit count
    result2 = graph.invoke({"user_id": "user123", "message": ""}, config)
    print(f"Second: {result2}")

    # Different user - should start fresh
    config2 = {"configurable": {"thread_id": "user456"}}
    result3 = graph.invoke({"user_id": "user456", "message": ""}, config2)
    print(f"Different user: {result3}")


if __name__ == "__main__":
    main()
```

#### Paso 2: Evaluar características

**Criterios de evaluación:**

| Criterio | Peso | Store API | flow_slots actual |
|----------|------|-----------|-------------------|
| Persistencia cross-session | Alto | ✅ | ❌ |
| Integración con LangGraph | Alto | ✅ Native | ⚠️ Manual |
| Simplicidad de uso | Medio | ✅ | ✅ |
| Type safety | Medio | ⚠️ | ✅ |
| Testabilidad | Medio | ⚠️ | ✅ |
| Overhead de implementación | Bajo | Alto | Ninguno |

#### Paso 3: Documentar decisión

**Archivo:** `docs/adr/ADR-XXX-Store-API-Decision.md`

```markdown
# ADR-XXX: LangGraph Store API Adoption

## Status
[Proposed | Accepted | Rejected]

## Context
[Summary of evaluation]

## Decision
[Adopt / Not adopt Store API]

## Consequences
[Positive and negative impacts]

## Alternatives Considered
- Store API (evaluated)
- External database (Redis, PostgreSQL)
- Custom persistence layer
```

### Preguntas a Responder

1. **Performance:** ¿Qué latencia añade el Store API?
2. **Backends:** ¿Qué backends de persistencia soporta?
3. **Scaling:** ¿Cómo escala con muchos usuarios?
4. **Migration:** ¿Cómo migrar datos existentes?
5. **Complexity:** ¿Vale la pena la complejidad añadida?

### Criterios de Éxito

- [ ] Spike ejecuta correctamente
- [ ] Documento de evaluación completo
- [ ] Decisión documentada en ADR
- [ ] Si se adopta: tareas de implementación creadas

### Validación

```bash
# Ejecutar spike
uv run python spikes/langgraph_store_spike.py

# Verificar persistencia
# (revisar output del spike)
```

### Referencias

- [LangGraph Store](ref/langgraph/libs/langgraph/langgraph/store/)
- [Store examples](ref/langgraph/examples/memory/)
- [Analysis Document](docs/analysis/LANGGRAPH_USAGE_REVIEW.md#37-store-api)

### Notas Adicionales

- Esta es una tarea de EVALUACIÓN, no de implementación
- La implementación completa sería una tarea separada si se decide adoptar
- Considerar si las necesidades de Soni justifican esta complejidad
- Alternativa: usar base de datos externa con wrapper propio
- Store API es relativamente nuevo en LangGraph - verificar estabilidad
