## Task: 712 - Verify and Expand Relative Dates Examples

**ID de tarea:** 712
**Hito:** Fix Integration Test Failures - NLU Dataset Improvements
**Dependencias:** Ninguna
**Duración estimada:** 1-2 horas

### Objetivo

Verificar y ampliar los ejemplos de fechas relativas en el dataset para asegurar que el NLU puede extraer correctamente slots de tipo fecha de frases como "Next Friday", "Tomorrow", "Next week".

### Contexto

**Problema identificado:**
- El test `test_e2e_flight_booking_complete_flow` falla porque después de proporcionar "Next Friday", el sistema pregunta por la fecha de nuevo
- Esto sugiere que el NLU no está extrayendo correctamente el slot `departure_date` de fechas relativas
- Necesitamos verificar que hay suficientes ejemplos de fechas relativas en el dataset

**Referencias:**
- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 1.5
- `tests/integration/test_e2e.py::test_e2e_flight_booking_complete_flow`
- `src/soni/dataset/domains/flight_booking.py` - `DATES_RELATIVE`
- `src/soni/dataset/patterns/slot_value.py` - Generador de ejemplos de slots

### Entregables

- [ ] Se verifica que `DATES_RELATIVE` incluye suficientes variantes
- [ ] Se verifica que los ejemplos de `slot_value.py` incluyen fechas relativas
- [ ] Se añaden ejemplos adicionales si es necesario
- [ ] Los ejemplos incluyen `current_datetime` para normalización

### Implementación Detallada

#### Paso 1: Verificar DATES_RELATIVE

**Archivo(s) a verificar:** `src/soni/dataset/domains/flight_booking.py`

**Código actual:**

```python
DATES_RELATIVE = [
    "tomorrow",
    "next Monday",
    "next week",
    "in two weeks",
    "next month",
]
```

**Verificaciones:**
- ¿Incluye "Next Friday"? (usado en el test)
- ¿Incluye suficientes variantes?
- ¿Están en formato consistente?

**Código esperado (si necesita ampliarse):**

```python
DATES_RELATIVE = [
    "tomorrow",
    "Tomorrow",  # Variante con mayúscula
    "next Monday",
    "Next Monday",  # Variante con mayúscula
    "next Friday",
    "Next Friday",  # ← Añadir si no existe
    "next week",
    "Next week",  # Variante con mayúscula
    "in two weeks",
    "next month",
    "the day after tomorrow",
    "in 3 days",
    "this Friday",
    "This Friday",
]
```

#### Paso 2: Verificar ejemplos en slot_value.py

**Archivo(s) a verificar:** `src/soni/dataset/patterns/slot_value.py`

**Verificaciones:**
- ¿Los ejemplos de `departure_date` usan `DATES_RELATIVE`?
- ¿Los ejemplos incluyen `current_datetime`?
- ¿Hay suficientes ejemplos con diferentes fechas relativas?

**Código esperado:**

```python
# En slot_value.py, ejemplos de departure_date deben:
1. Usar fechas de DATES_RELATIVE
2. Incluir current_datetime en el ExampleTemplate
3. Tener expected_slots con el slot normalizado (fecha ISO o similar)
```

#### Paso 3: Añadir ejemplos adicionales si es necesario

**Archivo(s) a modificar:** `src/soni/dataset/patterns/slot_value.py`

**Código específico (si falta):**

```python
# Añadir ejemplo específico con "Next Friday"
examples.append(
    ExampleTemplate(
        user_message="Next Friday",
        conversation_context=ConversationContext(
            history=dspy.History(messages=[...]),
            current_slots={"origin": "New York", "destination": "Los Angeles"},
            current_flow="book_flight",
            expected_slots=["departure_date"],
            current_prompted_slot="departure_date",
            conversation_state="waiting_for_slot",
        ),
        expected_output=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command=None,
            slots=[
                SlotValue(
                    name="departure_date",
                    value="2025-12-19",  # Valor normalizado (ejemplo)
                    confidence=0.95,
                ),
            ],
            confidence=0.95,
        ),
        domain=domain_config.name,
        pattern="slot_value",
        context_type="ongoing",
        current_datetime="2025-12-11T10:00:00",  # ← CRÍTICO para normalización
    )
)
```

**Explicación:**
- Asegurar que `current_datetime` está presente para normalización
- El valor esperado debe ser normalizado (fecha ISO)
- Incluir diferentes fechas relativas para entrenar al NLU

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dataset_patterns.py`

**Tests específicos:**

```python
def test_slot_value_examples_include_relative_dates():
    """Test que los ejemplos de slot_value incluyen fechas relativas."""
    generator = SlotValueGenerator()
    examples = generator.generate_examples(
        domain_config=FLIGHT_BOOKING,
        context_type="ongoing",
        count=20
    )

    # Verificar que hay ejemplos con departure_date
    date_examples = [
        ex for ex in examples
        if any(slot.name == "departure_date" for slot in ex.expected_output.slots)
    ]
    assert len(date_examples) > 0, "Debe haber ejemplos de departure_date"

    # Verificar que incluyen current_datetime
    for ex in date_examples:
        assert hasattr(ex, "current_datetime"), "Ejemplos de fecha deben tener current_datetime"
        assert ex.current_datetime, "current_datetime no debe estar vacío"

    # Verificar que hay ejemplos con "Next Friday"
    next_friday_examples = [
        ex for ex in date_examples
        if "next friday" in ex.user_message.lower() or "next Friday" in ex.user_message
    ]
    assert len(next_friday_examples) > 0, "Debe haber ejemplos con 'Next Friday'"
```

### Criterios de Éxito

- [ ] `DATES_RELATIVE` incluye "Next Friday" y variantes
- [ ] Los ejemplos de `slot_value.py` incluyen fechas relativas
- [ ] Todos los ejemplos de fecha incluyen `current_datetime`
- [ ] Los valores esperados están normalizados (fechas ISO)
- [ ] Los tests de dataset pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Verificar DATES_RELATIVE
grep -A 10 "DATES_RELATIVE" src/soni/dataset/domains/flight_booking.py

# Verificar ejemplos de slot_value con fechas
grep -B 5 -A 10 "departure_date" src/soni/dataset/patterns/slot_value.py

# Verificar que current_datetime está presente
grep "current_datetime" src/soni/dataset/patterns/slot_value.py
```

**Resultado esperado:**
- `DATES_RELATIVE` incluye "Next Friday"
- Los ejemplos incluyen `current_datetime`
- Los valores esperados están normalizados

### Referencias

- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Análisis completo de tests fallidos
- `tests/integration/test_e2e.py::test_e2e_flight_booking_complete_flow` - Test que debe pasar después
- `src/soni/dataset/domains/flight_booking.py` - `DATES_RELATIVE`
- `src/soni/dataset/patterns/slot_value.py` - Generador de ejemplos de slots
- `src/soni/du/normalizer.py` - Normalización de fechas

### Notas Adicionales

- Esta tarea es parte de la Fase 1 del plan de acción para arreglar tests fallidos
- `current_datetime` es crítico para normalizar fechas relativas
- El valor esperado debe ser normalizado (fecha ISO) para que el NLU aprenda correctamente
- Después de completar esta tarea, se debe ejecutar la tarea 713 (Re-optimizar NLU) para que los cambios surtan efecto
- Verificar que el normalizador de fechas funciona correctamente con `current_datetime`
