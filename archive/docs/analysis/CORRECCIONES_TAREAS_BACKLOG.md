# Correcciones a Tareas de Backlog - Tests Unitarios

**Fecha**: 2025-12-10
**Basado en**: `REVISION_TAREAS_BACKLOG_TESTS.md`
**Objetivo**: Documentar correcciones específicas a aplicar a tareas existentes

---

## 1. Correcciones Críticas por Tarea

### 1.1 Task-309: handle_correction.py

**Archivo**: `workflow/tasks/backlog/task-309-tests-handle-correction.md`

#### Corrección 1.1.1: Manejo de errores (return vs raise)

**Ubicación**: Paso 3 - Tests de edge cases

**Problema**: Los tests usan `with pytest.raises()` pero `handle_correction.py` retorna `{"conversation_state": "error"}` en lugar de lanzar excepciones.

**Corrección a aplicar**:

```python
# ❌ INCORRECTO (actual)
@pytest.mark.asyncio
async def test_handle_correction_no_nlu_result(...):
    # ...
    with pytest.raises((ValueError, KeyError)):
        await handle_correction_node(state, mock_runtime)

# ✅ CORRECTO
@pytest.mark.asyncio
async def test_handle_correction_no_nlu_result(...):
    # Arrange
    state = create_state_with_slots("book_flight", slots={"origin": "Madrid"})
    state["nlu_result"] = None

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "error"
```

**Aplica a todos estos tests**:
- `test_handle_correction_no_nlu_result`
- `test_handle_correction_no_slots`
- `test_handle_correction_no_active_flow`
- `test_handle_correction_unknown_format`
- `test_handle_correction_normalization_failure`

**Notas adicionales**:
- Para `test_handle_correction_no_slots`: Puede retornar `"waiting_for_slot"` si hay active flow
- Para `test_handle_correction_no_active_flow`: Mockear `get_active_context()` para retornar `None`
- Para `test_handle_correction_normalization_failure`: Mockear `get_active_context()` también

#### Corrección 1.1.2: Test adicional para variable faltante en template

**Ubicación**: Paso 6 - Tests de _get_response_template

**Agregar test**:

```python
def test_get_response_template_missing_variable():
    """Test que _get_response_template maneja variables faltantes en kwargs."""
    # Arrange
    config = MagicMock()
    config.responses = {
        "correction_acknowledged": "Updated {slot_name} to {new_value}"
    }

    # Act - Solo pasar slot_name, falta new_value
    result = _get_response_template(
        config,
        "correction_acknowledged",
        "Default message",
        slot_name="destination"
    )

    # Assert
    # La implementación actual deja placeholders sin reemplazar
    assert "destination" in result or result == "Default message"
```

---

### 1.2 Task-310: handle_modification.py

**Archivo**: `workflow/tasks/backlog/task-310-tests-handle-modification.md`

#### Corrección 1.2.1: Nota sobre MetadataManager

**Ubicación**: Sección "Implementación Detallada" - Antes del Paso 1

**Agregar nota**:

```markdown
### Nota Importante sobre MetadataManager

Este módulo usa `MetadataManager.set_modification_flags()` en lugar de `set_correction_flags()`.

**Verificar en todos los tests**:
- Metadata debe contener `_modification_slot` y `_modification_value`
- Metadata NO debe contener `_correction_slot` ni `_correction_value`
- Los tests deben verificar explícitamente que correction flags se limpian
```

#### Corrección 1.2.2: Test adicional de diferencia correction vs modification

**Ubicación**: Nueva sección después de "Tests de metadata y response"

**Agregar**:

