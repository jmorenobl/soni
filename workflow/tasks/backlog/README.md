# Backlog de Tests Unitarios - Cobertura >85%

Este directorio contiene las tareas para implementar tests unitarios exhaustivos según el análisis documentado en `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` y `docs/analysis/GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md`.

## Resumen Ejecutivo

**Objetivo**: Alcanzar cobertura >85% en tests unitarios (actualmente 66.23%)

**Estrategia**: Implementación por fases según prioridad:
- **Fase CRÍTICA**: Módulos con cobertura <50%
- **Fase ALTA**: Módulos con cobertura 50-80%
- **Fase FINAL**: Módulos con cobertura >80% (completitud)

**Total estimado**: ~232-290 tests nuevos

## Tareas por Fase

### Tarea Base (Prerrequisito)

- **[task-308](task-308-update-conftest-fixtures.md)**: Actualizar conftest.py con Fixtures
  - **Duración**: 2-3 horas
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente

### Fase CRÍTICA (<50% cobertura)

- **[task-309](task-309-tests-handle-correction.md)**: Tests para handle_correction.py
  - **Cobertura actual**: 6%
  - **Tests estimados**: ~30
  - **Duración**: 1-2 días
  - **Dependencias**: task-308

- **[task-310](task-310-tests-handle-modification.md)**: Tests para handle_modification.py
  - **Cobertura actual**: 6%
  - **Tests estimados**: ~25
  - **Duración**: 1-2 días
  - **Dependencias**: task-308, task-309

- **[task-311](task-311-tests-routing.md)**: Tests para routing.py
  - **Cobertura actual**: 38%
  - **Tests estimados**: ~50-60
  - **Duración**: 2-3 días
  - **Dependencias**: task-308
  - **Nota**: Módulo más crítico de routing

- **[task-312](task-312-tests-handle-confirmation.md)**: Tests para handle_confirmation.py
  - **Cobertura actual**: 40%
  - **Tests estimados**: ~20-25
  - **Duración**: 1-2 días
  - **Dependencias**: task-308, task-309

- **[task-313](task-313-tests-validate-slot.md)**: Tests para validate_slot.py
  - **Cobertura actual**: 46%
  - **Tests estimados**: ~30-40
  - **Duración**: 1-2 días
  - **Dependencias**: task-308

- **[task-314](task-314-tests-optimizers.md)**: Tests para du/optimizers.py
  - **Cobertura actual**: 27%
  - **Tests estimados**: ~7-10
  - **Duración**: 1 día
  - **Dependencias**: task-308
  - **Nota**: Requiere mocks de LLM

### Fase ALTA (50-80% cobertura)

- **[task-315](task-315-tests-runtime.md)**: Tests para runtime/runtime.py
  - **Cobertura actual**: 59%
  - **Tests estimados**: ~20-30
  - **Duración**: 1-2 días
  - **Dependencias**: task-308

- **[task-316](task-316-tests-response-generator.md)**: Tests para utils/response_generator.py
  - **Cobertura actual**: 61%
  - **Tests estimados**: ~5-8
  - **Duración**: 4-6 horas
  - **Dependencias**: task-308

- **[task-317](task-317-tests-normalizer.md)**: Tests para du/normalizer.py
  - **Cobertura actual**: 67%
  - **Tests estimados**: ~10-15
  - **Duración**: 1 día
  - **Dependencias**: task-308
  - **Nota**: Requiere mocks de LLM

- **[task-318](task-318-tests-step-manager.md)**: Tests para flow/step_manager.py
  - **Cobertura actual**: 69%
  - **Tests estimados**: ~15-20
  - **Duración**: 1 día
  - **Dependencias**: task-308

- **[task-319](task-319-tests-handle-intent-change.md)**: Tests adicionales para handle_intent_change.py
  - **Cobertura actual**: 69%
  - **Tests estimados**: ~10-15
  - **Duración**: 1 día
  - **Dependencias**: task-308

### Fase FINAL (>80% cobertura)

