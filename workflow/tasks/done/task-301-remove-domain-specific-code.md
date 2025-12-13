## Task: 301 - Remove Domain-Specific Code from Framework (CRITICAL)

**ID de tarea:** 301
**Hito:** Technical Debt Repayment - CRITICAL
**Dependencias:** Ninguna
**Duración estimada:** 1-2 horas
**Prioridad:** 🔴🔴 CRITICAL - Must fix before next commit
**Related DEBT:** DEBT-007

### Objetivo

Eliminar completamente todas las referencias hardcodeadas a conceptos específicos del dominio de booking (reservas de vuelos) del código del framework, garantizando que el framework sea 100% domain-agnostic y reutilizable para cualquier dominio (restaurantes, hoteles, citas médicas, etc.).

### Contexto

**Problema Crítico Encontrado:**
El framework contiene código hardcodeado específico del dominio de flight booking:
1. `generate_response.py` tiene lógica específica para slot "booking_ref"
2. `validators.py` tiene validador "booking_reference" en el registro del framework

**Violación Arquitectural:**
Esto viola el principio fundamental de **Zero-Leakage (Hexagonal Architecture)** documentado en `.cursor/rules/001-architecture.mdc`:
- YAML describes WHAT (domain-specific)
- Python implements HOW (domain-agnostic)

**Impacto:**
- Framework NO puede usarse para otros dominios
- Confusión entre framework code y application code
- Violación de OCP (Open/Closed Principle)
- Reduce valor del framework significativamente

**Referencias:**
- Technical Debt: `docs/technical-debt.md` (DEBT-007)
- Architecture Rules: `.cursor/rules/001-architecture.mdc`
- YAML DSL: `.cursor/rules/007-yaml-dsl.mdc`

### Entregables

- [ ] `generate_response.py` eliminado código hardcodeado de "booking_ref"
- [ ] `validate_booking_ref` movido de framework a ejemplo
- [ ] Nuevo archivo `examples/flight_booking/validators.py` creado
- [ ] `examples/flight_booking/soni.yaml` actualizado con custom validator
- [ ] Audit completo: ZERO referencias a "booking" en `src/soni/`
- [ ] Todos los tests actualizados y pasando
- [ ] Framework puede generar respuestas para CUALQUIER dominio

### Implementación Detallada

#### Paso 1: Eliminar hardcoded "booking_ref" de generate_response.py

**Archivo a modificar:** `src/soni/dm/nodes/generate_response.py`

**Código actual (INCORRECTO):**

```python
# Lines 42-44
elif "booking_ref" in slots and slots["booking_ref"]:
    response = f"Booking confirmed! Your reference is: {slots['booking_ref']}"
    logger.info("Using booking_ref to generate response")
```

**Código correcto (REEMPLAZAR CON):**

```python
# Remove this entire elif block (lines 42-44)
# Response generation should be purely generic:
# 1. Check "confirmation" slot (set by ANY action)
# 2. Check action_result.message
# 3. Check existing last_response
# 4. Default fallback

# The logic should flow directly from line 41 to line 45 (else block)
```

**Explicación:**
- El framework NO DEBE conocer nombres de slots específicos como "booking_ref"
- Las acciones (actions) deben escribir su mensaje en el slot genérico "confirmation"
- Si una action quiere retornar una confirmación, debe usar `action_result.message` o escribir en slot "confirmation"
- El framework solo lee slots genéricos, nunca slots específicos de dominio

**Actualizar también el comentario en línea 34:**

```python
# BEFORE (line 34):
# 1. Action results (booking_ref, confirmation from actions) - highest priority

# AFTER:
# 1. Action results (confirmation slot or action_result.message) - highest priority
```

**Actualizar logger.warning en línea 73:**

```python
# BEFORE:
logger.warning(
    "No confirmation, booking_ref, action_result, or existing response found, "
    "using default response"
)

# AFTER:
logger.warning(
    "No confirmation slot, action_result, or existing response found, "
    "using default response"
)
```

