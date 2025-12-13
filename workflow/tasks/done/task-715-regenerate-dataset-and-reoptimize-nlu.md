## Task: 715 - Regenerate Dataset and Re-optimize NLU

**ID de tarea:** 715
**Hito:** Fix Integration Test Failures - NLU Re-optimization
**Dependencias:** 709, 710, 711, 712 (Todas las tareas de añadir ejemplos al dataset)
**Duración estimada:** 4-6 horas (incluye tiempo de optimización)

### Objetivo

Regenerar el dataset con los nuevos ejemplos añadidos en las tareas 709-712 y re-optimizar el módulo NLU para que los cambios surtan efecto en los tests de integración.

### Contexto

**Problema identificado:**
- Después de añadir nuevos ejemplos al dataset (tareas 709-712), es necesario:
  1. Regenerar el dataset completo
  2. Re-ejecutar la optimización del NLU con el nuevo dataset
  3. Validar que los tests de integración pasan con el NLU optimizado

**Referencias:**
- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Plan de acción completo
- `scripts/generate_baseline_optimization.py` - Script de generación y optimización
- `src/soni/du/optimizers.py` - Optimizadores DSPy
- `src/soni/du/optimized/` - Módulos NLU optimizados

### Entregables

- [ ] El dataset se regenera con todos los nuevos ejemplos
- [ ] El NLU se re-optimiza con el nuevo dataset
- [ ] El módulo optimizado se guarda en `src/soni/du/optimized/`
- [ ] Los tests de integración pasan con el NLU optimizado
- [ ] Se documentan las métricas de mejora (baseline vs optimizado)

### Implementación Detallada

#### Paso 1: Regenerar el dataset

**Archivo(s) a usar:** `scripts/generate_baseline_optimization.py` o script equivalente

**Comandos:**

```bash
# Regenerar dataset con todos los nuevos ejemplos
uv run python scripts/generate_baseline_optimization.py

# O si hay un script específico para generar dataset:
uv run python scripts/generate_dataset.py
```

**Verificaciones:**
- El dataset incluye los nuevos ejemplos de cancelación (tarea 709)
- El dataset incluye los nuevos ejemplos de modificación (tarea 710)
- El dataset incluye los nuevos ejemplos de confirmación ambigua (tarea 711)
- El dataset incluye los ejemplos de fechas relativas verificados (tarea 712)

**Validación:**

```bash
# Verificar que el dataset incluye los nuevos ejemplos
uv run python -c "
from soni.dataset.registry import DatasetRegistry
registry = DatasetRegistry()
dataset = registry.build_dataset('flight_booking')
print(f'Total examples: {len(dataset)}')

# Verificar ejemplos de cancelación con nuevas frases
cancellation_examples = [e for e in dataset if 'Actually, cancel' in e.user_message]
print(f'Cancellation examples with new phrases: {len(cancellation_examples)}')

# Verificar ejemplos de modificación tras confirmación
modification_examples = [e for e in dataset if 'No, change' in e.user_message]
print(f'Modification after confirmation examples: {len(modification_examples)}')

# Verificar ejemplos de confirmación ambigua
unclear_examples = [e for e in dataset if e.expected_output.confirmation_value is None]
print(f'Unclear confirmation examples: {len(unclear_examples)}')
"
```

#### Paso 2: Re-optimizar el NLU

**Archivo(s) a usar:** `scripts/generate_baseline_optimization.py` o `src/soni/du/optimizers.py`

**Comandos:**

```bash
# Ejecutar optimización completa
uv run python scripts/generate_baseline_optimization.py

# O ejecutar optimización manualmente:
uv run python -c "
from soni.dataset.registry import DatasetRegistry
from soni.du.optimizers import optimize_soni_du
from pathlib import Path

# Cargar dataset
registry = DatasetRegistry()
trainset = registry.build_dataset('flight_booking')

# Optimizar
optimized_nlu, metrics = optimize_soni_du(
    trainset=trainset,
    optimizer_type='MIPROv2',
    num_trials=20,  # Ajustar según necesidad
    output_dir=Path('src/soni/du/optimized/baseline_v2'),
)

# Guardar métricas
import json
with open('src/soni/du/optimized/baseline_v2_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)
"
```

**Parámetros de optimización:**
- `num_trials`: 20-30 (ajustar según tiempo disponible)
- `timeout_seconds`: 600-900 (10-15 minutos)
- `max_bootstrapped_demos`: 6
- `max_labeled_demos`: 8

**Verificaciones:**
- La optimización completa sin errores
- El módulo optimizado se guarda correctamente
- Las métricas se guardan para comparación