- **[task-320](task-320-tests-flow-manager.md)**: Tests adicionales para flow/manager.py
  - **Cobertura actual**: 89%
  - **Tests estimados**: ~5
  - **Duración**: 4-6 horas
  - **Dependencias**: task-308

- **[task-321](task-321-tests-persistence.md)**: Tests adicionales para dm/persistence.py
  - **Cobertura actual**: 84%
  - **Tests estimados**: ~5
  - **Duración**: 4-6 horas
  - **Dependencias**: task-308

- **[task-322](task-322-tests-flow-cleanup.md)**: Tests adicionales para utils/flow_cleanup.py
  - **Cobertura actual**: 96%
  - **Tests estimados**: ~1-2
  - **Duración**: 2-3 horas
  - **Dependencias**: task-308

### Validación Final

- **[task-323](task-323-validate-unit-tests-coverage.md)**: Validación Final de Cobertura
  - **Duración**: 2-3 horas
  - **Dependencias**: Todas las tareas anteriores (308-322)
  - **Objetivo**: Verificar cobertura >85% y calidad de tests

## Orden Recomendado de Implementación

1. **Primero**: task-308 (fixtures base)
2. **Fase CRÍTICA** (en paralelo cuando sea posible):
   - task-309 (handle_correction)
   - task-311 (routing) - más grande, puede hacerse en paralelo
   - task-313 (validate_slot)
3. **Después de correction**: task-310 (handle_modification - similar a correction)
4. **Después de correction**: task-312 (handle_confirmation - usa correction)
5. **Fase ALTA**: task-315, 316, 317, 318, 319 (pueden hacerse en paralelo)
6. **Fase FINAL**: task-320, 321, 322 (rápidas)
7. **Finalmente**: task-323 (validación)

## Principios Clave

1. **Tests 100% Deterministas**: TODOS los tests unitarios DEBEN mockear el NLU
2. **No LLMs en tests unitarios**: Solo en tests de integración
3. **Rápidos**: Cada test <1s, suite completa <10 minutos
4. **Independientes**: Sin dependencias externas (DB, API, LLM)
5. **Patrones Conversacionales**: Cubrir todos los patrones definidos en diseño

## Referencias

### Cobertura de Tests
- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Análisis detallado
- `docs/analysis/GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md` - Guía práctica

### Conformidad con Diseño
- `docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md` - Informe de conformidad
- `docs/design/10-dsl-specification/06-patterns.md` - Especificación de patrones conversacionales
- `docs/design/04-state-machine.md` - State machine design
- `docs/design/05-message-flow.md` - Message flow design

### Reglas del Proyecto
- `.cursor/rules/003-testing.mdc` - Reglas de testing del proyecto

## Tareas de Conformidad con Diseño

Estas tareas corrigen gaps identificados en el informe de conformidad (`docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md`) para asegurar que los tests validan correctamente los patrones conversacionales y principios de diseño.

### Fase 1: Critical Fixes (Próxima Semana)

- **[task-324](task-324-tests-clarification-pattern.md)**: Tests para Patrón CLARIFICATION
  - **Prioridad**: 🔴 ALTA
  - **Duración**: 2-3 horas
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Crear tests para patrón CLARIFICATION (0% cobertura actual)

- **[task-325](task-325-tests-cancellation-pattern.md)**: Tests para Patrón CANCELLATION
  - **Prioridad**: 🔴 CRÍTICA
  - **Duración**: 4-5 horas
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Crear tests exhaustivos para patrón CANCELLATION (30% cobertura actual)

- **[task-326](task-326-digression-flow-stack-assertions.md)**: Agregar Assertions de flow_stack a Tests de Digression
  - **Prioridad**: 🔴 MEDIA-ALTA
  - **Duración**: 30 minutos
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Verificar que digression NO modifica flow_stack (principio de diseño)

- **[task-327](task-327-confirmation-correction-message-regeneration.md)**: Test de Regeneración de Mensaje en Correction Durante Confirmation
  - **Prioridad**: ⚠️ MEDIA
  - **Duración**: 1 hora
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Verificar regeneración de mensaje de confirmación cuando se corrige slot