#### Paso 2: Mover validate_booking_ref de framework a ejemplo

**Archivo a modificar:** `src/soni/validation/validators.py`

**Código a ELIMINAR completamente (lines 67-82 aproximadamente):**

```python
@ValidatorRegistry.register("booking_reference")
def validate_booking_ref(value: str) -> bool:
    """
    Validate booking reference format.

    Args:
        value: Booking reference to validate

    Returns:
        True if valid booking reference, False otherwise
    """
    if not isinstance(value, str):
        return False
    # Booking reference: 6 alphanumeric characters
    return bool(re.match(r"^[A-Z0-9]{6}$", value))
```

**Explicación:**
- Este validador es ESPECÍFICO del dominio de flight booking
- NO pertenece al framework genérico
- Debe moverse al código de la aplicación (ejemplo)

#### Paso 3: Crear validators.py en el ejemplo de flight_booking

**Archivo a crear:** `examples/flight_booking/validators.py`

**Código completo:**

```python
"""Domain-specific validators for flight booking example.

This module contains validators specific to the flight booking domain.
These are NOT part of the Soni framework - they are application-level validators.
"""

import re


def validate_booking_ref(value: str) -> bool:
    """
    Validate booking reference format for flight bookings.

    This is a domain-specific validator for the flight booking example.
    Different domains will have different reference formats.

    Args:
        value: Booking reference to validate

    Returns:
        True if valid booking reference (6 alphanumeric characters), False otherwise

    Examples:
        >>> validate_booking_ref("ABC123")
        True
        >>> validate_booking_ref("XYZ789")
        True
        >>> validate_booking_ref("abc123")  # lowercase not allowed
        False
        >>> validate_booking_ref("AB12")  # too short
        False
    """
    if not isinstance(value, str):
        return False
    # Booking reference: 6 uppercase alphanumeric characters
    return bool(re.match(r"^[A-Z0-9]{6}$", value))


def validate_passenger_count(value: int) -> bool:
    """
    Validate passenger count for flight booking.

    Domain-specific rule: Most commercial flights support 1-9 passengers per booking.

    Args:
        value: Number of passengers

    Returns:
        True if valid passenger count (1-9), False otherwise
    """
    if not isinstance(value, int):
        return False
    return 1 <= value <= 9
```

**Explicación:**
- Este archivo contiene validadores ESPECÍFICOS del dominio de flight booking
- Está claramente separado del framework (en `examples/`)
- Puede servir como referencia para otros dominios
- Incluye docstrings que explican que son domain-specific

#### Paso 4: Actualizar YAML del ejemplo para usar custom validator

**Archivo a modificar:** `examples/flight_booking/soni.yaml`

**Buscar la definición del slot `booking_ref` y actualizar:**

```yaml
# BEFORE:
slots:
  booking_ref:
    type: str
    description: "Booking reference number"
    validator: booking_reference  # <- This refers to framework validator (WRONG)

# AFTER:
slots:
  booking_ref:
    type: str
    description: "Booking reference number (6 uppercase alphanumeric characters)"
    validator:
      type: custom
      module: validators  # Relative to examples/flight_booking/
      function: validate_booking_ref
```

**Explicación:**
- El YAML ahora referencia un validador custom en el código de la aplicación
- El framework no necesita conocer qué es un "booking_ref"
- Otros dominios definirán sus propios validadores custom

#### Paso 5: Actualizar action para usar slot "confirmation" genérico

**Archivo a modificar:** `examples/flight_booking/actions.py`

**Buscar la función `book_flight` y verificar que use slot genérico "confirmation":**

