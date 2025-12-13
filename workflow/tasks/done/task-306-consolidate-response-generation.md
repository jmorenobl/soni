## Task: 306 - Consolidate Response Generation Logic

**ID de tarea:** 306
**Hito:** Technical Debt Repayment - LOW
**Dependencias:** Task 304 (ResponseGenerator class created)
**Duración estimada:** 2-3 horas
**Prioridad:** 🟢 LOW - Improves consistency
**Related DEBT:** DEBT-006

### Objetivo

Consolidar la lógica de generación de respuestas duplicada en múltiples nodos (`generate_response.py`, `handle_confirmation.py`, `handle_digression.py`) en la clase `ResponseGenerator` centralizada, eliminando duplicación.

### Contexto

**Duplicación encontrada:**
- `generate_response.py`: Priority-based response generation (lines 28-76)
- `handle_confirmation.py`: `_generate_confirmation_message()` function (lines 313-353)
- `handle_digression.py`: Simple response generation (lines 28-30)

**Problemas:**
- ❌ DRY violation: Similar logic in 3 places
- ⚠️ Consistency: Risk of inconsistent response formats
- ⚠️ Maintenance: Changes require updating multiple files

**Pre-requisito:**
- Task 304 debe completarse primero (crea `ResponseGenerator` class)
- Si Task 304 no está completo, crear `ResponseGenerator` en este task

**Referencias:**
- Technical Debt: `docs/technical-debt.md` (DEBT-006)
- Related: DEBT-004 (generate_response_node SRP)

### Entregables

- [ ] `ResponseGenerator.generate_confirmation()` método agregado
- [ ] `ResponseGenerator.generate_digression()` método agregado
- [ ] `handle_confirmation.py` usa `ResponseGenerator.generate_confirmation()`
- [ ] `handle_digression.py` usa `ResponseGenerator.generate_digression()`
- [ ] `_generate_confirmation_message()` eliminada de handle_confirmation.py
- [ ] Tests actualizados
- [ ] No duplicación de response logic

### Implementación Detallada

#### Paso 1: Extender ResponseGenerator con generate_confirmation

**Archivo a modificar:** `src/soni/utils/response_generator.py`

**Agregar método:**

```python
@staticmethod
def generate_confirmation(
    slots: dict[str, Any],
    step_config: Any | None,
    config: Any,
) -> str:
    """Generate confirmation message with slot values.

    Uses step_config.message template if available, otherwise generates
    default confirmation message listing all slot values.

    Args:
        slots: Dictionary of slot name to value
        step_config: Current step configuration (may be None)
        config: Soni configuration for slot display names

    Returns:
        Confirmation message string

    Examples:
        >>> slots = {"origin": "NYC", "destination": "LAX"}
        >>> msg = ResponseGenerator.generate_confirmation(slots, None, config)
        >>> print(msg)
        Let me confirm:
        - Origin: NYC
        - Destination: LAX

        Is this correct?
    """
    # Try to use template from step config if available
    if step_config and hasattr(step_config, "message") and step_config.message:
        message_str = str(step_config.message)
        # Interpolate slot values in template
        for slot_name, value in slots.items():
            message_str = message_str.replace(f"{{{slot_name}}}", str(value))
        return message_str

    # Default confirmation message
    message = "Let me confirm:\\n"
    for slot_name, value in slots.items():
        # Get display name from slot config if available
        display_name = slot_name
        if hasattr(config, "slots") and config.slots:
            slot_config = config.slots.get(slot_name, {})
            if isinstance(slot_config, dict):
                display_name = slot_config.get("display_name", slot_name)
        message += f"- {display_name}: {value}\\n"
    message += "\\nIs this correct?"

    return message
```

#### Paso 2: Agregar generate_digression method

**Agregar a `ResponseGenerator`:**

```python
@staticmethod
def generate_digression(command: str) -> str:
    """Generate response for digression (question/help).

    Args:
        command: The digression command/question

    Returns:
        Digression response string
    """
    if not command:
        return "I understand you have a question. How can I help?"

    return f"I understand you're asking about {command}. Let me help you with that."
```

#### Paso 3: Actualizar handle_confirmation.py

**Archivo a modificar:** `src/soni/dm/nodes/handle_confirmation.py`

**Agregar import:**
```python
from soni.utils.response_generator import ResponseGenerator
```

**Reemplazar líneas 274-276 (uso de _generate_confirmation_message):**

```python
# BEFORE:
confirmation_message = _generate_confirmation_message(
    flow_slots[flow_id], current_step_config, runtime.context
)

# AFTER:
confirmation_message = ResponseGenerator.generate_confirmation(
    flow_slots[flow_id],
    current_step_config,
    runtime.context["config"]
)
```

**Eliminar función `_generate_confirmation_message` completa (lines 313-353):**

```python
# DELETE ENTIRE FUNCTION:
def _generate_confirmation_message(
    slots: dict[str, Any],
    step_config: Any | None,
    context: Any,
) -> str:
    # ... 40 lines to delete ...
```

#### Paso 4: Actualizar handle_digression.py

**Archivo a modificar:** `src/soni/dm/nodes/handle_digression.py`

