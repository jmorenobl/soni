# Análisis de Causa Raíz: Problema de Salto de Flujo

## Resumen Ejecutivo

El problema de que el flujo "salte" pasos y ejecute acciones prematuramente no es un fallo del NLU ni de los validadores, sino un **problema estructural en la construcción del grafo de ejecución (LangGraph)**.

El sistema está construido asumiendo que los nodos se ejecutan secuencialmente (`A -> B -> C`), pero no tiene mecanismo para **detener la ejecución** cuando un nodo solicita información al usuario. Como resultado, el grafo ejecuta todos los nodos del flujo en una sola pasada, utilizando los valores extraídos inicialmente por el NLU (incluso si son incorrectos) y ignorando los intentos de los nodos de recolección (`collect_slot_node`) de pedir input.

## Detalles Técnicos

### 1. Construcción del Grafo (Causa Principal)

En `src/soni/dm/graph.py`, el método `_build_from_dag` utiliza aristas directas e incondicionales:

```python
# src/soni/dm/graph.py
for edge in dag.edges:
    # ...
    else:
        # Regular edge
        graph.add_edge(edge.source, edge.target)
```

En **LangGraph**, `add_edge(A, B)` significa "Tan pronto como A termine, ejecutar B inmediatamente". No hay lógica condicional para verificar si A necesita detenerse para esperar input del usuario.

**Consecuencia**: Cuando `collect_origin` genera un prompt ("Where are you flying from?"), el grafo simplemente actualiza el estado con ese mensaje y **continúa inmediatamente** a `collect_destination`.

### 2. Persistencia de Valores Incorrectos (Factor Contribuyente)

En `src/soni/dm/nodes.py`, la lógica de `force_explicit_collection` detecta correctamente que debe pedir el slot, pero **no limpia el valor del slot en el estado**:

```python
# src/soni/dm/nodes.py
if force_explicit_collection:
    # ...
    # Clear slot to force explicit collection
    is_filled = False # Solo actualiza variable local
```

El nodo retorna un update con `last_response` y un evento de trace, pero **no retorna** `{"slots": {slot_name: None}}`.

**Consecuencia**: El valor incorrecto extraído por el NLU (ej. "flight" en el slot `origin`) permanece en el estado global. Como el grafo no se detiene, el siguiente nodo lee este valor, lo considera válido (si pasa validación básica), y continúa.

### 3. El Efecto "Bola de Nieve"

1.  **Inicio**: Usuario dice "I want to book a flight". NLU extrae erróneamente `origin="flight"`, `destination="book"`, etc.
2.  **Paso 1 (`collect_origin`)**: Detecta que debe confirmar. Genera prompt. NO limpia el slot en el estado.
3.  **Transición Inmediata**: El grafo ignora el prompt y ejecuta el Paso 2.
4.  **Paso 2 (`collect_destination`)**: Lee `destination="book"`. Si no hay lógica de forzado (o si ya hay evento), lo da por válido.
5.  **...**
6.  **Acción Final**: Se ejecuta porque todos los slots parecen estar llenos en el estado.

## Recomendaciones de Refactorización

Para solucionar esto, se requiere un cambio de diseño en cómo se construye el grafo y cómo se comportan los nodos.

### 1. Implementar Aristas Condicionales (Router)

Modificar `SoniGraphBuilder` para usar `add_conditional_edges` en lugar de `add_edge`.

Se debe introducir una función de enrutamiento (`router`) entre nodos:

```python
def route_node(state: DialogueState) -> Literal["next_node", END]:
    # Si el último evento fue una solicitud de slot o error, DETENER
    last_event = state.trace[-1] if state.trace else {}
    if last_event.get("event") in ["slot_collection", "validation_error"]:
        return END
    return "next_node"
```

### 2. Limpiar Estado en `collect_slot_node`

Modificar `collect_slot_node` para que, cuando decida forzar la recolección, explícitamente limpie el valor en el estado:

```python
if force_explicit_collection:
    # ...
    return {
        "slots": {slot_name: None}, # CRÍTICO: Eliminar el valor incorrecto
        "last_response": prompt,
        "trace": ...
    }
```

### 3. Revisión de Lógica de NLU (Opcional pero Recomendado)

Aunque el problema principal es el grafo, que el NLU extraiga "flight" como ciudad indica que los modelos o la configuración de entidades necesitan ajuste. Sin embargo, con las correcciones 1 y 2, el sistema será robusto incluso ante estos errores del NLU.

## Conclusión

El sistema actual es un "pipeline" de ejecución continua. Debe transformarse en una **máquina de estados interactiva** que sepa cuándo pausar y ceder el control al usuario. La refactorización de `SoniGraphBuilder` es prioritaria.