```markdown
#### Tests de Diferencia con Correction

**Test crítico para documentar diferencia**:

```python
@pytest.mark.asyncio
async def test_handle_modification_vs_correction_metadata():
    """
    Test que verifica diferencia entre modification y correction.

    Este test documenta explícitamente la diferencia entre ambos nodos.
    """
    # Arrange - Estado con flags de correction previos
    state = create_state_with_slots(
        "book_flight",
        slots={"destination": "Madrid"},
        metadata={"_correction_slot": "origin", "_correction_value": "Barcelona"}
    )
    state["nlu_result"] = mock_nlu_modification.predict.return_value.model_dump()
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Valencia"

    # Act
    result = await handle_modification_node(state, mock_runtime)

    # Assert - Verifica que modification reemplaza correction
    assert result["metadata"]["_modification_slot"] == "destination"
    assert result["metadata"]["_modification_value"] == "Valencia"
    assert "_correction_slot" not in result["metadata"]  # CRÍTICO
    assert "_correction_value" not in result["metadata"]  # CRÍTICO
```
```

---

### 1.3 Task-311: routing.py

**Archivo**: `workflow/tasks/backlog/task-311-tests-routing.md`

#### Corrección 1.3.1: Mencionar tests fallando existentes

**Ubicación**: Después de "Contexto", antes de "Entregables"

**Agregar sección**:

```markdown
### ⚠️ IMPORTANTE: Tests Existentes Fallando

Antes de agregar nuevos tests, **ARREGLAR** los siguientes 4 tests que están fallando:

```bash
# Tests que actualmente fallan
FAILED tests/unit/test_routing.py::test_route_after_validate_warns_unexpected_state
FAILED tests/unit/test_routing.py::test_route_after_understand_logs_message_type
FAILED tests/unit/test_routing.py::test_route_after_understand_warns_unknown_message_type
FAILED tests/unit/test_routing.py::test_route_after_validate_logs_conversation_state
```

**Razón**: Estos tests usan logging y `caplog` pero pueden estar mal configurados.

**Acción requerida**:
1. Revisar y arreglar estos 4 tests PRIMERO
2. Luego proceder con tests nuevos
3. Documentar el fix en commit message

**Referencia**: `docs/analysis/REVISION_TAREAS_BACKLOG_TESTS.md` - Sección 1, item 2
```

#### Corrección 1.3.2: Agregar tests parametrizados

**Ubicación**: Nueva sección después de "route_after_understand"

**Agregar**:

```markdown
#### Tests Parametrizados (Reducir Duplicación)

**En lugar de crear un test por cada MessageType, usar parametrización**:

```python
@pytest.mark.parametrize("message_type,expected_node", [
    ("slot_value", "validate_slot"),
    ("correction", "handle_correction"),
    ("modification", "handle_modification"),
    ("confirmation", "handle_confirmation"),
    ("intent_change", "handle_intent_change"),
    ("question", "handle_digression"),
    ("help", "handle_digression"),
])
def test_route_after_understand_message_types(
    create_state_with_flow,
    message_type,
    expected_node
):
    """Test routing para todos los message types."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["nlu_result"] = {
        "message_type": message_type,
        "command": "continue",
        "slots": []
    }

    # Act
    result = route_after_understand(state)

    # Assert
    assert result == expected_node
```

**Beneficio**: Reduce de ~8 tests individuales a 1 test parametrizado.
```

#### Corrección 1.3.3: Agregar ejemplo de test de logging

**Ubicación**: Después de tests parametrizados

**Agregar**:

```markdown
#### Tests de Logging con caplog

**Ejemplo para tests que verifican logging**:

```python
import logging

def test_route_after_understand_logs_message_type(caplog, create_state_with_flow):
    """Test que routing logea message_type correctamente."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["nlu_result"] = {
        "message_type": "slot_value",
        "command": "continue",
        "slots": []
    }

    # Act
    with caplog.at_level(logging.INFO):
        route_after_understand(state)

    # Assert
    assert "message_type=slot_value" in caplog.text
```

**Nota**: Usar `caplog.at_level(logging.INFO)` para capturar logs de nivel INFO.
```

---

### 1.4 Task-312: handle_confirmation.py

**Archivo**: `workflow/tasks/backlog/task-312-tests-handle-confirmation.md`

#### Corrección 1.4.1: Mencionar tests existentes

**Ubicación**: Después de "Contexto", antes de "Entregables"

**Agregar sección**:

