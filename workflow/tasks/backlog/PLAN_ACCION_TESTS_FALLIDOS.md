# Plan de Acción: Arreglar Tests de Integración Fallidos

**Fecha de creación:** 2025-01-XX
**Estado:** Pendiente
**Tests afectados:** 7 tests de integración fallidos

## Resumen

Este plan de acción aborda los 7 tests de integración que están fallando, divididos en 3 fases:

- **Fase 1:** Añadir ejemplos al dataset (NLU) - 4 tareas
- **Fase 2:** Corregir lógica del sistema - 2 tareas
- **Fase 3:** Re-optimizar NLU - 1 tarea

## Tests Fallidos

1. `test_scenario_5_cancellation` - NLU no detecta "Actually, cancel this"
2. `test_action_to_confirmation_flow` - No avanza a confirmación después de acción
3. `test_complete_confirmation_flow_no_then_modify` - NLU no detecta modificación tras negativa
4. `test_confirmation_unclear_then_yes` - NLU no detecta respuestas ambiguas
5. `test_confirmation_max_retries` - NLU no maneja respuestas poco claras
6. `test_digression_flow_with_mocked_nlu` - No incluye respuesta de digresión
7. `test_e2e_flight_booking_complete_flow` - NLU no extrae fechas relativas correctamente

## Fase 1: Añadir Ejemplos al Dataset (NLU)

### Tarea 709: Add Cancellation Examples to Dataset
- **Archivo:** `task-709-add-cancellation-examples-dataset.md`
- **Objetivo:** Añadir "Actually, cancel this" y variantes a `CANCELLATION_UTTERANCES`
- **Tests afectados:** `test_scenario_5_cancellation`
- **Duración:** 2-3 horas
- **Dependencias:** Ninguna

### Tarea 710: Add Modification After Confirmation Examples
- **Archivo:** `task-710-add-modification-after-confirmation-examples.md`
- **Objetivo:** Añadir ejemplos de "No, change the destination" (sin nuevo valor)
- **Tests afectados:** `test_complete_confirmation_flow_no_then_modify`
- **Duración:** 2-3 horas
- **Dependencias:** Ninguna

### Tarea 711: Add Unclear Confirmation Examples
- **Archivo:** `task-711-add-unclear-confirmation-examples.md`
- **Objetivo:** Añadir `CONFIRMATION_UNCLEAR` y ejemplos con `confirmation_value=None`
- **Tests afectados:** `test_confirmation_unclear_then_yes`, `test_confirmation_max_retries`
- **Duración:** 2-3 horas
- **Dependencias:** Ninguna

### Tarea 712: Verify and Expand Relative Dates Examples
- **Archivo:** `task-712-verify-relative-dates-examples.md`
- **Objetivo:** Verificar y ampliar ejemplos de fechas relativas ("Next Friday", etc.)
- **Tests afectados:** `test_e2e_flight_booking_complete_flow`
- **Duración:** 1-2 horas
- **Dependencias:** Ninguna

## Fase 2: Corregir Lógica del Sistema

### Tarea 713: Fix Action to Confirmation Flow Advancement
- **Archivo:** `task-713-fix-action-to-confirmation-flow.md`
- **Objetivo:** Corregir avance de pasos después de ejecutar acción
- **Tests afectados:** `test_action_to_confirmation_flow`
- **Duración:** 3-4 horas
- **Dependencias:** Ninguna

### Tarea 714: Fix Digression Response Generation
- **Archivo:** `task-714-fix-digression-response-generation.md`
- **Objetivo:** Corregir `handle_digression` para incluir respuesta + re-prompt
- **Tests afectados:** `test_digression_flow_with_mocked_nlu`
- **Duración:** 3-4 horas
- **Dependencias:** Ninguna

## Fase 3: Re-optimizar NLU

### Tarea 715: Regenerate Dataset and Re-optimize NLU
- **Archivo:** `task-715-regenerate-dataset-and-reoptimize-nlu.md`
- **Objetivo:** Regenerar dataset y re-optimizar NLU con nuevos ejemplos
- **Tests afectados:** Todos los tests de NLU (tareas 709-712)
- **Duración:** 4-6 horas (incluye tiempo de optimización)
- **Dependencias:** 709, 710, 711, 712 (TODAS las tareas de Fase 1)

## Orden de Ejecución Recomendado

### Opción 1: Paralelo (Fase 1)
Las tareas 709-712 pueden ejecutarse en paralelo ya que no tienen dependencias entre sí.

```
Fase 1 (Paralelo):
├─ Tarea 709 ─┐
├─ Tarea 710 ├─→ Tarea 715 (Re-optimizar)
├─ Tarea 711 ─┤
└─ Tarea 712 ─┘

Fase 2 (Paralelo):
├─ Tarea 713
└─ Tarea 714
```

### Opción 2: Secuencial
Si prefieres ejecutar secuencialmente:

1. Tarea 709 → Tarea 710 → Tarea 711 → Tarea 712
2. Tarea 715 (después de todas las anteriores)
3. Tarea 713 y 714 (en paralelo o secuencial)

## Criterios de Éxito Global

- [ ] Todos los 7 tests de integración pasan
- [ ] El dataset incluye los nuevos ejemplos
- [ ] El NLU está re-optimizado con el nuevo dataset
- [ ] Las métricas muestran mejora en accuracy
- [ ] La lógica de avance de pasos funciona correctamente
- [ ] La generación de respuestas de digresión funciona correctamente

## Referencias

- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Análisis detallado de cada test fallido
- `tests/integration/` - Tests de integración
- `src/soni/dataset/` - Dataset y generadores de ejemplos
- `src/soni/du/optimizers.py` - Optimizadores DSPy

## Notas

- Las tareas de Fase 1 (709-712) son independientes y pueden ejecutarse en paralelo
- La tarea 715 debe ejecutarse DESPUÉS de completar todas las tareas de Fase 1
- Las tareas de Fase 2 (713-714) son independientes y pueden ejecutarse en paralelo
- La optimización (tarea 715) puede tardar 10-15 minutos dependiendo de `num_trials`
- Asegurar que hay suficiente tiempo y recursos (API keys, etc.) antes de ejecutar la optimización