```python
async def book_flight(slots: dict[str, Any], context: RuntimeContext) -> dict[str, Any]:
    """Book a flight with provided details."""
    # ... existing logic ...

    booking_ref = generate_booking_reference()

    # IMPORTANT: Set the confirmation message in GENERIC "confirmation" slot
    # This allows generate_response.py to work for ANY domain
    return {
        "booking_ref": booking_ref,  # Domain-specific slot
        "confirmation": f"Booking confirmed! Your reference is: {booking_ref}",  # Generic slot
        "success": True
    }
```

**Explicación:**
- Las actions siempre deben escribir su mensaje en el slot genérico "confirmation"
- También pueden escribir en slots específicos del dominio (booking_ref)
- Pero el framework solo lee el slot genérico "confirmation"

#### Paso 6: Audit completo del framework

**Comando para verificar:**

```bash
# Buscar TODAS las referencias a "booking" en el framework
grep -r "booking" src/soni/ --exclude-dir=__pycache__

# Buscar hardcoded slot names (potential violations)
grep -r "\"[a-z_]*_ref\"" src/soni/ --exclude-dir=__pycache__
grep -r "\"origin\"" src/soni/ --exclude-dir=__pycache__
grep -r "\"destination\"" src/soni/ --exclude-dir=__pycache__
grep -r "\"flight\"" src/soni/ --exclude-dir=__pycache__
```

**Resultado esperado:**
- ZERO referencias a "booking" excepto en comentarios/docstrings como EJEMPLOS
- ZERO hardcoded slot names específicos de dominio
- Solo referencias genéricas como "confirmation", "slots", "metadata"

**Si se encuentran referencias:**
- En comentarios/docstrings: OK si son ejemplos genéricos
- En código: ELIMINAR o hacer genérico

### Tests Requeridos

**Archivo de tests:** `tests/unit/dm/nodes/test_generate_response.py`

**Tests específicos a implementar:**

```python
import pytest
from soni.dm.nodes.generate_response import generate_response_node
from soni.core.types import DialogueState


@pytest.mark.asyncio
async def test_generate_response_uses_confirmation_slot_generic():
    """Test that generate_response uses generic 'confirmation' slot, not domain-specific slots."""
    # Arrange
    state: DialogueState = {
        "user_message": "book a flight",
        "last_response": "",
        "messages": [],
        "flow_stack": [{"flow_id": "test_flow", "flow_name": "test"}],
        "flow_slots": {
            "test_flow": {
                "confirmation": "Order confirmed! Reference: XYZ789",  # Generic slot
                "order_ref": "XYZ789",  # Domain-specific slot (should be ignored)
            }
        },
        "conversation_state": "completed",
        # ... other required fields
    }
    runtime = MockRuntime()

    # Act
    result = await generate_response_node(state, runtime)

    # Assert
    assert result["last_response"] == "Order confirmed! Reference: XYZ789"
    # Should use confirmation slot, NOT domain-specific slot


@pytest.mark.asyncio
async def test_generate_response_no_hardcoded_slot_names():
    """Test that generate_response doesn't check for hardcoded slot names like 'booking_ref'."""
    # Arrange
    state: DialogueState = {
        "user_message": "test",
        "last_response": "",
        "messages": [],
        "flow_stack": [{"flow_id": "test_flow", "flow_name": "test"}],
        "flow_slots": {
            "test_flow": {
                "booking_ref": "ABC123",  # Framework should NOT look for this
                "reservation_id": "XYZ789",  # Or this
                # No "confirmation" slot
            }
        },
        "conversation_state": "idle",
        # ... other required fields
    }
    runtime = MockRuntime()

    # Act
    result = await generate_response_node(state, runtime)

    # Assert
    # Should fall back to default, NOT use booking_ref or reservation_id
    assert result["last_response"] == "How can I help you?"


@pytest.mark.asyncio
async def test_generate_response_works_for_any_domain():
    """Test that response generation is truly domain-agnostic."""
    # Arrange - Simulate restaurant booking domain
    state: DialogueState = {
        "user_message": "book a table",
        "last_response": "",
        "messages": [],
        "flow_stack": [{"flow_id": "restaurant_flow", "flow_name": "book_table"}],
        "flow_slots": {
            "restaurant_flow": {
                "confirmation": "Table reserved! Confirmation code: TBL456",  # Generic
                "table_number": "12",  # Domain-specific (restaurant)
                "party_size": "4",  # Domain-specific (restaurant)
            }
        },
        "conversation_state": "completed",
        # ... other required fields
    }
    runtime = MockRuntime()

    # Act
    result = await generate_response_node(state, runtime)

    # Assert
    assert result["last_response"] == "Table reserved! Confirmation code: TBL456"
    # Works for restaurant domain without any framework changes!
```

