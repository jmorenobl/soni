# Estrategia de Refactorización: Sistema de Flujo Interactivo

## Resumen Ejecutivo

Esta estrategia detalla la refactorización necesaria para transformar el sistema de un **pipeline continuo** a una **máquina de estados interactiva** que puede pausar la ejecución cuando necesita input del usuario.

**Problema Principal**: El sistema actual ejecuta todos los nodos del flujo en una sola pasada, ignorando cuando un nodo necesita detenerse para esperar input del usuario.

**Solución**: Implementar aristas condicionales en LangGraph que detecten cuando un nodo solicita información y detengan la ejecución, retornando control al usuario.

## Objetivos de la Refactorización

1. **Detener ejecución cuando se solicita input**: El grafo debe pausar cuando un nodo `collect` necesita información del usuario.
2. **Limpiar valores incorrectos**: Los nodos deben limpiar valores inválidos del estado cuando fuerzan recolección explícita.
3. **Testeable incrementalmente**: Cada componente debe ser testeable de forma independiente.
4. **Diseño correcto desde el inicio**: No hay restricciones de retrocompatibilidad (pre-v1.0), podemos hacer cambios arquitectónicos significativos.

## Principios de Diseño

- **Incremental**: Cambios pequeños y testeables en cada paso
- **Test-Driven**: Escribir tests antes de implementar cambios
- **SOLID**: Mantener principios de diseño sólido
- **No Retrocompatibilidad**: Pre-v1.0, podemos hacer cambios arquitectónicos significativos sin preocuparnos por compatibilidad
- **Defensive**: Validar y limpiar estado en cada paso

## Fases de Implementación

### Fase 1: Preparación y Análisis (Sin Cambios de Código)

**Objetivo**: Entender completamente el sistema actual y preparar el terreno.

#### 1.1 Análisis de Estado Actual

**Tareas**:
- [ ] Documentar todos los tipos de nodos actuales (`UNDERSTAND`, `COLLECT`, `ACTION`, `BRANCH`)
- [ ] Mapear cómo se construyen las aristas actualmente
- [ ] Identificar todos los lugares donde se usa `add_edge` vs `add_conditional_edges`
- [ ] Documentar el flujo de ejecución actual paso a paso

**Archivos a revisar**:
- `src/soni/dm/graph.py` - `_build_from_dag`
- `src/soni/compiler/builder.py` - `_build_graph`
- `src/soni/dm/nodes.py` - Todos los nodos
- `src/soni/dm/routing.py` - Funciones de routing existentes

**Criterio de Éxito**: Documento completo que explique cómo funciona el sistema actual.

#### 1.2 Definir Contrato de Nodos

**Tareas**:
- [ ] Definir qué eventos en `trace` indican que un nodo necesita detenerse
- [ ] Definir qué eventos indican que un nodo puede continuar
- [ ] Crear constantes para eventos estándar
- [ ] Documentar el contrato en docstrings

**Eventos propuestos**:
```python
# Eventos que detienen ejecución
STOP_EVENTS = {
    "slot_collection",      # Nodo está pidiendo un slot
    "validation_error",     # Error de validación que requiere corrección
    "user_confirmation",   # Necesita confirmación del usuario
}

# Eventos que permiten continuar
CONTINUE_EVENTS = {
    "slot_collected",      # Slot fue recolectado exitosamente
    "action_completed",    # Acción completada
    "flow_activated",      # Flujo activado
}
```

**Criterio de Éxito**: Constantes definidas y documentadas en `src/soni/dm/constants.py`.

#### 1.3 Crear Tests de Regresión

**Tareas**:
- [ ] Crear test que reproduzca el problema actual (flujo saltando pasos)
- [ ] Crear test que verifique comportamiento esperado (flujo se detiene)
- [ ] Documentar casos de prueba edge cases

**Archivo**: `tests/integration/test_interactive_flow.py`

**Criterio de Éxito**: Tests que fallan con el comportamiento actual y pasarán con la refactorización.

---

### Fase 2: Implementar Router de Continuación (Core)

**Objetivo**: Crear la función de routing que decide si el flujo debe continuar o detenerse.

#### 2.1 Crear Función Router Base

**Ubicación**: `src/soni/dm/routing.py`