### Fase 2: Enhanced Coverage (Próximo Sprint)

- **[task-328](task-328-multi-slot-skip-logic.md)**: Tests para Multi-Slot Skip Logic
  - **Prioridad**: ⚠️ MEDIA
  - **Duración**: 1-2 horas
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Verificar que pasos de collect se saltan cuando slots ya están completados

- **[task-329](task-329-continuation-pattern-tests.md)**: Tests para Patrón CONTINUATION
  - **Prioridad**: 🟡 BAJA
  - **Duración**: 2 horas
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Completar tests para patrón CONTINUATION (40% cobertura actual)

- **[task-330](task-330-digression-depth-limits.md)**: Tests para Límites de Digression Depth
  - **Prioridad**: 🟡 BAJA
  - **Duración**: 1-2 horas
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Verificar límites de profundidad de digresiones consecutivas

- **[task-331](task-331-interruption-stack-limits.md)**: Tests para Límites de Stack en Interruption
  - **Prioridad**: 🟡 BAJA
  - **Duración**: 1 hora
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Verificar límites de stack depth durante interruptions

### Fase 3: Quality Improvements (Mes Siguiente)

- **[task-332](task-332-design-reference-comments.md)**: Agregar Comentarios de Referencia al Diseño en Tests
  - **Prioridad**: 🟢 BAJA
  - **Duración**: 1 hora
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Mejorar trazabilidad entre tests y diseño con referencias

- **[task-333](task-333-state-transition-validator.md)**: Crear Helper de Validación de Transiciones de Estado
  - **Prioridad**: 🟢 BAJA
  - **Duración**: 2-3 horas
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Crear helper para validar transiciones de estado según state machine

## Orden Recomendado de Implementación (Conformidad)

1. **Fase 1 - Critical Fixes** (8-10 horas):
   - task-325 (CANCELLATION) - CRÍTICA, hacer primero
   - task-324 (CLARIFICATION) - ALTA
   - task-326 (digression flow_stack) - Rápida (30min)
   - task-327 (confirmation message regeneration) - Rápida (1h)

2. **Fase 2 - Enhanced Coverage** (5-8 horas):
   - task-328 (multi-slot skip) - MEDIA
   - task-329 (continuation) - BAJA
   - task-330 (digression depth) - BAJA
   - task-331 (interruption stack) - BAJA

3. **Fase 3 - Quality Improvements** (3-5 horas):
   - task-332 (design references) - BAJA
   - task-333 (state transition validator) - BAJA

## Tareas de Mejora del NLU

Estas tareas mejoran la documentación y estructura del módulo NLU (Dialogue Understanding) para facilitar la optimización con DSPy y el mantenimiento del código.

### Fase Única: NLU Documentation Improvements

- **[task-334](task-334-document-nlu-data-structures.md)**: Document NLU Data Structures and Injection Flow
  - **Duración**: 2-3 horas
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Crear documentación de referencia para desarrolladores sobre estructuras de datos del NLU

- **[task-335](task-335-refactor-dialogue-understanding-signature.md)**: Refactor DialogueUnderstanding Signature Docstring
  - **Duración**: 2-3 horas
  - **Dependencias**: task-334
  - **Estado**: Pendiente
  - **Objetivo**: Refactorizar docstring de signature para ser conciso y autocontenido (enviado al LLM)

- **[task-336](task-336-improve-sonidu-module-documentation.md)**: Improve SoniDU Module Documentation
  - **Duración**: 2 horas
  - **Dependencias**: task-334
  - **Estado**: Pendiente
  - **Objetivo**: Mejorar documentación del módulo SoniDU (propósito, flujo de datos, interfaces)

- **[task-337](task-337-enrich-models-with-examples.md)**: Enrich NLU Models with Examples and Documentation
  - **Duración**: 2-3 horas
  - **Dependencias**: task-334
  - **Estado**: Pendiente
  - **Objetivo**: Añadir ejemplos exhaustivos a enums y modelos (MessageType, SlotAction, etc.)