**Archivo de tests:** `tests/unit/validation/test_validators.py`

```python
import pytest
from soni.validation.validators import ValidatorRegistry


def test_no_domain_specific_validators_in_registry():
    """Test that framework validator registry contains NO domain-specific validators."""
    # Arrange
    registry_validators = ValidatorRegistry.list_validators()

    # Assert - Framework should only have GENERIC validators
    domain_specific_keywords = [
        "booking",
        "flight",
        "hotel",
        "restaurant",
        "reservation",
        "passenger",
        "table",
    ]

    for validator_name in registry_validators:
        for keyword in domain_specific_keywords:
            assert keyword not in validator_name.lower(), (
                f"Domain-specific validator '{validator_name}' found in framework registry! "
                f"Move to application code (examples/)."
            )


def test_framework_validators_are_generic():
    """Test that all framework validators are truly generic."""
    # Arrange
    expected_generic_validators = [
        "email",
        "url",
        "phone",
        "date",
        "time",
        "datetime",
        "integer",
        "float",
        "boolean",
        "string",
        "regex",
        "range",
        "length",
        "enum",
        "airport_code",  # Generic: any 3-letter code (not just airports!)
    ]

    # Act
    registry_validators = ValidatorRegistry.list_validators()

    # Assert
    for validator_name in expected_generic_validators:
        assert validator_name in registry_validators, (
            f"Expected generic validator '{validator_name}' not found in registry"
        )
```

**Archivo de tests para ejemplo:** `examples/flight_booking/test_validators.py`

```python
"""Tests for flight booking domain-specific validators."""

import pytest
from validators import validate_booking_ref, validate_passenger_count


def test_validate_booking_ref_valid():
    """Test booking ref validation with valid references."""
    assert validate_booking_ref("ABC123") is True
    assert validate_booking_ref("XYZ789") is True
    assert validate_booking_ref("000000") is True


def test_validate_booking_ref_invalid_length():
    """Test booking ref validation rejects wrong length."""
    assert validate_booking_ref("ABC") is False  # Too short
    assert validate_booking_ref("ABCD1234") is False  # Too long


def test_validate_booking_ref_invalid_characters():
    """Test booking ref validation rejects invalid characters."""
    assert validate_booking_ref("abc123") is False  # Lowercase
    assert validate_booking_ref("ABC-123") is False  # Special chars


def test_validate_booking_ref_invalid_type():
    """Test booking ref validation rejects non-strings."""
    assert validate_booking_ref(123456) is False
    assert validate_booking_ref(None) is False


def test_validate_passenger_count_valid():
    """Test passenger count validation with valid counts."""
    assert validate_passenger_count(1) is True
    assert validate_passenger_count(4) is True
    assert validate_passenger_count(9) is True


def test_validate_passenger_count_invalid():
    """Test passenger count validation rejects invalid counts."""
    assert validate_passenger_count(0) is False  # Too low
    assert validate_passenger_count(10) is False  # Too high
    assert validate_passenger_count(-1) is False  # Negative
```

### Criterios de Éxito