**Tareas**:
- [ ] Crear función `should_continue_flow(state: DialogueState) -> Literal["continue", "stop"]`
- [ ] Implementar lógica que revisa el último evento en `trace`
- [ ] Si último evento está en `STOP_EVENTS`, retornar `"stop"`
- [ ] Si último evento está en `CONTINUE_EVENTS` o no hay eventos, retornar `"continue"`
- [ ] Agregar logging detallado

**Código propuesto**:
```python
from typing import Literal

from soni.dm.constants import CONTINUE_EVENTS, STOP_EVENTS

def should_continue_flow(state: DialogueState | dict[str, Any]) -> Literal["continue", "stop"]:
    """
    Determine if flow execution should continue or stop.

    Stops execution if the last trace event indicates that user input is needed.
    This enables interactive flows that pause for user confirmation.

    Args:
        state: Current dialogue state

    Returns:
        "stop" if execution should pause for user input
        "continue" if execution can proceed to next node
    """
    # Implementation here
```

**Tests**:
- [ ] Test: `test_should_continue_after_slot_collection` - Debe retornar "stop"
- [ ] Test: `test_should_continue_after_action` - Debe retornar "continue"
- [ ] Test: `test_should_continue_after_validation_error` - Debe retornar "stop"
- [ ] Test: `test_should_continue_empty_trace` - Debe retornar "continue"

**Criterio de Éxito**: Función implementada, testeada, y documentada. Tests pasan.

#### 2.2 Integrar Router en Construcción de Grafo

**Ubicación**: `src/soni/dm/graph.py` - `_build_from_dag`

**Tareas**:
- [ ] Modificar `_build_from_dag` para usar aristas condicionales entre nodos
- [ ] Reemplazar `graph.add_edge(source, target)` con `graph.add_conditional_edges`
- [ ] Usar `should_continue_flow` como función de routing
- [ ] Mapear `"continue"` -> `target`, `"stop"` -> `END`
- [ ] Mantener aristas directas para `START` y `END`

**Código propuesto**:
```python
def _build_from_dag(self, dag: FlowDAG, context: RuntimeContext) -> StateGraph:
    graph = StateGraph(DialogueState)

    # Add nodes (sin cambios)
    for node in dag.nodes:
        node_fn = self._create_node_function_from_dag(node, context)
        graph.add_node(node.id, node_fn)

    # Add edges with conditional routing
    for edge in dag.edges:
        if edge.source == "__start__":
            graph.add_edge(START, edge.target)
        elif edge.target == "__end__":
            # Use conditional edge to check if we should stop
            from soni.dm.routing import should_continue_flow
            graph.add_conditional_edges(
                edge.source,
                should_continue_flow,
                {
                    "continue": END,  # Continue to end if no stop needed
                    "stop": END,     # Stop at end if user input needed
                }
            )
        else:
            # Regular edge between nodes - use conditional routing
            from soni.dm.routing import should_continue_flow
            graph.add_conditional_edges(
                edge.source,
                should_continue_flow,
                {
                    "continue": edge.target,  # Continue to next node
                    "stop": END,              # Stop if user input needed
                }
            )

    return graph
```

**Tests**:
- [ ] Test: Verificar que grafo se construye correctamente
- [ ] Test: Verificar que aristas condicionales están configuradas
- [ ] Test: Verificar que `START` y `END` mantienen aristas directas

**Criterio de Éxito**: Grafo se construye con aristas condicionales. Tests pasan.

---

### Fase 3: Corregir `collect_slot_node` (Crítico)

**Objetivo**: Asegurar que `collect_slot_node` limpia valores incorrectos del estado.

#### 3.1 Limpiar Estado en `force_explicit_collection`

**Ubicación**: `src/soni/dm/nodes.py` - `collect_slot_node`

**Tareas**:
- [ ] Modificar lógica de `force_explicit_collection` para retornar `{"slots": {slot_name: None}}`
- [ ] Asegurar que el valor incorrecto se elimina del estado
- [ ] Agregar logging cuando se limpia un slot
- [ ] Mantener evento `slot_collection` en trace

