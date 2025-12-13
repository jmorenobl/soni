## Task: 339 - Fix Cancellation Infinite Loop

**ID de tarea:** 339
**Hito:** Bug Fixes - Critical
**Dependencias:** Ninguna
**Duración estimada:** 4-6 horas

### Objetivo

Corregir el loop infinito que ocurre cuando el usuario cancela un flow. El test `test_scenario_5_cancellation` falla con `GraphRecursionError: Recursion limit of 25 reached`.

### Contexto

**Problema identificado:**
- Cuando el usuario dice "Actually, cancel this" durante un flow activo, el sistema entra en un loop infinito
- El error ocurre en `test_scenario_5_cancellation` que valida el patrón CANCELLATION
- El sistema debería limpiar el flow_stack y retornar a estado `idle`, pero en su lugar entra en un ciclo de ejecución

**Referencias:**
- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 2.1
- `tests/integration/test_all_scenarios.py::TestScenario5Cancellation::test_scenario_5_cancellation`
- `src/soni/dm/nodes/handle_cancellation.py`
- `src/soni/dm/routing.py` - `route_after_cancellation`

### Entregables

- [ ] El test `test_scenario_5_cancellation` pasa sin errores
- [ ] `handle_cancellation` limpia correctamente el flow_stack
- [ ] El routing después de cancelación retorna correctamente a estado `idle`
- [ ] No hay loops infinitos en ningún escenario de cancelación
- [ ] Todos los tests de integración relacionados pasan

### Implementación Detallada

#### Paso 1: Investigar el loop infinito

**Archivo(s) a revisar:**
- `src/soni/dm/nodes/handle_cancellation.py`
- `src/soni/dm/routing.py` - función `route_after_cancellation`
- `src/soni/flow/manager.py` - métodos de limpieza de flow_stack

**Acciones:**
1. Ejecutar el test fallido con debug para identificar dónde se produce el loop
2. Revisar qué retorna `handle_cancellation_node`
3. Revisar a dónde rutea `route_after_cancellation`
4. Verificar que el flow_stack se limpia correctamente

**Comando de debug:**
```bash
uv run pytest tests/integration/test_all_scenarios.py::TestScenario5Cancellation::test_scenario_5_cancellation -v --tb=long -s
```

#### Paso 2: Corregir handle_cancellation

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_cancellation.py`

**Verificaciones:**
- El nodo debe limpiar completamente el flow_stack
- Debe establecer `conversation_state="idle"`
- Debe limpiar `current_step`, `waiting_for_slot`, etc.
- No debe dejar referencias a flows cancelados

**Código esperado:**
```python
# handle_cancellation debe retornar:
{
    "flow_stack": [],  # Limpiar completamente
    "conversation_state": "idle",
    "current_step": None,
    "waiting_for_slot": None,
    "current_prompted_slot": None,
    # ... otros campos relacionados con el flow cancelado
}
```

#### Paso 3: Corregir routing después de cancelación

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

**Verificaciones:**
- `route_after_cancellation` debe retornar `"generate_response"` cuando el estado es `idle`
- No debe crear loops (no debe volver a `understand` si no hay user_message)
- Debe manejar correctamente el caso cuando no hay flow activo

#### Paso 4: Agregar validaciones adicionales

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_cancellation.py`

**Verificaciones:**
- Agregar logs para debugging
- Validar que el flow_stack está vacío después de cancelación
- Asegurar que no hay referencias colgantes a flows cancelados

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_all_scenarios.py`

**Test existente que debe pasar:**
```python
async def test_scenario_5_cancellation(...):
    # Este test ya existe y debe pasar después de la corrección
```

**Tests adicionales a considerar:**
```python
# Test: Cancelación con múltiples flows en stack
async def test_cancellation_with_multiple_flows_in_stack(...):
    """Test que cancelación limpia todo el stack, no solo el flow activo."""

# Test: Cancelación cuando no hay flow activo
async def test_cancellation_when_no_active_flow(...):
    """Test que cancelación maneja correctamente cuando no hay flow activo."""
```

### Criterios de Éxito

- [ ] `test_scenario_5_cancellation` pasa sin errores
- [ ] No hay `GraphRecursionError` en ningún escenario de cancelación
- [ ] El flow_stack se limpia completamente después de cancelación
- [ ] El `conversation_state` es `idle` después de cancelación
- [ ] Todos los tests de integración pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**
```bash
# Ejecutar test específico
uv run pytest tests/integration/test_all_scenarios.py::TestScenario5Cancellation::test_scenario_5_cancellation -v

# Ejecutar todos los tests de cancelación
uv run pytest tests/integration/ -k cancellation -v

# Ejecutar suite completa de integración
uv run pytest tests/integration/ -v
```

**Resultado esperado:**
- Todos los tests pasan sin loops infinitos
- El estado después de cancelación es correcto (idle, flow_stack vacío)

### Referencias

- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 2.1
- `docs/design/04-state-machine.md` - State machine design
- `docs/design/05-message-flow.md` - Message flow design
- `src/soni/dm/nodes/handle_cancellation.py` - Implementación actual
- `src/soni/dm/routing.py` - Routing logic

### Notas Adicionales

- Este es un bug crítico que bloquea la funcionalidad de cancelación
- El problema podría estar relacionado con cómo LangGraph maneja los writes cuando se limpia el flow_stack
- Verificar si hay algún problema con el checkpointing cuando se cancela un flow
