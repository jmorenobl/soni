## Task: 711 - Add Unclear Confirmation Examples

**ID de tarea:** 711
**Hito:** Fix Integration Test Failures - NLU Dataset Improvements
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Añadir ejemplos al dataset para detectar respuestas ambiguas durante confirmaciones (ej: "hmm, I'm not sure", "maybe", "I don't know") y manejarlas correctamente.

### Contexto

**Problema identificado:**
- Los tests `test_confirmation_unclear_then_yes` y `test_confirmation_max_retries` fallan
- El NLU no detecta correctamente respuestas ambiguas durante confirmaciones
- El dataset actual solo tiene respuestas claras: "Yes", "No", "That's right", etc.
- Faltan ejemplos de respuestas poco claras que requieren re-prompt

**Referencias:**
- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Secciones 1.3 y 1.4
- `tests/integration/test_confirmation_flow.py::test_confirmation_unclear_then_yes`
- `tests/integration/test_confirmation_flow.py::test_confirmation_max_retries`
- `src/soni/dataset/patterns/confirmation.py` - Generador de ejemplos
- `src/soni/dataset/domains/flight_booking.py` - CONFIRMATION_POSITIVE/NEGATIVE

### Entregables

- [ ] Se añade `CONFIRMATION_UNCLEAR` a `flight_booking.py`
- [ ] Se añaden ejemplos de confirmaciones ambiguas en `confirmation.py`
- [ ] Los ejemplos tienen `confirmation_value=None` para indicar ambigüedad
- [ ] El dataset regenerado incluye estos nuevos ejemplos

### Implementación Detallada

#### Paso 1: Añadir CONFIRMATION_UNCLEAR

**Archivo(s) a modificar:** `src/soni/dataset/domains/flight_booking.py`

**Código específico:**

```python
CONFIRMATION_POSITIVE = [
    "Yes",
    "Correct",
    "That's right",
    "Yes, that looks good",
    "Confirmed",
    "Yeah",
]

CONFIRMATION_NEGATIVE = [
    "No",
    "That's wrong",
    "No, that's not right",
    "Incorrect",
    "Nope",
]

CONFIRMATION_UNCLEAR = [  # ← NUEVO
    "hmm, I'm not sure",
    "maybe",
    "hmm",
    "I don't know",
    "I'm not sure",
    "Let me think",
    "Not really sure",
    "I guess so",
    "Perhaps",
    "Kind of",
]
```

**Explicación:**
- Crear nueva lista de frases ambiguas
- Estas frases deben resultar en `confirmation_value=None` en el NLUOutput
- El sistema debe re-preguntar cuando detecta ambigüedad

#### Paso 2: Añadir ejemplos en confirmation.py

**Archivo(s) a modificar:** `src/soni/dataset/patterns/confirmation.py`

**Código específico:**

```python
# En _generate_ongoing_examples para flight_booking:
from soni.dataset.domains.flight_booking import (
    CONFIRMATION_NEGATIVE,
    CONFIRMATION_POSITIVE,
    CONFIRMATION_UNCLEAR,  # ← NUEVO
    create_context_before_confirmation,
)

# Añadir ejemplos de confirmaciones ambiguas
for unclear_phrase in CONFIRMATION_UNCLEAR[:5]:  # Primeros 5 para no exceder count
    examples.append(
        ExampleTemplate(
            user_message=unclear_phrase,
            conversation_context=create_context_before_confirmation(),
            expected_output=NLUOutput(
                message_type=MessageType.CONFIRMATION,
                command="book_flight",
                slots=[],
                confidence=0.7,  # Menor confianza para respuestas ambiguas
                confirmation_value=None,  # ← CRÍTICO: None indica ambigüedad
            ),
            domain=domain_config.name,
            pattern="confirmation",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )
```

**Explicación:**
- Crear ejemplos con `confirmation_value=None` para indicar ambigüedad
- Usar menor confianza (0.7) para reflejar la incertidumbre
- El sistema debe detectar CONFIRMATION pero con `confirmation_value=None`
- Esto permite al sistema re-preguntar en lugar de procesar como sí/no