- [ ] ZERO occurrences of "booking" in `src/soni/` (except comments as examples)
- [ ] ZERO hardcoded domain-specific slot names in framework code
- [ ] `validate_booking_ref` removed from `src/soni/validation/validators.py`
- [ ] `examples/flight_booking/validators.py` created with domain validators
- [ ] `examples/flight_booking/soni.yaml` uses custom validator reference
- [ ] `generate_response.py` uses only generic response sources
- [ ] Framework can generate responses for ANY domain (demonstrated with test)
- [ ] All existing tests pass
- [ ] New tests for domain-agnostic behavior pass
- [ ] Linting pasa sin errores (`uv run ruff check src/`)
- [ ] Type checking pasa sin errores (`uv run mypy src/soni`)
- [ ] Example still works correctly with custom validator

### Validación Manual

**Comandos para validar:**

```bash
# 1. Audit: Verify NO domain references in framework
grep -r "booking" src/soni/ --exclude-dir=__pycache__ || echo "✅ No 'booking' found"
grep -r "flight" src/soni/ --exclude-dir=__pycache__ --exclude="*.md" || echo "✅ No 'flight' found"

# 2. Run tests
uv run pytest tests/unit/dm/nodes/test_generate_response.py -v
uv run pytest tests/unit/validation/test_validators.py -v
uv run pytest examples/flight_booking/test_validators.py -v

# 3. Run example to verify it still works
cd examples/flight_booking
uv run python -m pytest test_validators.py -v

# 4. Lint and type check
uv run ruff check src/ examples/
uv run mypy src/soni

# 5. Integration test: verify framework works for different domain
# Create a simple test with restaurant booking (different domain)
```

**Resultado esperado:**
- All grep commands return empty (no domain-specific references)
- All tests pass
- Example still works with custom validators
- Framework code has ZERO knowledge of booking domain
- Framework can be used for restaurant, hotel, medical, or ANY domain

### Referencias

- **Technical Debt Document:** `docs/technical-debt.md` (DEBT-007)
- **Architecture Principles:** `.cursor/rules/001-architecture.mdc` (Zero-Leakage, Hexagonal)
- **YAML DSL Specification:** `.cursor/rules/007-yaml-dsl.mdc`
- **CLAUDE.md:** Framework Principles section
- **Validator Registry:** `src/soni/validation/validators.py`
- **Example Actions:** `examples/flight_booking/actions.py`

### Notas Adicionales

**Edge Cases:**

1. **Comentarios y Docstrings:**
   - OK tener "booking" en ejemplos de docstrings
   - Ejemplo: `"""Generate response. Example: 'Booking confirmed!'"""`
   - Pero NO en código ejecutable

2. **Tests del Framework:**
   - Tests pueden usar dominios de ejemplo (booking, restaurant, etc.)
   - Pero el framework NO debe depender de esos dominios
   - Los tests deben demostrar que funciona con CUALQUIER dominio

3. **Validadores Genéricos vs Específicos:**
   - **Genérico:** `email`, `url`, `date`, `airport_code` (3 letras)
   - **Específico:** `booking_reference` (formato específico de una airline)
   - Si duda: moverlo a aplicación, no a framework

4. **Migración para Usuarios Existentes:**
   - Si alguien está usando el framework, necesitará:
     1. Crear su propio `validators.py` en su aplicación
     2. Actualizar YAML para referenciar custom validators
     3. Actualizar actions para usar slot "confirmation" genérico
   - Documentar esto en CHANGELOG/MIGRATION.md

5. **Confirmación en Actions:**
   - TODAS las actions deben retornar su mensaje final en slot "confirmation"
   - Slot "confirmation" es el ÚNICO slot genérico que framework lee
   - Actions pueden retornar slots adicionales específicos del dominio
   - Pero framework no debe leerlos directamente en generate_response

**Principio a Seguir:**
> "El framework es como un motor de coche genérico. No debe saber si está en un taxi, ambulancia o coche de policía. El dominio (booking, restaurant, etc.) es la aplicación construida sobre el motor."