**Código propuesto**:
```python
if force_explicit_collection:
    logger.info(
        f"Slot '{slot_name}' was extracted by NLU but never explicitly collected - "
        f"forcing explicit collection even though NLU extracted '{slot_value}'"
    )
    # CRITICAL: Clear the incorrect value from state
    return {
        "slots": {slot_name: None},  # Clear invalid value
        "last_response": prompt,
        "trace": state.trace + [
            {
                "event": "slot_collection",
                "data": {"slot": slot_name, "prompt": prompt},
            }
        ],
    }
```

**Tests**:
- [ ] Test: `test_collect_node_clears_invalid_slot` - Verificar que slot se limpia
- [ ] Test: `test_collect_node_preserves_valid_slot` - Verificar que slot válido se mantiene
- [ ] Test: `test_collect_node_returns_stop_event` - Verificar que retorna evento de stop

**Criterio de Éxito**: `collect_slot_node` limpia valores incorrectos. Tests pasan.

#### 3.2 Mejorar Validación de Slots

**Ubicación**: `src/soni/dm/nodes.py` - `collect_slot_node`

**Tareas**:
- [ ] Revisar lógica de validación para asegurar que siempre valida
- [ ] Asegurar que valores que fallan validación se limpian
- [ ] Agregar logging detallado de decisiones de validación

**Criterio de Éxito**: Validación robusta implementada. Tests pasan.

---

### Fase 4: Integración y Testing End-to-End

**Objetivo**: Verificar que todo funciona correctamente en conjunto.

#### 4.1 Test E2E Completo

**Tareas**:
- [ ] Ejecutar `test_e2e_flight_booking_complete_flow` - Debe pasar
- [ ] Verificar que el flujo se detiene en cada paso de recolección
- [ ] Verificar que el flujo continúa después de recibir input
- [ ] Verificar que valores incorrectos se limpian

**Criterio de Éxito**: Test E2E pasa completamente.

#### 4.2 Tests de Performance

**Tareas**:
- [ ] Ejecutar tests de performance
- [ ] Verificar que latencia no aumenta significativamente
- [ ] Verificar que throughput se mantiene

**Criterio de Éxito**: Tests de performance pasan.

#### 4.3 Tests de Regresión

**Tareas**:
- [ ] Ejecutar suite completa de tests
- [ ] Verificar que no hay regresiones
- [ ] Documentar cualquier cambio de comportamiento esperado

**Criterio de Éxito**: 100% de tests pasando.

---

### Fase 5: Optimización y Refinamiento

**Objetivo**: Mejorar la implementación y optimizar el código.

#### 5.1 Optimizar Router

**Tareas**:
- [ ] Revisar eficiencia del router
- [ ] Optimizar acceso a `trace` (puede ser costoso si es muy largo)
- [ ] Considerar cachear último evento en estado

**Criterio de Éxito**: Router optimizado sin perder funcionalidad.

#### 5.2 Mejorar Logging

**Tareas**:
- [ ] Agregar logging estructurado en puntos clave
- [ ] Agregar métricas de cuántas veces se detiene el flujo
- [ ] Documentar eventos de trace para debugging

**Criterio de Éxito**: Logging completo y útil para debugging.

#### 5.3 Documentación

**Tareas**:
- [ ] Actualizar documentación de arquitectura
- [ ] Documentar nuevo comportamiento de flujos interactivos
- [ ] Crear ejemplos de uso

**Criterio de Éxito**: Documentación completa y actualizada.

---

## Plan de Implementación Detallado

### Semana 1: Fase 1 (Preparación)

**Día 1-2**: Análisis y documentación
- Análisis completo del sistema actual
- Documentar tipos de nodos y aristas
- Crear diagramas de flujo actual

**Día 3-4**: Definir contratos
- Crear `src/soni/dm/constants.py` con eventos
- Documentar contrato de nodos
- Crear tests de regresión

**Día 5**: Revisión y validación
- Revisar análisis con equipo
- Validar contratos definidos
- Preparar para Fase 2

### Semana 2: Fase 2 (Router Core)

**Día 1-2**: Implementar router
- Implementar `should_continue_flow`
- Crear tests unitarios
- Validar lógica

**Día 3-4**: Integrar en grafo
- Modificar `_build_from_dag`
- Crear tests de integración
- Validar construcción de grafo

**Día 5**: Testing y refinamiento
- Ejecutar tests completos
- Refinar implementación
- Documentar cambios

### Semana 3: Fase 3 (Corregir Nodos)