#### Paso 3: Validar mejora de métricas

**Archivo(s) a revisar:** `src/soni/du/optimized/baseline_v2_metrics.json`

**Verificaciones:**
- `baseline_accuracy`: Accuracy antes de optimización
- `optimized_accuracy`: Accuracy después de optimización
- `improvement`: Mejora porcentual
- Comparar con métricas anteriores

**Código de análisis:**

```python
import json

# Cargar métricas anteriores y nuevas
with open('src/soni/du/optimized/baseline_v1_metrics.json') as f:
    old_metrics = json.load(f)

with open('src/soni/du/optimized/baseline_v2_metrics.json') as f:
    new_metrics = json.load(f)

print(f"Baseline accuracy: {new_metrics['baseline_accuracy']:.2%}")
print(f"Optimized accuracy: {new_metrics['optimized_accuracy']:.2%}")
print(f"Improvement: {new_metrics['improvement_pct']:+.1f}%")
print(f"Previous optimized: {old_metrics.get('optimized_accuracy', 'N/A')}")
```

#### Paso 4: Validar tests de integración

**Comandos:**

```bash
# Ejecutar tests que deberían pasar ahora
uv run pytest tests/integration/test_all_scenarios.py::TestScenario5Cancellation::test_scenario_5_cancellation -v
uv run pytest tests/integration/test_confirmation_flow.py::test_complete_confirmation_flow_no_then_modify -v
uv run pytest tests/integration/test_confirmation_flow.py::test_confirmation_unclear_then_yes -v
uv run pytest tests/integration/test_confirmation_flow.py::test_confirmation_max_retries -v
uv run pytest tests/integration/test_e2e.py::test_e2e_flight_booking_complete_flow -v

# Ejecutar suite completa de integración
uv run pytest tests/integration/ -v
```

**Verificaciones:**
- Los tests que fallaban por problemas de NLU ahora pasan
- Los tests que fallaban por problemas de lógica siguen fallando (esperado, se arreglan en tareas 713-714)

### Tests Requeridos

**Archivo de tests:** `tests/integration/` (tests existentes)

**Tests que deben pasar después de esta tarea:**
- `test_scenario_5_cancellation` (tarea 709)
- `test_complete_confirmation_flow_no_then_modify` (tarea 710)
- `test_confirmation_unclear_then_yes` (tarea 711)
- `test_confirmation_max_retries` (tarea 711)
- `test_e2e_flight_booking_complete_flow` (tarea 712)

**Tests que aún pueden fallar (problemas de lógica):**
- `test_action_to_confirmation_flow` (tarea 713)
- `test_digression_flow_with_mocked_nlu` (tarea 714)

### Criterios de Éxito

- [ ] El dataset se regenera con todos los nuevos ejemplos
- [ ] El NLU se re-optimiza exitosamente
- [ ] El módulo optimizado se guarda en `src/soni/du/optimized/baseline_v2/`
- [ ] Las métricas muestran mejora respecto al baseline
- [ ] Los tests de integración relacionados con NLU pasan
- [ ] Se documenta la mejora de métricas
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Verificar dataset regenerado
uv run python -c "from soni.dataset.registry import DatasetRegistry; r = DatasetRegistry(); d = r.build_dataset('flight_booking'); print(f'Dataset size: {len(d)}')"

# Verificar módulo optimizado guardado
ls -la src/soni/du/optimized/baseline_v2/

# Verificar métricas
cat src/soni/du/optimized/baseline_v2_metrics.json

# Ejecutar tests de integración
uv run pytest tests/integration/ -v --tb=short
```

**Resultado esperado:**
- Dataset incluye nuevos ejemplos
- Módulo optimizado guardado correctamente
- Métricas muestran mejora
- Tests de NLU pasan

### Referencias

- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Análisis completo y plan de acción
- `scripts/generate_baseline_optimization.py` - Script de generación y optimización
- `src/soni/du/optimizers.py` - Optimizadores DSPy
- `src/soni/dataset/registry.py` - Registro de datasets

### Notas Adicionales

- Esta tarea es parte de la Fase 3 del plan de acción (re-optimización)
- **Depende de las tareas 709-712** - No ejecutar hasta que todas estén completadas
- La optimización puede tardar 10-15 minutos dependiendo de `num_trials`
- Asegurar que hay suficiente tiempo y recursos (API keys, etc.) antes de ejecutar
- Guardar las métricas para comparación futura
- Si la optimización falla, revisar logs y ajustar parámetros
