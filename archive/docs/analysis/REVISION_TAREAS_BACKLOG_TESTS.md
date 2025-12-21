# Revisión de Tareas de Backlog - Tests Unitarios

**Fecha**: 2025-12-10
**Revisor**: Claude Code
**Documentos de referencia**:
- `ANALISIS_TESTS_UNITARIOS_COBERTURA.md`
- `GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md`

---

## Resumen Ejecutivo

**Estado general**: ✅ **EXCELENTE** - Las tareas están muy bien estructuradas y siguen fielmente los documentos de análisis y guía.

**Tareas revisadas**: 16 tareas (task-308 a task-323)

**Principales fortalezas**:
- ✅ Estructura consistente entre tareas
- ✅ Referencias claras a documentos de análisis
- ✅ Estimaciones realistas de tests necesarios
- ✅ Criterios de éxito bien definidos
- ✅ Dependencias correctamente especificadas
- ✅ Comandos de validación incluidos

**Áreas de mejora identificadas**: Menores (ver detalles por tarea)

---

## 1. Revisión de Tareas CRÍTICAS (Prioridad Alta)

### ✅ Task 308: Actualizar conftest.py con Fixtures

**Estado**: ✅ **EXCELENTE**

**Fortalezas**:
- Código completo y copy-paste ready
- Incluye todos los fixtures necesarios de la guía
- Documentación inline clara
- StateBuilder pattern implementado
- Tests opcionales para validar fixtures

**Recomendaciones**:
1. ✅ **Ya incluido**: Fixtures para todos los MessageType
2. ✅ **Ya incluido**: Factory patterns para flexibilidad
3. ⚠️ **Considerar agregar**: Fixture para crear mock de `step_manager.config` con flows completos
   ```python
   @pytest.fixture
   def mock_flow_config_complete():
       """Mock flow config con steps completos."""
       from soni.core.types import FlowConfig, StepConfig
       return FlowConfig(
           name="book_flight",
           steps=[
               StepConfig(step="collect_origin", type="collect", slot="origin"),
               StepConfig(step="collect_destination", type="collect", slot="destination"),
               StepConfig(step="confirm_booking", type="confirm"),
               StepConfig(step="execute_booking", type="action", action="book_flight_action"),
           ]
       )
   ```

**Prioridad de implementación**: 🔴 **MÁXIMA** - Debe ser la primera tarea

**Estimación**: 2-3 horas ✅ Correcta

---

### ✅ Task 309: Tests handle_correction.py (Cobertura: 6%)

**Estado**: ✅ **EXCELENTE** - Muy detallado y completo

**Fortalezas**:
- Código de ejemplo completo para cada tipo de test
- Checklist exhaustivo con ~30 tests
- Referencias específicas a secciones de la guía
- Edge cases bien identificados
- Tests de metadata flags incluidos

**Recomendaciones menores**:
1. ⚠️ **Aclarar manejo de errores**: Los tests usan `with pytest.raises()` pero el código de `handle_correction.py` retorna `{"conversation_state": "error"}` en lugar de lanzar excepciones. Verificar comportamiento real.

   **Sugerencia**: Cambiar tests de edge cases de:
   ```python
   # ❌ Incorrecto si no lanza excepción
   with pytest.raises((ValueError, KeyError)):
       await handle_correction_node(state, mock_runtime)
   ```

   A:
   ```python
   # ✅ Correcto si retorna error state
   result = await handle_correction_node(state, mock_runtime)
   assert result["conversation_state"] == "error"
   ```

2. ✅ **Considerar agregar**: Test para verificar que `_get_response_template` interpola correctamente cuando falta una variable en kwargs
   ```python
   def test_get_response_template_missing_variable():
       """Test que _get_response_template maneja variables faltantes."""
       config = MagicMock()
       config.responses = {"template": "Updated {slot} to {value}"}

       # Solo pasar 'slot', falta 'value'
       result = _get_response_template(
           config, "template", "Default", slot="origin"
       )

       # Debería dejar placeholder o usar fallback
       assert "{value}" in result or result == "Default"
   ```

