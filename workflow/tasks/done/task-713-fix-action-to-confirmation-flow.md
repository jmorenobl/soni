## Task: 713 - Fix Action to Confirmation Flow Advancement

**ID de tarea:** 713
**Hito:** Fix Integration Test Failures - Logic Fixes
**Dependencias:** Ninguna
**Duración estimada:** 3-4 horas

### Objetivo

Corregir la lógica de avance de pasos para que después de ejecutar una acción, el sistema avance correctamente al paso de confirmación en lugar de quedarse en `collect_origin`.

### Contexto

**Problema identificado:**
- El test `test_action_to_confirmation_flow` falla: `assert 'collect_origin' == 'ask_confirmation'`
- Después de ejecutar la acción `search_flights`, el sistema debería avanzar a `ask_confirmation`
- En lugar de eso, el sistema se queda en `collect_origin` o no avanza correctamente
- Este es un problema de lógica, no del NLU

**Referencias:**
- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 2.1
- `tests/integration/test_confirmation_flow.py::test_action_to_confirmation_flow`
- `src/soni/flow/step_manager.py` - Gestión de pasos
- `src/soni/dm/nodes/execute_action.py` - Ejecución de acciones
- `src/soni/dm/builder.py` - Construcción del grafo

### Entregables

- [ ] El test `test_action_to_confirmation_flow` pasa sin errores
- [ ] Después de ejecutar una acción, el sistema avanza al siguiente paso (confirmación si existe)
- [ ] El `current_step` se actualiza correctamente después de la acción
- [ ] El `conversation_state` se actualiza a `ready_for_confirmation` o `confirming`

### Implementación Detallada

#### Paso 1: Investigar el problema

**Archivo(s) a revisar:**
- `src/soni/dm/nodes/execute_action.py`
- `src/soni/flow/step_manager.py`
- `src/soni/dm/builder.py` - Routing después de execute_action

**Acciones:**
1. Ejecutar el test fallido con debug
2. Verificar qué paso está activo después de ejecutar la acción
3. Verificar si `advance_through_completed_steps` se llama correctamente
4. Verificar el routing después de `execute_action`

**Comando de debug:**
```bash
uv run pytest tests/integration/test_confirmation_flow.py::test_action_to_confirmation_flow -v --tb=long -s
```

#### Paso 2: Verificar step_manager.advance_through_completed_steps

**Archivo(s) a revisar:** `src/soni/flow/step_manager.py`

**Verificaciones:**
- ¿`advance_through_completed_steps` se llama después de `execute_action`?
- ¿Avanza correctamente al siguiente paso (confirmación)?
- ¿Actualiza `current_step` correctamente?

**Código esperado:**

```python
# En execute_action.py, después de ejecutar la acción:
# Debe llamar a step_manager.advance_through_completed_steps()
# Y actualizar current_step y conversation_state
```

#### Paso 3: Corregir avance de pasos después de acción

**Archivo(s) a modificar:** `src/soni/dm/nodes/execute_action.py`

**Código esperado:**

```python
async def execute_action_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
    # ... ejecutar acción ...

    # Después de ejecutar acción exitosamente:
    step_manager = runtime.context["step_manager"]
    flow_manager = runtime.context["flow_manager"]

    active_ctx = flow_manager.get_active_context(state)
    if active_ctx:
        # Avanzar al siguiente paso
        next_step = step_manager.advance_through_completed_steps(
            state, active_ctx["flow_id"]
        )

        # Actualizar current_step
        active_ctx["current_step"] = next_step

        # Si el siguiente paso es confirmación, actualizar conversation_state
        if next_step and next_step.get("type") == "confirm":
            return {
                "conversation_state": "ready_for_confirmation",
                "current_step": next_step,
                # ... otros campos ...
            }

    return {...}
```

**Explicación:**
- Después de ejecutar la acción, debe avanzar al siguiente paso
- Si el siguiente paso es confirmación, actualizar `conversation_state`
- Actualizar `current_step` en el contexto activo

#### Paso 4: Verificar routing después de execute_action

**Archivo(s) a revisar:** `src/soni/dm/builder.py`

**Verificaciones:**
- ¿El routing después de `execute_action` va al siguiente paso?
- ¿O va directamente a `generate_response`?

**Código esperado:**

```python
# En builder.py, routing después de execute_action:
# Si hay siguiente paso (confirmación), ir a ese paso
# Si no hay siguiente paso, ir a generate_response
```

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_confirmation_flow.py`

**Test existente que debe pasar:**
```python
async def test_action_to_confirmation_flow(...):
    # Este test ya existe y debe pasar después de la corrección
    # Verifica que después de acción, current_step == "ask_confirmation"
```

**Tests adicionales a considerar:**
```python
# Test: Acción sin paso de confirmación
async def test_action_without_confirmation_step(...):
    """Test que acción avanza correctamente cuando no hay confirmación."""

# Test: Acción como último paso
async def test_action_as_last_step(...):
    """Test que acción como último paso termina el flow correctamente."""
```

### Criterios de Éxito

- [ ] `test_action_to_confirmation_flow` pasa sin errores
- [ ] Después de ejecutar acción, `current_step` se actualiza al siguiente paso
- [ ] Si el siguiente paso es confirmación, `conversation_state` es `ready_for_confirmation`
- [ ] El routing después de `execute_action` funciona correctamente
- [ ] Todos los tests de integración relacionados pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar test específico
uv run pytest tests/integration/test_confirmation_flow.py::test_action_to_confirmation_flow -v

# Ejecutar todos los tests de confirmación
uv run pytest tests/integration/test_confirmation_flow.py -v

# Ejecutar suite completa de integración
uv run pytest tests/integration/ -v
```

**Resultado esperado:**
- Después de ejecutar la acción, el sistema avanza a `ask_confirmation`
- El `current_step` es `ask_confirmation`
- El `conversation_state` es `ready_for_confirmation` o `confirming`

### Referencias

- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 2.1
- `tests/integration/test_confirmation_flow.py::test_action_to_confirmation_flow` - Test que debe pasar
- `src/soni/dm/nodes/execute_action.py` - Implementación actual
- `src/soni/flow/step_manager.py` - Gestión de pasos
- `src/soni/dm/builder.py` - Construcción del grafo

### Notas Adicionales

- Esta tarea es parte de la Fase 2 del plan de acción (corrección de lógica)
- No es un problema del NLU, es un problema de lógica de avance de pasos
- Verificar que `advance_through_completed_steps` funciona correctamente
- Verificar que el routing después de `execute_action` va al siguiente paso, no directamente a `generate_response`