```markdown
### Tests Existentes a Revisar

Ya existen algunos tests en `tests/unit/test_handle_confirmation_node.py`:

- ✅ `test_handle_confirmation_confirmed` - Revisar y completar
- ✅ `test_handle_confirmation_denied` - Revisar y completar
- ✅ `test_handle_confirmation_unclear_first_attempt` - Revisar y completar
- ✅ `test_handle_confirmation_max_retries_exceeded` - Revisar y completar

**Acción requerida**:
1. Revisar tests existentes antes de crear nuevos
2. Completar tests existentes si faltan assertions
3. Agregar solo tests faltantes según checklist
4. No duplicar tests que ya existen

**Cobertura actual**: 40% - Verificar qué tests faltan usando:
```bash
uv run pytest tests/unit/test_handle_confirmation_node.py \
    --cov=src/soni/dm/nodes/handle_confirmation \
    --cov-report=term-missing
```
```

#### Corrección 1.4.2: Test adicional de contador inválido

**Ubicación**: Después de "Tests de max retries"

**Agregar**:

```markdown
- [ ] **Edge cases adicionales**
  - [ ] test_handle_confirmation_invalid_attempts_counter

**Implementación**:

```python
@pytest.mark.asyncio
async def test_handle_confirmation_invalid_attempts_counter(
    create_state_with_slots,
    mock_nlu_confirmation_unclear,
    mock_runtime
):
    """Test manejo robusto de contador de intentos inválido."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid"},
        metadata={"_confirmation_attempts": -1}  # Valor inválido
    )
    state["nlu_result"] = mock_nlu_confirmation_unclear.predict.return_value.model_dump()

    # Act
    result = await handle_confirmation_node(state, mock_runtime)

    # Assert - Debe manejar gracefully o resetear a 0
    assert result["metadata"]["_confirmation_attempts"] >= 0
```
```

---

### 1.5 Task-313: validate_slot.py

**Archivo**: `workflow/tasks/backlog/task-313-tests-validate-slot.md`

#### Corrección 1.5.1: Actualizar estimación

**Ubicación**: Header del documento

**Cambio**:

```markdown
# Antes
**Duración estimada:** 1-2 días

# Después
**Duración estimada:** 2-3 días
```

**Razón**: 30-40 tests requieren más tiempo que 1-2 días.

#### Corrección 1.5.2: Agregar fixtures de validators

**Ubicación**: Nueva sección "Paso 1" antes de tests

**Agregar**:

```markdown
#### Paso 1: Agregar Fixtures de Validators (si no están en conftest.py)

**Agregar a conftest.py o al archivo de test**:

```python
@pytest.fixture
def mock_validator_success():
    """Mock validator que siempre retorna valid=True."""
    validator = AsyncMock()
    validator.validate.return_value = {
        "valid": True,
        "normalized_value": "Madrid"
    }
    return validator


@pytest.fixture
def mock_validator_failure():
    """Mock validator que retorna valid=False."""
    validator = AsyncMock()
    validator.validate.return_value = {
        "valid": False,
        "error": "Invalid value",
        "normalized_value": None
    }
    return validator


@pytest.fixture
def mock_validator_exception():
    """Mock validator que lanza excepción."""
    validator = AsyncMock()
    validator.validate.side_effect = ValueError("Validation error")
    return validator
```

**Uso en tests**:

```python
@pytest.mark.asyncio
async def test_validate_slot_success(
    create_state_with_slots,
    mock_validator_success,
    mock_runtime
):
    """Test validación exitosa de slot."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"origin": "Madrid"})

    # Mock validator registry para retornar validator mockeado
    mock_runtime.context["validator_registry"] = MagicMock()
    mock_runtime.context["validator_registry"].get_validator.return_value = mock_validator_success

    # Act
    result = await validate_slot_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "waiting_for_slot"  # O el estado correcto
```
```

---

### 1.6 Task-314: optimizers.py

**Archivo**: `workflow/tasks/backlog/task-314-tests-optimizers.md`

#### Corrección 1.6.1: Agregar ejemplo de mock DSPy

**Ubicación**: Nueva sección después de "Contexto"

**Agregar**:

