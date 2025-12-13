## Task: 710 - Add Modification After Confirmation Examples

**ID de tarea:** 710
**Hito:** Fix Integration Test Failures - NLU Dataset Improvements
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Añadir ejemplos al dataset para detectar modificaciones cuando el usuario niega una confirmación y solicita cambiar un slot (ej: "No, change the destination").

### Contexto

**Problema identificado:**
- El test `test_complete_confirmation_flow_no_then_modify` falla con error de validación del NLU
- El mensaje "No, change the destination" no está siendo clasificado correctamente como MODIFICATION
- El dataset actual tiene "Change the destination to X" pero no "No, change the destination" (sin nuevo valor)
- El NLU debe detectar que es una modificación incluso cuando no se proporciona el nuevo valor inmediatamente

**Referencias:**
- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 1.4
- `tests/integration/test_confirmation_flow.py::test_complete_confirmation_flow_no_then_modify`
- `src/soni/dataset/patterns/modification.py` - Generador de ejemplos
- `src/soni/dataset/domains/flight_booking.py` - Contextos de confirmación

### Entregables

- [ ] Se añaden ejemplos de modificación tras negativa de confirmación en `modification.py`
- [ ] Los ejemplos cubren casos con y sin nuevo valor especificado
- [ ] El dataset regenerado incluye estos nuevos ejemplos
- [ ] El NLU puede detectar MODIFICATION en contexto de confirmación

### Implementación Detallada

#### Paso 1: Añadir ejemplos de modificación tras negativa

**Archivo(s) a modificar:** `src/soni/dataset/patterns/modification.py`

**Código específico:**

```python
# En _generate_ongoing_examples para flight_booking:
# Añadir ejemplo de modificación tras negativa de confirmación

# Ejemplo 1: "No, change the destination" (sin nuevo valor)
examples.append(
    ExampleTemplate(
        user_message="No, change the destination",
        conversation_context=create_context_before_confirmation(
            origin="New York",
            destination="Los Angeles",
            departure_date="2025-12-15",
        ),
        expected_output=NLUOutput(
            message_type=MessageType.MODIFICATION,
            command="book_flight",
            slots=[],  # No tiene el nuevo valor aún, solo solicita cambio
            confidence=0.9,
        ),
        domain=domain_config.name,
        pattern="modification",
        context_type="ongoing",
        current_datetime="2024-12-11T10:00:00",
    )
)

# Ejemplo 2: "No, change the origin" (sin nuevo valor)
examples.append(
    ExampleTemplate(
        user_message="No, change the origin",
        conversation_context=create_context_before_confirmation(),
        expected_output=NLUOutput(
            message_type=MessageType.MODIFICATION,
            command="book_flight",
            slots=[],
            confidence=0.9,
        ),
        domain=domain_config.name,
        pattern="modification",
        context_type="ongoing",
        current_datetime="2024-12-11T10:00:00",
    )
)

# Ejemplo 3: "No, change the date" (sin nuevo valor)
examples.append(
    ExampleTemplate(
        user_message="No, change the date",
        conversation_context=create_context_before_confirmation(),
        expected_output=NLUOutput(
            message_type=MessageType.MODIFICATION,
            command="book_flight",
            slots=[],
            confidence=0.9,
        ),
        domain=domain_config.name,
        pattern="modification",
        context_type="ongoing",
        current_datetime="2024-12-11T10:00:00",
    )
)
```

**Explicación:**
- Crear ejemplos donde el usuario niega la confirmación y solicita cambiar un slot específico
- El `conversation_state` debe ser "confirming" o "ready_for_confirmation"
- Los `slots` pueden estar vacíos si el usuario no proporciona el nuevo valor inmediatamente
- El sistema debe detectar MODIFICATION para luego preguntar qué valor nuevo quiere

#### Paso 2: Añadir ejemplos con nuevo valor incluido

**Archivo(s) a modificar:** `src/soni/dataset/patterns/modification.py`

**Código específico:**