**Agregar import:**
```python
from soni.utils.response_generator import ResponseGenerator
```

**Reemplazar líneas 28-30:**

```python
# BEFORE:
response = f"I understand you're asking about {command}. Let me help you with that."

# AFTER:
response = ResponseGenerator.generate_digression(command)
```

#### Paso 5: Verificar que _get_response_template también se centraliza (opcional)

**Nota:** `_get_response_template` aparece duplicado en handle_confirmation y handle_correction.

**Considerar agregar a ResponseGenerator:**

```python
@staticmethod
def get_response_template(
    config: Any,
    template_name: str,
    default_template: str,
    **kwargs: Any,
) -> str:
    """Get response template from config and interpolate variables.

    Args:
        config: SoniConfig instance
        template_name: Name of template in config.responses
        default_template: Default template if not found
        **kwargs: Variables to interpolate

    Returns:
        Interpolated template string
    """
    template = None
    if hasattr(config, "responses") and config.responses:
        template_config = config.responses.get(template_name)
        if template_config:
            if isinstance(template_config, dict):
                template = template_config.get("default")
            elif isinstance(template_config, str):
                template = template_config

    if not template:
        template = default_template

    # Interpolate variables
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"{{{key}}}", str(value))

    return result
```

### Tests Requeridos

**Archivo:** `tests/unit/utils/test_response_generator.py` (extender existente)

```python
class TestGenerateConfirmation:
    """Tests for generate_confirmation method."""

    def test_uses_template_when_available(self):
        """Test uses step_config template when available."""
        slots = {"origin": "NYC", "destination": "LAX"}
        step_config = type('obj', (), {
            'message': 'Confirm {origin} to {destination}?'
        })()
        config = None

        result = ResponseGenerator.generate_confirmation(slots, step_config, config)

        assert result == "Confirm NYC to LAX?"

    def test_generates_default_confirmation(self):
        """Test generates default confirmation when no template."""
        slots = {"origin": "NYC", "destination": "LAX"}
        step_config = None
        config = type('obj', (), {'slots': None})()

        result = ResponseGenerator.generate_confirmation(slots, step_config, config)

        assert "Let me confirm:" in result
        assert "origin: NYC" in result or "Origin: NYC" in result
        assert "destination: LAX" in result or "Destination: LAX" in result
        assert "Is this correct?" in result

    def test_uses_display_names_from_config(self):
        """Test uses display names from config."""
        slots = {"origin": "NYC"}
        step_config = None
        config = type('obj', (), {
            'slots': {
                "origin": {"display_name": "Departure City"}
            }
        })()

        result = ResponseGenerator.generate_confirmation(slots, step_config, config)

        assert "Departure City: NYC" in result


class TestGenerateDigression:
    """Tests for generate_digression method."""

    def test_generates_digression_with_command(self):
        """Test generates response with command."""
        result = ResponseGenerator.generate_digression("status")

        assert "status" in result.lower()
        assert "help" in result.lower() or "asking" in result.lower()

    def test_generates_default_when_no_command(self):
        """Test generates default when command is empty."""
        result = ResponseGenerator.generate_digression("")

        assert "question" in result.lower()
        assert "help" in result.lower()
```

### Criterios de Éxito

- [ ] `ResponseGenerator.generate_confirmation()` implemented and tested
- [ ] `ResponseGenerator.generate_digression()` implemented and tested
- [ ] `handle_confirmation.py` uses ResponseGenerator (not local function)
- [ ] `handle_digression.py` uses ResponseGenerator
- [ ] `_generate_confirmation_message()` deleted from handle_confirmation.py
- [ ] No duplicated response generation logic
- [ ] All tests pass
- [ ] Mypy passes
- [ ] Ruff passes

### Validación Manual

```bash
# 1. Verify no duplicated _generate_confirmation_message
grep -r "_generate_confirmation_message" src/soni/dm/nodes/ && echo "❌ Found duplicate" || echo "✅ No duplicate"

# 2. Run tests
uv run pytest tests/unit/utils/test_response_generator.py -v
uv run pytest tests/unit/dm/nodes/test_handle_confirmation.py -v
uv run pytest tests/unit/dm/nodes/test_handle_digression.py -v

# 3. Type and lint check
uv run mypy src/soni
uv run ruff check src/
```

### Referencias

- **Technical Debt:** `docs/technical-debt.md` (DEBT-006)
- **DRY Principle:** "The Pragmatic Programmer" by Hunt & Thomas
- **Related:** DEBT-004 (generate_response_node SRP)
- **Files:** `generate_response.py`, `handle_confirmation.py`, `handle_digression.py`

### Notas Adicionales

**Dependency on Task 304:**
- If Task 304 is complete, extend existing `ResponseGenerator`
- If Task 304 not complete, create `ResponseGenerator` in this task

**Benefits:**
- Single place to modify response generation
- Consistent response formatting
- Easier to add response variations/templates
- Centralized response logic makes testing easier

**Future Improvements:**
- Add support for response templates in YAML
- Add support for response variations (random selection)
- Add support for internationalization (i18n)
- All improvements in ONE place (ResponseGenerator)