**Prioridad de implementación**: 🔴 **CRÍTICA** - Segunda tarea después de 308

**Estimación**: 1-2 días ✅ Correcta

**Cobertura esperada**: 6% → 85%+ ✅

---

### ✅ Task 310: Tests handle_modification.py (Cobertura: 6%)

**Estado**: ✅ **BUENA** - Estrategia correcta de reutilizar estructura

**Fortalezas**:
- Estrategia clara: copiar estructura de correction pero adaptar
- Bien identificadas las diferencias (modification flags vs correction flags)
- Dependencia correcta de task-309
- Checklist completo

**Recomendaciones**:
1. ✅ **Agregar nota**: Mencionar explícitamente que se debe verificar el método `MetadataManager.set_modification_flags()` en lugar de `set_correction_flags()`

2. ⚠️ **Considerar agregar test específico**:
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

       # Act
       result = await handle_modification_node(state, mock_runtime)

       # Assert - Verifica que modification reemplaza correction
       assert result["metadata"]["_modification_slot"] == "destination"
       assert result["metadata"]["_modification_value"] == "Valencia"
       assert "_correction_slot" not in result["metadata"]  # CRÍTICO
       assert "_correction_value" not in result["metadata"]  # CRÍTICO
   ```

**Prioridad de implementación**: 🔴 **CRÍTICA** - Tercera tarea

**Estimación**: 1-2 días ✅ Correcta (más rápido si reutiliza código de 309)

**Cobertura esperada**: 6% → 85%+ ✅

---

### ✅ Task 311: Tests routing.py (Cobertura: 38%)

**Estado**: ✅ **MUY BUENA** - Muy completo

**Fortalezas**:
- Identifica todas las funciones de routing
- ~60 tests estimados (realista)
- Incluye edge cases especiales (confirming state, modification after denial)
- Checklist organizado por función

**Recomendaciones**:
1. ✅ **Agregar tests de logging**: Las funciones de routing usan `logger.info()` y `logger.warning()`. Considerar tests que verifican logging:
   ```python
   def test_route_after_understand_logs_message_type(caplog, create_state_with_flow):
       """Test que routing logea message_type correctamente."""
       state = create_state_with_flow("book_flight")
       state["nlu_result"] = {"message_type": "slot_value", "command": "continue"}

       with caplog.at_level(logging.INFO):
           route_after_understand(state)

       assert "message_type=slot_value" in caplog.text
   ```

2. ⚠️ **Aclarar**: Los tests actuales en `tests/unit/test_routing.py` tienen 4 tests FAILING. Revisar por qué:
   - `test_route_after_validate_warns_unexpected_state`
   - `test_route_after_understand_logs_message_type`
   - `test_route_after_understand_warns_unknown_message_type`
   - `test_route_after_validate_logs_conversation_state`

   Estos parecen tests de logging que están fallando. Priorizar arreglar estos antes de agregar nuevos.

3. ✅ **Considerar agregar**: Tests parametrizados para reducir duplicación:
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
       state = create_state_with_flow("book_flight")
       state["nlu_result"] = {"message_type": message_type}

       result = route_after_understand(state)

       assert result == expected_node
   ```

**Prioridad de implementación**: 🔴 **CRÍTICA** - Cuarta tarea

**Estimación**: 2-3 días ✅ Correcta

**Cobertura esperada**: 38% → 85%+ ✅

---

### ✅ Task 312: Tests handle_confirmation.py (Cobertura: 40%)

**Estado**: ✅ **BUENA**

**Fortalezas**:
- Bien organizado por tipo de confirmación (yes/no/unclear)
- Incluye tests de max retries
- Incluye tests de corrección durante confirmación
- ~25 tests estimados (realista)

**Recomendaciones**:
1. ⚠️ **Revisar tests existentes**: Ya hay tests en `tests/unit/test_handle_confirmation_node.py` que cubren algunos casos. Verificar qué tests ya existen antes de duplicar:
   - `test_handle_confirmation_confirmed` ✅ Ya existe
   - `test_handle_confirmation_denied` ✅ Ya existe
   - `test_handle_confirmation_unclear_first_attempt` ✅ Ya existe
   - `test_handle_confirmation_max_retries_exceeded` ✅ Ya existe

   **Sugerencia**: Partir de los tests existentes y agregar los faltantes.