```markdown
### ⚠️ CRÍTICO: Mockear DSPy y LLM

Este módulo requiere mockear DSPy completamente para tests unitarios deterministas.

**Ejemplo de fixture para DSPy**:

```python
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_dspy_lm():
    """Mock DSPy language model for deterministic tests."""
    lm = MagicMock()
    lm.predict = MagicMock(return_value={
        "optimized_prompt": "mocked optimized prompt",
        "score": 0.95
    })
    return lm


@pytest.mark.asyncio
async def test_optimize_soni_du_with_mock_lm(mock_dspy_lm):
    """Test que optimize_soni_du funciona con LM mockeado."""
    # Arrange
    from soni.du.optimizers import optimize_soni_du

    # Patch DSPy
    with patch('soni.du.optimizers.dspy.OpenAI', return_value=mock_dspy_lm):
        # Act
        result = await optimize_soni_du(
            examples=[],  # Mock examples
            metric=lambda x, y: 1.0  # Mock metric
        )

        # Assert
        assert result is not None
```
```

#### Corrección 1.6.2: Considerar alcance

**Ubicación**: Después del ejemplo de mock

**Agregar nota**:

```markdown
### Consideración: ¿Test Unitario o Integración?

**Pregunta a resolver**: ¿Debe `optimizers.py` tener tests unitarios o solo tests de integración?

**Argumentos para tests de integración**:
- Optimización depende fuertemente de LLM real
- Mockear DSPy completamente puede no ser representativo
- La mayoría del valor está en la integración con LLM real

**Argumentos para tests unitarios**:
- Funciones helper pueden testearse sin LLM
- Lógica de evaluación de métricas puede testearse
- Carga/guardado de módulos optimizados puede testearse

**Recomendación**:
1. Tests unitarios para funciones helper (load_optimized_module, etc.)
2. Tests de integración para optimización completa
3. Reducir scope de tests unitarios a ~7-10 tests solo para funciones helper

**Decisión pendiente**: Consultar con equipo si optimizers debe estar en scope de tests unitarios.
```

---

## 2. Tareas Nuevas Creadas

### 2.1 Task-324: Tests collect_next_slot.py

**Archivo creado**: `workflow/tasks/backlog/task-324-tests-collect-next-slot.md`

**Detalles**:
- Módulo identificado como faltante en análisis
- ~8-10 tests estimados
- Prioridad ALTA
- Tests cubren: colección de siguiente slot, interrupciones, re-ejecuciones, edge cases

### 2.2 Task-325: Tests confirm_action.py

**Archivo creado**: `workflow/tasks/backlog/task-325-tests-confirm-action.md`

**Detalles**:
- Módulo identificado como faltante en análisis
- ~12 tests estimados
- Prioridad ALTA
- Tests cubren: construcción de confirmación, interpolación de slots, primera ejecución vs re-ejecución, edge cases

---

## 3. Correcciones Menores Generales

### 3.1 Pre-implementación Checklist

**Agregar a TODAS las tareas** después de "Contexto", antes de "Entregables":

```markdown
### Pre-implementación Checklist

Antes de empezar, verificar:

- [ ] Revisar código fuente del módulo para entender comportamiento real
- [ ] Identificar tests existentes que puedan reutilizarse
- [ ] Verificar que fixtures necesarios están en conftest.py
- [ ] Leer documentación de diseño relevante
- [ ] Revisar cobertura actual con: `uv run pytest --cov=src/soni/PATH/MODULE --cov-report=term-missing`
```

### 3.2 Template de PR Description

**Agregar a TODAS las tareas** en "Notas Adicionales":

```markdown
### Template de Pull Request

Al crear PR para esta tarea, usar el siguiente template:

```markdown
## Tests Unitarios: [Nombre del Módulo]

**Tarea**: task-XXX
**Módulo**: `src/soni/[path]/[module].py`
**Cobertura antes**: X%
**Cobertura después**: Y%
**Tests añadidos**: Z tests

### Cambios

- Implementados X tests para [funcionalidad]
- Tests cubren todos los edge cases identificados
- Todos los tests son deterministas con NLU mockeado