- **[task-338](task-338-validate-nlu-documentation-improvements.md)**: Validate NLU Documentation Improvements
  - **Duración**: 1-2 horas
  - **Dependencias**: task-334, task-335, task-336, task-337
  - **Estado**: Pendiente
  - **Objetivo**: Validar que todas las mejoras están implementadas correctamente

**Orden recomendado:**
1. task-334 (prerequisito - crea documentación de referencia)
2. task-335, task-336, task-337 (pueden hacerse en paralelo)
3. task-338 (validación final)

**Notas importantes:**
- DATA_STRUCTURES.md es solo para desarrolladores, NO se envía al LLM
- Docstrings de signatures deben ser autocontenidos (el LLM los ve)
- Todos los ejemplos usan el escenario flight_booking para consistencia

## Estado del Backlog

**Total de tareas (Cobertura)**: 16
- **Pendientes**: 16
- **En progreso**: 0
- **Completadas**: 0

**Total de tareas (Conformidad)**: 10
- **Pendientes**: 10
- **En progreso**: 0
- **Completadas**: 0

**Total de tareas (NLU Improvements)**: 5
- **Pendientes**: 5
- **En progreso**: 0
- **Completadas**: 0

## Tareas de Corrección de Bugs (No-NLU)

Estas tareas corrigen problemas de lógica y configuración identificados en `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` que NO son problemas del NLU.

### Prioridad Alta (Bugs Críticos)

- **[task-339](task-339-fix-cancellation-infinite-loop.md)**: Fix Cancellation Infinite Loop
  - **Prioridad**: 🔴 CRÍTICA
  - **Duración**: 4-6 horas
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Corregir loop infinito cuando el usuario cancela un flow

- **[task-340](task-340-fix-digression-conversation-state.md)**: Fix Digression Conversation State
  - **Prioridad**: 🔴 ALTA
  - **Duración**: 2-3 horas
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Corregir conversation_state después de digresión (debe ser waiting_for_slot, no idle)

- **[task-341](task-341-fix-correction-acknowledgment-template.md)**: Fix Correction Acknowledgment Template
  - **Prioridad**: 🔴 ALTA
  - **Duración**: 3-4 horas
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Corregir uso del template correction_acknowledged cuando se corrige un slot

### Prioridad Media (Configuración de Tests)

- **[task-342](task-342-fix-optimizer-tests-valset-size.md)**: Fix Optimizer Tests Valset Size
  - **Prioridad**: ⚠️ MEDIA
  - **Duración**: 1-2 horas
  - **Dependencias**: Ninguna
  - **Estado**: Pendiente
  - **Objetivo**: Corregir tests de optimizadores que fallan por valset demasiado pequeño

**Orden recomendado:**
1. task-339 (crítico - loop infinito)
2. task-340 y task-341 (pueden hacerse en paralelo)
3. task-342 (configuración de tests)

**Total de tareas (Bug Fixes)**: 4
- **Pendientes**: 4
- **En progreso**: 0
- **Completadas**: 0

**Total general**: 35 tareas

## Tareas de Dataset para Optimización NLU

Estas tareas implementan el paquete de dataset para generar ejemplos de entrenamiento que permitan optimizar el sistema NLU con DSPy.

### Objetivo

Crear un dataset de ~150-200 ejemplos cubriendo:
- **9 Patrones Conversacionales**: SLOT_VALUE, CORRECTION, MODIFICATION, INTERRUPTION, DIGRESSION, CLARIFICATION, CANCELLATION, CONFIRMATION, CONTINUATION
- **4 Dominios**: flight_booking, hotel_booking, restaurant, ecommerce
- **2 Contextos**: cold_start (sin histórico), ongoing (con histórico conversacional)

### Estructura de Tareas

#### Fase 1: Infraestructura Base

- **[task-701](task-701-dataset-base-infrastructure.md)**: Dataset Base Infrastructure
  - **Duración**: 3-4 horas
  - **Dependencias**: Ninguna
  - **Objetivo**: Crear clases base (DomainConfig, PatternGenerator, ExampleTemplate, DatasetBuilder)

