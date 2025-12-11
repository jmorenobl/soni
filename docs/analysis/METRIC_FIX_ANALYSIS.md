# Análisis y Corrección de la Métrica de Optimización NLU

## Problema Identificado

El script `generate_baseline_optimization.py` reportaba **100% de accuracy** en la optimización baseline, pero los tests de integración fallaban con 5 errores relacionados con:

1. **Confirmación y modificación**: El sistema no detecta correctamente cuando el usuario quiere modificar durante la confirmación
2. **Reintentos de confirmación**: El sistema no maneja correctamente respuestas poco claras
3. **Acknowledgment de correcciones**: El sistema no usa el template correcto para reconocer correcciones
4. **Digresiones**: El sistema no vuelve correctamente al flujo después de una digresión
5. **Flujo E2E**: El sistema no genera respuestas apropiadas después de completar todos los slots

## Causa Raíz

La métrica `intent_accuracy_metric` en `src/soni/du/metrics.py` estaba evaluando campos **que no existen** en los ejemplos del dataset:

### Campos que la métrica buscaba (INCORRECTO):
- `structured_command` ❌ (no existe en los ejemplos)
- `extracted_slots` ❌ (no existe en los ejemplos)

### Campos que realmente existen en los ejemplos:
- `result.message_type` ✅ (MessageType enum: SLOT_VALUE, CORRECTION, etc.)
- `result.command` ✅ (string: "book_flight", etc.)
- `result.slots` ✅ (list[SlotValue]: valores extraídos)

## Impacto

Como la métrica buscaba campos inexistentes:
1. **Siempre devolvía 0.0 o valores por defecto** (ambos campos vacíos coincidían)
2. **El accuracy del 100% era falso** - la métrica no estaba evaluando nada real
3. **La optimización no mejoraba el NLU** porque no sabía qué estaba evaluando
4. **Los tests fallaban** porque el NLU no estaba optimizado correctamente

## Solución Implementada

Se corrigió la métrica `intent_accuracy_metric` para evaluar los campos correctos:

### Nueva Métrica (CORRECTO):
- **40% peso**: `message_type` (crítico para routing)
- **30% peso**: `command` (intent/flow name)
- **30% peso**: `slots` (valores extraídos con matching fuzzy)

### Cambios Realizados:

1. **Acceso correcto a los campos**:
   ```python
   expected_result = example.result  # NLUOutput
   predicted_result = prediction.result  # NLUOutput
   ```

2. **Comparación de message_type** (40% del peso):
   ```python
   message_type_match = expected_result.message_type == predicted_result.message_type
   ```

3. **Comparación de command** (30% del peso):
   ```python
   command_match = (expected_result.command or "").lower() == (predicted_result.command or "").lower()
   ```

4. **Comparación de slots** (30% del peso):
   - Compara nombre y valor de cada slot
   - Permite matching fuzzy (substring)
   - Verifica que todos los slots esperados estén presentes

## Próximos Pasos

1. **Regenerar la optimización baseline**:
   ```bash
   uv run python scripts/generate_baseline_optimization.py
   ```

2. **Verificar que el accuracy sea realista**:
   - El accuracy debería ser menor al 100% inicialmente
   - La optimización debería mejorar el accuracy progresivamente

3. **Ejecutar los tests de integración**:
   ```bash
   make test-integration
   ```

4. **Si los tests aún fallan**:
   - Revisar si el dataset necesita más ejemplos de los casos que fallan
   - Añadir ejemplos específicos de los escenarios de los tests al dataset

## Casos de Test que Fallan

Los siguientes casos deberían estar mejor representados en el dataset:

1. **Confirmación con modificación**: "No, change the destination"
2. **Reintentos de confirmación**: Respuestas poco claras como "maybe", "hmm"
3. **Correcciones durante confirmación**: "Actually, I meant next Monday"
4. **Digresiones**: Preguntas que interrumpen el flujo
5. **Flujo completo E2E**: Todos los slots proporcionados en secuencia

## Referencias

- Métrica corregida: `src/soni/du/metrics.py`
- Dataset: `src/soni/du/datasets/baseline_v1.json`
- Script de optimización: `scripts/generate_baseline_optimization.py`
- Tests que fallan: `tests/integration/test_*.py`