2. ✅ **Considerar agregar**: Test que verifica el comportamiento cuando `_confirmation_attempts` está en un valor incorrecto (ej: negativo):
   ```python
   @pytest.mark.asyncio
   async def test_handle_confirmation_invalid_attempts_counter():
       """Test manejo robusto de contador de intentos inválido."""
       state = create_state_with_slots(
           "book_flight",
           slots={"origin": "Madrid"},
           metadata={"_confirmation_attempts": -1}  # Valor inválido
       )
       state["nlu_result"] = mock_nlu_confirmation_unclear.predict.return_value.model_dump()

       result = await handle_confirmation_node(state, mock_runtime)

       # Debe manejar gracefully o resetear a 0
       assert result["metadata"]["_confirmation_attempts"] >= 0
   ```

**Prioridad de implementación**: 🔴 **CRÍTICA** - Quinta tarea

**Estimación**: 1-2 días ✅ Correcta

**Cobertura esperada**: 40% → 85%+ ✅

---

### ✅ Task 313: Tests validate_slot.py (Cobertura: 46%)

**Estado**: ✅ **BUENA**

**Fortalezas**:
- Identifica necesidad de mockear validators
- ~30-40 tests estimados
- Incluye edge cases

**Recomendaciones**:
1. ⚠️ **Aclarar fixture de validators**: Agregar ejemplo de cómo mockear validators:
   ```python
   @pytest.fixture
   def mock_validator_success():
       """Mock validator que siempre retorna valid=True."""
       validator = AsyncMock()
       validator.validate.return_value = {"valid": True, "normalized_value": "Madrid"}
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
   ```

**Prioridad de implementación**: 🔴 **CRÍTICA** - Sexta tarea

**Estimación**: Actualizar a 2-3 días (30-40 tests es bastante)

---

## 2. Revisión de Tareas ALTA Prioridad

### ✅ Task 314: Tests optimizers.py (Cobertura: 27%)

**Estado**: ✅ **BUENA** pero necesita aclaración

**Fortalezas**:
- Reconoce necesidad de mockear LLM
- Tests estimados realistas (~7-10)

