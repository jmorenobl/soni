## Task: 340 - Fix Digression Conversation State

**ID de tarea:** 340
**Hito:** Bug Fixes - High Priority
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Corregir el `conversation_state` después de manejar una digresión. El test `test_digression_flow_with_mocked_nlu` falla porque el estado es `idle` en lugar de `waiting_for_slot`.

### Contexto

**Problema identificado:**
- Después de manejar una digresión (pregunta del usuario), el sistema debería mantener `conversation_state="waiting_for_slot"`
- El test usa NLU mockeado, por lo que NO es un problema del NLU
- El problema está en la lógica de `handle_digression` o `generate_response`

**Referencias:**
- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 2.2
- `tests/integration/test_dialogue_manager_with_mocked_nlu.py::test_digression_flow_with_mocked_nlu`
- `src/soni/dm/nodes/handle_digression.py`
- `src/soni/dm/nodes/generate_response.py`

### Entregables

- [ ] El test `test_digression_flow_with_mocked_nlu` pasa sin errores
- [ ] `handle_digression` preserva correctamente `conversation_state="waiting_for_slot"`
- [ ] `generate_response` no cambia incorrectamente el estado a `idle` después de digresión
- [ ] El `waiting_for_slot` se preserva correctamente después de digresión

### Implementación Detallada

#### Paso 1: Investigar el problema

**Archivo(s) a revisar:**
- `src/soni/dm/nodes/handle_digression.py`
- `src/soni/dm/nodes/generate_response.py`
- `src/soni/dm/routing.py` - routing después de digresión

**Acciones:**
1. Ejecutar el test fallido con debug
2. Verificar qué retorna `handle_digression_node`
3. Verificar qué hace `generate_response` con el estado
4. Identificar dónde se pierde el `conversation_state="waiting_for_slot"`

**Comando de debug:**
```bash
uv run pytest tests/integration/test_dialogue_manager_with_mocked_nlu.py::test_digression_flow_with_mocked_nlu -v --tb=long -s
```

#### Paso 2: Corregir handle_digression

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_digression.py`

**Verificaciones:**
- El nodo debe preservar `conversation_state="waiting_for_slot"` cuando hay un `waiting_for_slot`
- Debe preservar `current_step` si existe
- No debe cambiar el estado a `idle` o `generating_response` cuando hay un slot esperando

**Código esperado:**
```python
# handle_digression debe retornar cuando hay waiting_for_slot:
{
    "last_response": f"{response}\n\n{prompt}",  # Respuesta + re-prompt
    "conversation_state": "waiting_for_slot",  # CRÍTICO: preservar
    "waiting_for_slot": waiting_for_slot,  # Preservar
    "current_step": current_step,  # Preservar si existe
    # ...
}
```

#### Paso 3: Corregir generate_response

**Archivo(s) a modificar:** `src/soni/dm/nodes/generate_response.py`

**Verificaciones:**
- `generate_response` NO debe cambiar `conversation_state` a `idle` cuando hay `waiting_for_slot`
- Debe preservar el estado que viene del nodo anterior
- Solo debe cambiar a `idle` cuando realmente no hay nada esperando

**Código esperado:**
```python
# generate_response debe preservar waiting_for_slot:
if current_conv_state == "waiting_for_slot" and waiting_for_slot:
    conversation_state = "waiting_for_slot"  # Preservar, NO cambiar a idle
```

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_dialogue_manager_with_mocked_nlu.py`

**Test existente que debe pasar:**
```python
async def test_digression_flow_with_mocked_nlu(...):
    # Este test ya existe y debe pasar después de la corrección
    # Verifica que conversation_state es 'waiting_for_slot' después de digresión
```

**Tests adicionales a considerar:**
```python
# Test: Digresión sin waiting_for_slot
async def test_digression_without_waiting_slot(...):
    """Test que digresión sin waiting_for_slot usa conversation_state apropiado."""

# Test: Múltiples digresiones consecutivas
async def test_multiple_digressions_preserve_state(...):
    """Test que múltiples digresiones preservan el waiting_for_slot."""
```

### Criterios de Éxito

- [ ] `test_digression_flow_with_mocked_nlu` pasa sin errores
- [ ] `conversation_state` es `waiting_for_slot` después de digresión cuando hay slot esperando
- [ ] `waiting_for_slot` se preserva correctamente
- [ ] `current_step` se preserva correctamente
- [ ] Todos los tests de integración relacionados pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**
```bash
# Ejecutar test específico
uv run pytest tests/integration/test_dialogue_manager_with_mocked_nlu.py::test_digression_flow_with_mocked_nlu -v

# Ejecutar todos los tests de digresión
uv run pytest tests/integration/ -k digression -v

# Ejecutar suite completa de integración
uv run pytest tests/integration/ -v
```

**Resultado esperado:**
- El estado después de digresión preserva `waiting_for_slot` y `conversation_state="waiting_for_slot"`

### Referencias

- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 2.2
- `docs/design/04-state-machine.md` - State machine design
- `docs/design/05-message-flow.md` - Message flow design (digression handling)
- `src/soni/dm/nodes/handle_digression.py` - Implementación actual
- `src/soni/dm/nodes/generate_response.py` - Implementación actual

### Notas Adicionales

- Este es un problema de lógica, NO del NLU (el test usa NLU mockeado)
- El problema podría estar en cómo `generate_response` determina el `conversation_state`
- Verificar que no hay conflictos entre el estado que retorna `handle_digression` y el que establece `generate_response`