```python
# Ejemplo: "No, change the destination to San Francisco" (con nuevo valor)
examples.append(
    ExampleTemplate(
        user_message="No, change the destination to San Francisco",
        conversation_context=create_context_before_confirmation(
            origin="New York",
            destination="Los Angeles",
            departure_date="2025-12-15",
        ),
        expected_output=NLUOutput(
            message_type=MessageType.MODIFICATION,
            command="book_flight",
            slots=[
                SlotValue(name="destination", value="San Francisco", confidence=0.95),
            ],
            confidence=0.95,
        ),
        domain=domain_config.name,
        pattern="modification",
        context_type="ongoing",
        current_datetime="2024-12-11T10:00:00",
    )
)
```

**Explicación:**
- Cubrir también el caso donde el usuario proporciona el nuevo valor en el mismo mensaje
- Esto ayuda al NLU a entender ambos patrones

#### Paso 3: Verificar contexto de confirmación

**Archivo(s) a verificar:** `src/soni/dataset/domains/flight_booking.py`

**Verificaciones:**
- `create_context_before_confirmation()` debe tener `conversation_state="confirming"` o similar
- Si no existe, añadir parámetro para especificar el estado de conversación

**Código esperado:**

```python
def create_context_before_confirmation(
    origin: str = "Madrid",
    destination: str = "Barcelona",
    departure_date: str = "tomorrow",
    conversation_state: str = "confirming",  # ← Añadir si no existe
) -> ConversationContext:
    # ... código existente ...
    # Asegurar que conversation_state está en el contexto
```

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dataset_patterns.py`

**Tests específicos:**

```python
def test_modification_after_confirmation_examples():
    """Test que los ejemplos de modificación incluyen casos tras negativa de confirmación."""
    generator = ModificationGenerator()
    examples = generator.generate_examples(
        domain_config=FLIGHT_BOOKING,
        context_type="ongoing",
        count=10
    )

    # Verificar que hay ejemplos con "No, change"
    messages = [ex.user_message for ex in examples]
    no_change_messages = [m for m in messages if m.lower().startswith("no, change")]
    assert len(no_change_messages) > 0, "Debe haber ejemplos de modificación tras negativa"

    # Verificar que el contexto es de confirmación
    for ex in examples:
        if "no, change" in ex.user_message.lower():
            # El contexto debe indicar que estamos en confirmación
            assert ex.conversation_context.current_flow == "book_flight"
```

### Criterios de Éxito

- [ ] Se añaden al menos 3 ejemplos de modificación tras negativa de confirmación
- [ ] Los ejemplos cubren diferentes slots (origin, destination, date)
- [ ] Los ejemplos incluyen casos con y sin nuevo valor
- [ ] El dataset regenerado incluye estos ejemplos
- [ ] Los tests de dataset pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Verificar que los nuevos ejemplos están en modification.py
grep -A 20 "No, change" src/soni/dataset/patterns/modification.py

# Verificar generación de ejemplos
uv run python -c "from soni.dataset.patterns.modification import ModificationGenerator; from soni.dataset.domains.flight_booking import FLIGHT_BOOKING; gen = ModificationGenerator(); examples = gen.generate_examples(FLIGHT_BOOKING, 'ongoing', 10); print([e.user_message for e in examples])"
```

**Resultado esperado:**
- Los nuevos ejemplos aparecen en `modification.py`
- Los ejemplos incluyen "No, change the [slot]"
- El dataset puede regenerarse correctamente

### Referencias

- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Análisis completo de tests fallidos
- `tests/integration/test_confirmation_flow.py::test_complete_confirmation_flow_no_then_modify` - Test que debe pasar después
- `src/soni/dataset/patterns/modification.py` - Generador de ejemplos
- `src/soni/dataset/domains/flight_booking.py` - Contextos de confirmación

### Notas Adicionales

- Esta tarea es parte de la Fase 1 del plan de acción para arreglar tests fallidos
- El NLU debe poder distinguir entre MODIFICATION (cambiar un slot) y CONFIRMATION negativa (solo decir "No")
- Después de completar esta tarea, se debe ejecutar la tarea 713 (Re-optimizar NLU) para que los cambios surtan efecto
- Verificar que el routing después de detectar MODIFICATION en contexto de confirmación funciona correctamente