#### Fase 2: Dominios de Negocio

- **[task-702](task-702-dataset-domain-flight-booking.md)**: Domain: Flight Booking
  - **Duración**: 2-3 horas
  - **Dependencias**: task-701
  - **Objetivo**: Implementar dominio flight_booking (template para otros dominios)

- **[task-703](task-703-dataset-additional-domains.md)**: Additional Domains (Hotel, Restaurant, Ecommerce)
  - **Duración**: 4-5 horas
  - **Dependencias**: task-702
  - **Objetivo**: Implementar 3 dominios adicionales siguiendo el patrón de flight_booking

#### Fase 3: Generadores de Patrones

- **[task-704](task-704-dataset-patterns-slot-value.md)**: Pattern: SLOT_VALUE
  - **Duración**: 3-4 horas
  - **Dependencias**: task-701, task-702, task-703
  - **Objetivo**: Implementar generador para patrón más común (respuesta directa a slots)

- **[task-705](task-705-dataset-patterns-correction-modification.md)**: Patterns: CORRECTION & MODIFICATION
  - **Duración**: 3-4 horas
  - **Dependencias**: task-704
  - **Objetivo**: Generadores para correcciones reactivas y modificaciones proactivas

- **[task-706](task-706-dataset-patterns-flow-control.md)**: Patterns: Flow Control (INTERRUPTION, CANCELLATION, CONTINUATION)
  - **Duración**: 3-4 horas
  - **Dependencias**: task-705
  - **Objetivo**: Generadores para control de flujo conversacional

- **[task-707](task-707-dataset-patterns-questions.md)**: Patterns: Questions (DIGRESSION, CLARIFICATION, CONFIRMATION)
  - **Duración**: 3-4 horas
  - **Dependencias**: task-706
  - **Objetivo**: Generadores para preguntas del usuario

#### Fase 4: Integración y Validación

- **[task-708](task-708-dataset-integration-validation.md)**: Dataset Integration & Validation
  - **Duración**: 2-3 horas
  - **Dependencias**: task-707
  - **Objetivo**: Integrar todos los componentes, generar dataset completo, validar y documentar

### Orden Recomendado de Implementación

```
task-701 (base)
    ↓
task-702 (flight_booking)
    ↓
task-703 (otros dominios)
    ↓
task-704 (SLOT_VALUE)
    ↓
task-705 (CORRECTION + MODIFICATION)
    ↓
task-706 (INTERRUPTION + CANCELLATION + CONTINUATION)
    ↓
task-707 (DIGRESSION + CLARIFICATION + CONFIRMATION)
    ↓
task-708 (integración + validación)
```

**Paralelización posible:**
- Tasks 705, 706, 707 pueden hacerse en paralelo después de task-704
- La task-708 requiere que todas las anteriores estén completas

### Características del Dataset

**Dimensiones:**
- Patrones: 9 (todos los MessageType)
- Dominios: 4 (flight, hotel, restaurant, ecommerce)
- Contextos: 2 (cold_start, ongoing)
- Ejemplos por combinación: 2-3

**Total estimado:** ~150-200 ejemplos manuales curados

**Uso del dataset:**
```python
from soni.dataset import DatasetBuilder

builder = DatasetBuilder()
trainset = builder.build_all(examples_per_combination=2)

# Optimizar con DSPy
from soni.du.optimizers import optimize_soni_du
optimized_nlu, metrics = optimize_soni_du(
    trainset=trainset,
    optimizer_type="MIPROv2",
    num_trials=50,
)
```

### Referencias

- docs/design/06-nlu-system.md - Arquitectura NLU y optimización DSPy
- docs/design/10-dsl-specification/06-patterns.md - Patrones conversacionales
- https://dspy-docs.vercel.app/ - Documentación DSPy

**Total de tareas (Dataset)**: 8
- **Pendientes**: 8
- **En progreso**: 0
- **Completadas**: 0

**Total general**: 43 tareas

**Última actualización**: 2025-12-11