### Checklist

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para el módulo
- [ ] Tests son deterministas (ejecutados 5 veces, todos pasan)
- [ ] Tests son independientes (ejecutados en orden aleatorio)
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores
- [ ] Tests ejecutan en <1s cada uno

### Comandos de Validación

```bash
# Ejecutar tests
uv run pytest tests/unit/test_[module].py -v

# Verificar cobertura
uv run pytest tests/unit/test_[module].py --cov=src/soni/[path]/[module] --cov-report=term-missing

# Verificar determinismo (5 runs)
for i in {1..5}; do uv run pytest tests/unit/test_[module].py -q || exit 1; done

# Verificar independencia
uv run pytest tests/unit/test_[module].py --random-order
```
```
```

---

## 4. Resumen de Correcciones

| Tarea | Correcciones Críticas | Correcciones Menores | Nuevas Secciones |
|-------|----------------------|---------------------|------------------|
| task-308 | Agregar fixture flow config | - | 1 (Paso 5) |
| task-309 | Cambiar pytest.raises a assert error state | Test variable faltante | - |
| task-310 | Nota MetadataManager | Test diferencia correction vs modification | 1 (Tests diferencia) |
| task-311 | Mencionar tests fallando | Tests parametrizados, tests logging | 3 (Tests fallando, parametrizados, logging) |
| task-312 | Mencionar tests existentes | Test contador inválido | 1 (Tests existentes) |
| task-313 | Actualizar estimación 2-3 días | Fixtures validators | 1 (Paso 1 fixtures) |
| task-314 | Ejemplo mock DSPy | Nota sobre alcance unitario vs integración | 2 (Mock DSPy, Consideración) |
| task-324 | - | - | Nueva tarea |
| task-325 | - | - | Nueva tarea |

**Total de correcciones**: 7 críticas, 6 menores, 9 nuevas secciones, 2 tareas nuevas

---

## 5. Prioridad de Aplicación de Correcciones

### Fase 1: INMEDIATO (antes de empezar implementación)

1. ✅ **task-308**: Agregar Paso 5 con fixture flow config
2. ✅ **task-311**: Agregar sección de tests fallando
3. ✅ **task-312**: Agregar sección de tests existentes

### Fase 2: ANTES de implementar cada tarea

1. **task-309**: Cambiar todos los tests de edge cases (raise → assert error)
2. **task-310**: Agregar nota MetadataManager y test diferencia
3. **task-313**: Agregar Paso 1 con fixtures validators
4. **task-314**: Agregar ejemplo mock DSPy y nota consideración

### Fase 3: OPCIONAL (mejoras)

1. Agregar pre-implementación checklist a todas las tareas
2. Agregar template de PR a todas las tareas
3. **task-311**: Agregar tests parametrizados y logging (como ejemplos)

---

## 6. Próximos Pasos

### Para Aplicar Correcciones

**Opción A - Manual** (recomendado para cambios críticos):
1. Abrir cada tarea en editor
2. Aplicar correcciones según sección correspondiente
3. Verificar que no rompe formato markdown

**Opción B - Script** (para correcciones repetitivas):
1. Crear script que agregue pre-implementación checklist a todas
2. Crear script que agregue template PR a todas
3. Ejecutar scripts

**Opción C - Híbrida** (recomendada):
1. Correcciones críticas (Fase 1 y 2): Manual
2. Correcciones opcionales (Fase 3): Script o dejar para después

### Para Validar Correcciones

Después de aplicar correcciones, verificar:

```bash
# Verificar que todos los archivos .md son válidos
for file in workflow/tasks/backlog/task-3*.md; do
    echo "Checking $file..."
    # Verificar que no hay errores de sintaxis markdown
    # (usar linter de markdown si disponible)
done

# Verificar que las tareas están completas
ls -la workflow/tasks/backlog/task-3*.md | wc -l
# Debe mostrar 18 tareas (308-325)
```

---

**Documento generado**: 2025-12-10
**Basado en revisión**: `REVISION_TAREAS_BACKLOG_TESTS.md`
**Estado**: Listo para aplicar correcciones