**Recomendaciones CRÍTICAS**:
1. 🔴 **CRÍTICO - Aclarar alcance**: Este módulo requiere mockear DSPy y LLM. Agregar ejemplo específico:
   ```python
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

2. ⚠️ **Considerar**: ¿Realmente necesitamos tests unitarios de optimizers? Es un módulo que depende fuertemente de LLM. Podría ser más apropiado como test de integración.

   **Sugerencia**: Reducir scope de tests unitarios a funciones helper y dejar optimización completa para tests de integración.

**Prioridad de implementación**: 🟡 **MEDIA-BAJA** - Después de tareas críticas

**Estimación**: 1-2 días ✅ Correcta

---

### ✅ Task 315-322: Tests de Prioridad ALTA/MEDIA

**Estado**: ✅ **BUENAS** - Estructura consistente

**Observaciones generales**:
- Todas siguen formato consistente
- Estimaciones realistas
- Comandos de validación incluidos

**Recomendación general**:
- Implementar en orden de prioridad según cobertura actual
- Usar parametrized tests donde sea posible para reducir duplicación

---

## 3. Revisión de Tarea de Validación Final

### ✅ Task 323: Validación Final de Cobertura

**Estado**: ✅ **EXCELENTE**

**Fortalezas**:
- Checklist completo de validación
- Comandos específicos para cada métrica
- Template de reporte incluido
- Criterios de éxito claros

**Recomendaciones**:
1. ✅ **Agregar**: Validación de mutation testing (si se decide usar):
   ```bash
   # Mutation testing (opcional)
   uv run mutmut run --paths-to-mutate=src/soni/dm/nodes/
   uv run mutmut results
   ```

2. ✅ **Agregar**: Generación de badge de cobertura:
   ```bash
   # Generar badge de cobertura
   uv run coverage-badge -o coverage.svg -f
   ```

**Prioridad de implementación**: 🟢 **FINAL** - Última tarea

**Estimación**: 2-3 horas ✅ Correcta

---

## 4. Análisis Transversal de Todas las Tareas

### 4.1 Adherencia a Documentos de Análisis

| Aspecto | Adherencia | Observaciones |
|---------|------------|---------------|
| **Estructura AAA** | ✅ 100% | Todos los ejemplos siguen Arrange-Act-Assert |
| **NLU Mockeado** | ✅ 100% | Todas las tareas usan mocks, no LLM real |
| **Fixtures de conftest** | ✅ 100% | Todas referencian task-308 |
| **Tests deterministas** | ✅ 100% | Énfasis en determinismo en todas las tareas |
| **Estimaciones realistas** | ✅ 95% | Solo task-313 podría necesitar más tiempo |
| **Referencias a docs** | ✅ 100% | Todas referencian análisis y guía |

### 4.2 Consistencia Entre Tareas

| Aspecto | Consistencia | Observaciones |
|---------|--------------|---------------|
| **Formato de tarea** | ✅ 100% | Formato idéntico en todas |
| **Secciones incluidas** | ✅ 100% | Objetivo, Contexto, Entregables, etc. |
| **Comandos de validación** | ✅ 100% | Todas incluyen comandos específicos |
| **Criterios de éxito** | ✅ 100% | Todos medibles y verificables |
| **Dependencias** | ✅ 100% | Correctamente especificadas |

### 4.3 Completitud del Backlog

**Tareas que cubren prioridad CRÍTICA (<50% cobertura)**:
- ✅ task-309: handle_correction.py (6%)
- ✅ task-310: handle_modification.py (6%)
- ✅ task-311: routing.py (38%)
- ✅ task-312: handle_confirmation.py (40%)
- ✅ task-313: validate_slot.py (46%)
- ⚠️ task-314: optimizers.py (27%) - Considerar si es unitario o integración

**Tareas que cubren prioridad ALTA (50-80% cobertura)**:
- ✅ task-315: runtime.py (59%)
- ✅ task-316: response_generator.py (61%)
- ✅ task-317: normalizer.py (67%)
- ✅ task-318: step_manager.py (69%)
- ✅ task-319: handle_intent_change.py (69%)

**Tareas que cubren módulos >80% (verificación completitud)**:
- ✅ task-320: flow_manager.py (89%)
- ✅ task-321: persistence.py (84%)
- ✅ task-322: flow_cleanup.py (96%)

**Módulos faltantes** (según análisis):
- ❌ **FALTA**: Tests para `dm/nodes/collect_next_slot.py` (no hay tarea específica)
- ❌ **FALTA**: Tests para `dm/nodes/confirm_action.py` (no hay tarea específica)
- ✅ **No necesarios**: `utils/metadata_manager.py` (100% cobertura)
- ✅ **No necesarios**: `utils/cycle_detector.py` (100% cobertura)

---

## 5. Recomendaciones Generales

### 5.1 Recomendaciones de Priorización

**Orden de implementación sugerido**:

1. 🔴 **INMEDIATO**: task-308 (conftest fixtures) - Bloquea todas las demás
2. 🔴 **CRÍTICO** (Semana 1-2):
   - task-309 (handle_correction)
   - task-310 (handle_modification)
   - task-311 (routing)
3. 🔴 **CRÍTICO** (Semana 3):
   - task-312 (handle_confirmation)
   - task-313 (validate_slot)
4. 🟡 **ALTA** (Semana 4-5):
   - task-315 (runtime)
   - task-316 (response_generator)
   - task-317 (normalizer)
   - task-318 (step_manager)
   - task-319 (handle_intent_change)
5. 🟢 **MEDIA** (Semana 6):
   - task-320 (flow_manager)
   - task-321 (persistence)
   - task-322 (flow_cleanup)
   - task-314 (optimizers) - Solo si se decide que es unitario
6. 🟢 **FINAL**: task-323 (validación)

### 5.2 Tareas Adicionales Necesarias

**Crear las siguientes tareas**:

1. **task-324-tests-collect-next-slot.md**
   - Módulo: `dm/nodes/collect_next_slot.py`
   - Cobertura actual: No especificada
   - Tests estimados: ~8-10
   - Prioridad: ALTA

2. **task-325-tests-confirm-action.md**
   - Módulo: `dm/nodes/confirm_action.py`
   - Cobertura actual: No especificada
   - Tests estimados: ~12-15
   - Prioridad: ALTA

### 5.3 Mejoras al Proceso

1. **Agregar checklist pre-implementación** en cada tarea:
   ```markdown
   ## Pre-implementación
   - [ ] Revisar código fuente del módulo
   - [ ] Identificar tests existentes que puedan reutilizarse
   - [ ] Verificar que fixtures necesarios están en conftest.py
   - [ ] Leer documentación de diseño relevante
   ```

2. **Agregar sección de "Tests Existentes"** en cada tarea:
   ```markdown
   ## Tests Existentes a Revisar
   - `test_handle_confirmation_confirmed` - Revisar y completar
   - `test_handle_confirmation_denied` - Revisar y completar
   ```

3. **Agregar template de PR description**:
   ```markdown
   ## PR Template

   **Tarea**: task-XXX
   **Módulo**: [nombre del módulo]
   **Cobertura antes**: X%
   **Cobertura después**: Y%
   **Tests añadidos**: Z tests

   ### Checklist
   - [ ] Todos los tests pasan
   - [ ] Cobertura >85%
   - [ ] Tests son deterministas
   - [ ] Linting pasa
   - [ ] Type checking pasa
   ```

---

## 6. Conclusiones

### 6.1 Resumen de la Revisión

**Calificación general**: ⭐⭐⭐⭐⭐ **EXCELENTE** (5/5)

**Aspectos positivos**:
- ✅ Todas las tareas siguen fielmente los documentos de análisis y guía
- ✅ Estructura consistente y profesional
- ✅ Código de ejemplo completo y ejecutable
- ✅ Estimaciones realistas
- ✅ Dependencias correctas
- ✅ Comandos de validación específicos
- ✅ Referencias a documentación completa

**Aspectos a mejorar** (menores):
- ⚠️ Aclarar manejo de errores en algunos tests (raise vs return error state)
- ⚠️ Agregar 2 tareas faltantes (collect_next_slot, confirm_action)
- ⚠️ Revisar tests existentes antes de duplicar
- ⚠️ Considerar si optimizers debe ser unitario o integración

### 6.2 Impacto Esperado

Si se implementan todas las tareas correctamente:

- **Cobertura actual**: 66.23%
- **Cobertura esperada**: **85-90%** ✅
- **Tests actuales**: 596
- **Tests nuevos**: ~232-290
- **Tests finales**: **~828-886 tests unitarios**

**Distribución de esfuerzo**:
- Fase CRÍTICA: ~155-180 tests (60-70% del esfuerzo)
- Fase ALTA: ~60-88 tests (25-30% del esfuerzo)
- Fase FINAL: ~18-22 tests (5-10% del esfuerzo)

### 6.3 Recomendación Final

**APROBADO PARA IMPLEMENTACIÓN** ✅

Las tareas están listas para comenzar la implementación. Recomiendo:

1. ✅ **Implementar task-308 inmediatamente** (bloquea todas las demás)
2. ✅ **Seguir orden de prioridad** sugerido en 5.1
3. ⚠️ **Crear tasks 324 y 325** antes de empezar fase ALTA
4. ✅ **Validar continuamente** después de cada tarea (no esperar al final)
5. ✅ **Documentar issues/blockers** que surjan durante implementación

**Tiempo total estimado** (siguiendo orden de prioridad):
- Fase preparación: 2-3 horas (task-308)
- Fase CRÍTICA: 8-12 días (tasks 309-313)
- Fase ALTA: 5-7 días (tasks 315-319)
- Fase MEDIA: 2-3 días (tasks 320-322, 314)
- Fase validación: 2-3 horas (task-323)
- **TOTAL**: ~15-22 días laborables

---

**Documento generado**: 2025-12-10
**Revisión completada**: ✅
**Estado**: Listo para implementación