#### Paso 3: Verificar manejo de confirmation_value=None

**Archivo(s) a verificar:** `src/soni/dm/nodes/handle_confirmation.py`

**Verificaciones:**
- El nodo debe manejar `confirmation_value=None` correctamente
- Debe re-preguntar cuando es `None`
- Debe incrementar contador de reintentos

**Código esperado:**

```python
# En handle_confirmation.py:
confirmation_value = nlu_result.get("confirmation_value")

if confirmation_value is None:
    # Respuesta ambigua - re-preguntar
    retry_count = state.get("confirmation_retry_count", 0) + 1
    if retry_count >= max_retries:
        # Error después de max reintentos
        return {"conversation_state": "error", ...}
    return {
        "confirmation_retry_count": retry_count,
        "last_response": "I didn't quite understand. Please answer yes or no.",
        ...
    }
```

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dataset_patterns.py`

**Tests específicos:**

```python
def test_confirmation_unclear_examples():
    """Test que los ejemplos de confirmación incluyen respuestas ambiguas."""
    generator = ConfirmationGenerator()
    examples = generator.generate_examples(
        domain_config=FLIGHT_BOOKING,
        context_type="ongoing",
        count=10
    )

    # Verificar que hay ejemplos con confirmation_value=None
    unclear_examples = [
        ex for ex in examples
        if ex.expected_output.confirmation_value is None
    ]
    assert len(unclear_examples) > 0, "Debe haber ejemplos de confirmaciones ambiguas"

    # Verificar que los mensajes son ambiguos
    unclear_messages = [ex.user_message for ex in unclear_examples]
    assert any("not sure" in m.lower() or "maybe" in m.lower() for m in unclear_messages)
```

### Criterios de Éxito

- [ ] `CONFIRMATION_UNCLEAR` está definido con al menos 5 frases
- [ ] Se añaden al menos 3 ejemplos de confirmaciones ambiguas en `confirmation.py`
- [ ] Todos los ejemplos ambiguos tienen `confirmation_value=None`
- [ ] El dataset regenerado incluye estos ejemplos
- [ ] Los tests de dataset pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Verificar que CONFIRMATION_UNCLEAR está definido
grep -A 10 "CONFIRMATION_UNCLEAR" src/soni/dataset/domains/flight_booking.py

# Verificar que los ejemplos incluyen confirmation_value=None
grep -B 5 -A 5 "confirmation_value=None" src/soni/dataset/patterns/confirmation.py

# Verificar generación de ejemplos
uv run python -c "from soni.dataset.patterns.confirmation import ConfirmationGenerator; from soni.dataset.domains.flight_booking import FLIGHT_BOOKING; gen = ConfirmationGenerator(); examples = gen.generate_examples(FLIGHT_BOOKING, 'ongoing', 10); unclear = [e for e in examples if e.expected_output.confirmation_value is None]; print(f'Unclear examples: {len(unclear)}')"
```

**Resultado esperado:**
- `CONFIRMATION_UNCLEAR` está definido
- Los ejemplos incluyen `confirmation_value=None`
- El dataset puede regenerarse correctamente

### Referencias

- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Análisis completo de tests fallidos
- `tests/integration/test_confirmation_flow.py::test_confirmation_unclear_then_yes` - Test que debe pasar después
- `tests/integration/test_confirmation_flow.py::test_confirmation_max_retries` - Test que debe pasar después
- `src/soni/dataset/patterns/confirmation.py` - Generador de ejemplos
- `src/soni/dataset/domains/flight_booking.py` - Definición de utterances
- `src/soni/dm/nodes/handle_confirmation.py` - Manejo de confirmaciones

### Notas Adicionales

- Esta tarea es parte de la Fase 1 del plan de acción para arreglar tests fallidos
- `confirmation_value=None` es crítico para indicar ambigüedad
- El sistema debe re-preguntar cuando detecta `confirmation_value=None`
- Después de completar esta tarea, se debe ejecutar la tarea 713 (Re-optimizar NLU) para que los cambios surtan efecto
- Verificar que `handle_confirmation` maneja correctamente `confirmation_value=None` y los reintentos
