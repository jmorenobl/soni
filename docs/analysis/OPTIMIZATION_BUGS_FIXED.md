# Bugs Corregidos en el Sistema de Optimización NLU

## Resumen

Se identificaron y corrigieron múltiples bugs en el sistema de optimización que causaban que la métrica reportara accuracy incorrecto (100% falso) y que la optimización no funcionara correctamente.

## Bugs Encontrados y Corregidos

### 1. ✅ Métrica Evaluaba Campos Incorrectos (CRÍTICO)

**Problema**: La métrica `intent_accuracy_metric` buscaba campos que no existen en los ejemplos:
- `structured_command` ❌ (no existe)
- `extracted_slots` ❌ (no existe)

**Impacto**:
- La métrica siempre devolvía 0.0 o valores por defecto
- El accuracy del 100% era completamente falso
- La optimización no mejoraba el NLU porque no sabía qué evaluar

**Solución**:
- Corregida para evaluar los campos correctos:
  - `result.message_type` (40% peso) - CRÍTICO para routing
  - `result.command` (30% peso) - Intent/flow name
  - `result.slots` (30% peso) - Valores extraídos

**Archivo**: `src/soni/du/metrics.py`

### 2. ✅ Duplicado de `scores.append(0.0)` en Evaluación

**Problema**: En `_evaluate_module`, había un `scores.append(0.0)` duplicado en el bloque de excepciones.

**Impacto**:
- Código redundante
- Posible confusión en debugging

**Solución**: Eliminado el duplicado.

**Archivo**: `src/soni/du/optimizers.py`

### 3. ✅ No Manejo de Resultados como Dict

**Problema**: DSPy puede devolver resultados como `dict` en lugar de objetos `NLUOutput`, especialmente cuando el LLM no devuelve el formato exacto.

**Impacto**:
- La métrica fallaba silenciosamente cuando DSPy devolvía dicts
- Se perdían evaluaciones válidas

**Solución**:
- Añadida función `_extract_nlu_output()` que maneja:
  - Objetos `NLUOutput` directamente
  - Dicts que se convierten a `NLUOutput` usando `model_validate()`
  - Valores `None` o inválidos

**Archivo**: `src/soni/du/metrics.py`

### 4. ✅ Comparación de MessageType (Enum vs String)

**Problema**: `message_type` puede ser un enum `MessageType` o un string, dependiendo de cómo DSPy lo devuelva.

**Impacto**:
- Comparaciones fallaban cuando uno era enum y otro string
- Falsos negativos en la evaluación

**Solución**:
- Añadida función `_normalize_message_type()` que:
  - Convierte enums a su valor string
  - Normaliza strings a lowercase
  - Maneja casos edge

**Archivo**: `src/soni/du/metrics.py`

### 5. ✅ Comparación de Slots con Dicts

**Problema**: Los slots pueden venir como objetos `SlotValue` o como dicts, dependiendo de cómo DSPy los devuelva.

**Impacto**:
- La comparación fallaba cuando los slots eran dicts
- Falsos negativos en la evaluación

**Solución**:
- Mejorada función `_compare_slots()` para manejar:
  - Objetos `SlotValue` con atributos
  - Dicts con claves `name` y `value`
  - Normalización de valores a lowercase
  - Matching fuzzy (substring)

**Archivo**: `src/soni/du/metrics.py`

## Mejoras Adicionales

### Manejo de Errores Mejorado

- Logging más detallado con índices de ejemplo
- Información de contexto en warnings
- Manejo graceful de errores sin romper la evaluación completa

### Robustez de la Comparación

- Normalización de tipos (enum → string)
- Manejo de valores None/vacíos
- Matching fuzzy para valores de slots (permite variaciones menores)

## Próximos Pasos

1. **Regenerar optimización baseline**:
   ```bash
   uv run python scripts/generate_baseline_optimization.py
   ```

2. **Verificar accuracy realista**:
   - El accuracy inicial debería ser < 100%
   - La optimización debería mostrar mejora progresiva

3. **Ejecutar tests de integración**:
   ```bash
   make test-integration
   ```

4. **Si los tests aún fallan**:
   - Revisar si el dataset necesita más ejemplos
   - Añadir casos específicos de los tests que fallan

## Archivos Modificados

- `src/soni/du/metrics.py` - Métrica corregida completamente
- `src/soni/du/optimizers.py` - Bug de duplicado corregido
- `docs/analysis/METRIC_FIX_ANALYSIS.md` - Análisis del problema original
- `docs/analysis/OPTIMIZATION_BUGS_FIXED.md` - Este documento

## Validación

Para validar que los bugs están corregidos:

1. **Verificar que la métrica funciona**:
   ```python
   from soni.du.metrics import intent_accuracy_metric
   from soni.du.models import NLUOutput, MessageType
   import dspy

   # Crear ejemplo y predicción
   example = dspy.Example(
       result=NLUOutput(
           message_type=MessageType.SLOT_VALUE,
           command=None,
           slots=[],
           confidence=0.9
       )
   )

   prediction = dspy.Prediction(
       result=NLUOutput(
           message_type=MessageType.SLOT_VALUE,
           command=None,
           slots=[],
           confidence=0.9
       )
   )

   # Debería devolver 1.0 (match perfecto)
   score = intent_accuracy_metric(example, prediction)
   assert score == 1.0
   ```

2. **Verificar manejo de dicts**:
   ```python
   # DSPy puede devolver dicts
   prediction_dict = dspy.Prediction(
       result={
           "message_type": "slot_value",
           "command": None,
           "slots": [],
           "confidence": 0.9
       }
   )

   # Debería funcionar correctamente
   score = intent_accuracy_metric(example, prediction_dict)
   ```

## Referencias

- Issue original: Accuracy del 100% era falso
- Tests que fallaban: 5 tests de integración relacionados con routing y respuestas
- Dataset: `src/soni/du/datasets/baseline_v1.json`
- Script de optimización: `scripts/generate_baseline_optimization.py`