**Día 1-2**: Corregir `collect_slot_node`
- Implementar limpieza de estado
- Crear tests
- Validar comportamiento

**Día 3-4**: Mejorar validación
- Revisar lógica de validación
- Agregar logging
- Crear tests adicionales

**Día 5**: Testing y refinamiento
- Ejecutar tests completos
- Refinar implementación
- Documentar cambios

### Semana 4: Fase 4 (Integración)

**Día 1-2**: Tests E2E
- Ejecutar y corregir tests E2E
- Verificar comportamiento completo
- Documentar resultados

**Día 3-4**: Tests de performance
- Ejecutar tests de performance
- Optimizar si es necesario
- Documentar métricas

**Día 5**: Tests de regresión
- Ejecutar suite completa
- Corregir regresiones
- Validar que todo funciona

### Semana 5: Fase 5 (Optimización)

**Día 1-2**: Optimización
- Optimizar router
- Mejorar eficiencia
- Validar mejoras

**Día 3-4**: Logging y documentación
- Mejorar logging
- Actualizar documentación
- Crear ejemplos

**Día 5**: Revisión final
- Revisión completa del código
- Validar que cumple objetivos
- Preparar release

---

## Criterios de Aceptación por Fase

### Fase 1: Preparación
- ✅ Documentación completa del sistema actual
- ✅ Constantes de eventos definidas
- ✅ Tests de regresión creados

### Fase 2: Router Core
- ✅ Función `should_continue_flow` implementada y testeada
- ✅ Grafo construido con aristas condicionales
- ✅ Tests de integración pasan

### Fase 3: Corregir Nodos
- ✅ `collect_slot_node` limpia valores incorrectos
- ✅ Validación robusta implementada
- ✅ Tests pasan

### Fase 4: Integración
- ✅ Test E2E pasa
- ✅ Tests de performance pasan
- ✅ Suite completa de tests pasa

### Fase 5: Optimización
- ✅ Código optimizado
- ✅ Logging completo
- ✅ Documentación actualizada

---

## Riesgos y Mitigaciones

### Riesgo 1: Cambios Arquitectónicos Significativos

**Mitigación**:
- Implementar cambios de forma incremental
- Tests exhaustivos antes de cada cambio
- Documentar cambios arquitectónicos claramente
- Nota: No hay restricción de retrocompatibilidad pre-v1.0

### Riesgo 2: Performance Degradada

**Mitigación**:
- Medir performance en cada fase
- Optimizar router si es necesario
- Considerar cachear último evento

### Riesgo 3: Complejidad Aumentada

**Mitigación**:
- Documentar claramente cambios
- Mantener código simple y legible
- Agregar logging detallado

---

## Métricas de Éxito

1. **Funcionalidad**: Test E2E pasa completamente
2. **Performance**: Latencia p95 < 1.5s (mantener objetivo actual)
3. **Calidad**: 100% de tests pasando
4. **Cobertura**: Coverage ≥ 85% (mantener objetivo actual)

---

## Notas de Implementación

### Consideraciones de LangGraph

- `add_conditional_edges` requiere función que retorne `str` o `Literal`
- La función de routing recibe el estado completo
- `END` es una constante especial de LangGraph

### Consideraciones de Estado

- `trace` puede crecer mucho - considerar límite
- Último evento es el más importante para routing
- Estado debe ser serializable para checkpointing

### Consideraciones de Testing

- Mockear LangGraph puede ser complejo
- Usar tests de integración reales cuando sea posible
- Verificar comportamiento con tests E2E

---

## Referencias

- [LangGraph Conditional Edges Documentation](https://langchain-ai.github.io/langgraph/concepts/low_level/#conditional-edges)
- Análisis de Causa Raíz: `docs/validation/flow-skipping-issue-analysis-report.md`
- Arquitectura Actual: `docs/architecture/`

---

## Conclusión

Esta estrategia transforma el sistema de un pipeline continuo a una máquina de estados interactiva de forma incremental y testeable. Cada fase tiene criterios de éxito claros y puede ser validada independientemente antes de continuar.

La implementación debe seguir principios SOLID y aprovechar la libertad de hacer cambios arquitectónicos significativos sin restricciones de retrocompatibilidad (pre-v1.0).
