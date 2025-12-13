## Task: 709 - Add Cancellation Examples to Dataset

**ID de tarea:** 709
**Hito:** Fix Integration Test Failures - NLU Dataset Improvements
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Añadir ejemplos de cancelación al dataset para mejorar la detección del NLU de frases como "Actually, cancel this" que actualmente no están cubiertas en `CANCELLATION_UTTERANCES`.

### Contexto

**Problema identificado:**
- El test `test_scenario_5_cancellation` falla porque el NLU no detecta CANCELLATION con "Actually, cancel this"
- El dataset actual solo tiene frases simples: "Cancel", "Never mind", "Forget it", etc.
- Faltan variantes más naturales como "Actually, cancel this", "Cancel this", "I want to cancel"

**Referencias:**
- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 1.1
- `tests/integration/test_all_scenarios.py::TestScenario5Cancellation::test_scenario_5_cancellation`
- `src/soni/dataset/domains/flight_booking.py` - `CANCELLATION_UTTERANCES`
- `src/soni/dataset/patterns/cancellation.py` - Generador de ejemplos

### Entregables

- [ ] `CANCELLATION_UTTERANCES` incluye "Actually, cancel this" y variantes
- [ ] Se añaden ejemplos en `cancellation.py` con estas nuevas frases
- [ ] Los ejemplos cubren diferentes contextos (con slots parciales, sin slots, etc.)
- [ ] El dataset regenerado incluye estos nuevos ejemplos

### Implementación Detallada

#### Paso 1: Actualizar CANCELLATION_UTTERANCES

**Archivo(s) a modificar:** `src/soni/dataset/domains/flight_booking.py`

**Código específico:**

```python
CANCELLATION_UTTERANCES = [
    "Cancel",
    "Never mind",
    "Forget it",
    "I changed my mind",
    "Stop",
    "Cancel everything",
    "Actually, cancel this",  # ← NUEVO
    "Actually, cancel",        # ← NUEVO
    "Cancel this",             # ← NUEVO
    "I want to cancel",        # ← NUEVO
    "I'd like to cancel",      # ← NUEVO
    "Please cancel",           # ← NUEVO
]
```

**Explicación:**
- Añadir variantes más naturales que los usuarios pueden usar
- Incluir frases con "Actually" que son comunes en correcciones
- Mantener compatibilidad con ejemplos existentes

#### Paso 2: Añadir ejemplos en cancellation.py

**Archivo(s) a modificar:** `src/soni/dataset/patterns/cancellation.py`

**Código específico:**

```python
# En _generate_ongoing_examples para flight_booking:
# Añadir ejemplo con "Actually, cancel this" después de proporcionar origin
examples.append(
    ExampleTemplate(
        user_message="Actually, cancel this",
        conversation_context=ConversationContext(
            history=dspy.History(
                messages=[
                    {"user_message": "I want to book a flight"},
                    {"user_message": "Boston"},
                ]
            ),
            current_slots={"origin": "Boston"},
            current_flow="book_flight",
            expected_slots=["destination"],
        ),
        expected_output=NLUOutput(
            message_type=MessageType.CANCELLATION,
            command="book_flight",  # O None, dependiendo de la especificación
            slots=[],
            confidence=0.9,
        ),
        domain=domain_config.name,
        pattern="cancellation",
        context_type="ongoing",
        current_datetime="2024-12-11T10:00:00",
    )
)

# Añadir más variantes con diferentes contextos
```

**Explicación:**
- Crear ejemplos con diferentes estados (con slots parciales, sin slots)
- Usar las nuevas frases de `CANCELLATION_UTTERANCES`
- Asegurar que `command` sea correcto según la especificación

#### Paso 3: Verificar generación del dataset

**Archivo(s) a verificar:** Scripts de generación de dataset

**Comandos:**

```bash
# Regenerar dataset y verificar que incluye los nuevos ejemplos
uv run python scripts/generate_baseline_optimization.py
# O el script correspondiente para generar el dataset
```

**Verificaciones:**
- Los nuevos ejemplos aparecen en el dataset generado
- El formato es correcto (compatible con DSPy)
- No hay duplicados

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dataset_patterns.py` o similar

**Tests específicos a considerar:**

```python
def test_cancellation_examples_include_new_phrases():
    """Test que los ejemplos de cancelación incluyen las nuevas frases."""
    generator = CancellationGenerator()
    examples = generator.generate_examples(
        domain_config=FLIGHT_BOOKING,
        context_type="ongoing",
        count=10
    )

    messages = [ex.user_message for ex in examples]
    assert "Actually, cancel this" in messages
    assert "Cancel this" in messages
```

### Criterios de Éxito

- [ ] `CANCELLATION_UTTERANCES` incluye al menos 3 nuevas variantes
- [ ] `cancellation.py` genera ejemplos con las nuevas frases
- [ ] El dataset regenerado incluye estos ejemplos
- [ ] Los tests de dataset pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Verificar que las nuevas frases están en CANCELLATION_UTTERANCES
grep -A 10 "CANCELLATION_UTTERANCES" src/soni/dataset/domains/flight_booking.py

# Verificar generación de ejemplos
uv run python -c "from soni.dataset.patterns.cancellation import CancellationGenerator; from soni.dataset.domains.flight_booking import FLIGHT_BOOKING; gen = CancellationGenerator(); examples = gen.generate_examples(FLIGHT_BOOKING, 'ongoing', 10); print([e.user_message for e in examples])"
```

**Resultado esperado:**
- Las nuevas frases aparecen en `CANCELLATION_UTTERANCES`
- Los ejemplos generados incluyen estas frases
- El dataset puede regenerarse correctamente

### Referencias

- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Análisis completo de tests fallidos
- `tests/integration/test_all_scenarios.py::TestScenario5Cancellation` - Test que debe pasar después
- `src/soni/dataset/domains/flight_booking.py` - Definición de utterances
- `src/soni/dataset/patterns/cancellation.py` - Generador de ejemplos

### Notas Adicionales

- Esta tarea es parte de la Fase 1 del plan de acción para arreglar tests fallidos
- Después de completar esta tarea, se debe ejecutar la tarea 713 (Re-optimizar NLU) para que los cambios surtan efecto
- Verificar que `command` en `NLUOutput` sea consistente con la especificación (puede ser `None` o el nombre del flow actual)
