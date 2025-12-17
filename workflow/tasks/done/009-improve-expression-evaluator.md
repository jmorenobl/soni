## Task: 009 - Improve Expression Evaluator Edge Cases

**ID de tarea:** 009
**Hito:** Robustness
**Dependencias:** Ninguna
**Duración estimada:** 1 hora

### Objetivo

Mejorar el evaluador de expresiones en `core/expression.py` para manejar edge cases correctamente.

### Contexto

Problemas actuales en `_parse_value()`:

```python
# core/expression.py:138
if expr.replace(".", "").replace("-", "").isdigit():
```

Problemas:
1. `"-"` (solo guión) pasa la validación
2. `"--5"` pasa la validación
3. `"5-3"` se interpreta como número

### Entregables

- [ ] Usar regex o try/except para parsing numérico
- [ ] Tests para edge cases
- [ ] Mantener comportamiento existente para casos válidos

### Implementación Detallada

#### Paso 1: Refactorizar parsing numérico

**Archivo(s) a modificar:** `src/soni/core/expression.py`

```python
def _parse_value(expr: str, slots: dict[str, Any]) -> Any:
    """Parse a value expression (literal or slot reference)."""
    expr = expr.strip()

    # String literal (quoted)
    if (expr.startswith("'") and expr.endswith("'")) or (
        expr.startswith('"') and expr.endswith('"')
    ):
        return expr[1:-1]

    # Numeric literal - use try/except instead of fragile regex
    try:
        if "." in expr:
            return float(expr)
        return int(expr)
    except ValueError:
        pass  # Not a number, continue

    # Boolean literals
    if expr.lower() == "true":
        return True
    if expr.lower() == "false":
        return False

    # None literal
    if expr.lower() in ("none", "null"):
        return None

    # Slot reference
    return slots.get(expr)
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/core/test_expression_edge_cases.py`

```python
import pytest
from soni.core.expression import evaluate_condition, _parse_value


class TestParseValueEdgeCases:
    """Tests for _parse_value edge cases."""

    def test_valid_integer(self):
        """Test parsing valid integer."""
        # Arrange & Act
        result = _parse_value("42", {})

        # Assert
        assert result == 42
        assert isinstance(result, int)

    def test_valid_negative_integer(self):
        """Test parsing negative integer."""
        # Arrange & Act
        result = _parse_value("-5", {})

        # Assert
        assert result == -5

    def test_valid_float(self):
        """Test parsing valid float."""
        # Arrange & Act
        result = _parse_value("3.14", {})

        # Assert
        assert result == 3.14
        assert isinstance(result, float)

    def test_dash_only_is_slot_reference(self):
        """Test that single dash is treated as slot reference, not number."""
        # Arrange
        slots = {"-": "dash_value"}

        # Act
        result = _parse_value("-", slots)

        # Assert
        # Should return slot value or None, not crash
        assert result == "dash_value" or result is None

    def test_double_dash_is_slot_reference(self):
        """Test that double dash is not treated as number."""
        # Arrange
        slots = {}

        # Act
        result = _parse_value("--5", slots)

        # Assert
        # Should not return -5, should be None (no such slot)
        assert result is None

    def test_expression_like_string_is_slot(self):
        """Test that 5-3 is treated as slot reference."""
        # Arrange
        slots = {"5-3": "slot_value"}

        # Act
        result = _parse_value("5-3", slots)

        # Assert
        assert result == "slot_value"


class TestEvaluateConditionEdgeCases:
    """Tests for evaluate_condition edge cases."""

    def test_compare_with_negative_number(self):
        """Test comparison with negative literal."""
        # Arrange
        slots = {"temperature": -10}

        # Act
        result = evaluate_condition("temperature > -20", slots)

        # Assert
        assert result is True

    def test_compare_missing_slot_returns_false(self):
        """Test that missing slot returns False, not crash."""
        # Arrange
        slots = {}

        # Act
        result = evaluate_condition("missing > 5", slots)

        # Assert
        assert result is False
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/core/test_expression_edge_cases.py -v
# Expected: Some FAILED (edge cases not handled)
```

#### Green Phase: Make Tests Pass

Implementar parsing robusto.

```bash
uv run pytest tests/unit/core/test_expression_edge_cases.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] `"-"` solo no se parsea como número
- [ ] `"--5"` no se parsea como -5
- [ ] Números negativos válidos funcionan
- [ ] `uv run pytest` pasa
- [ ] `uv run ruff check .` sin errores
- [ ] `uv run mypy src/soni` sin errores

### Validación Manual

```bash
uv run pytest tests/unit/core/test_expression*.py -v
```

### Referencias

- `src/soni/core/expression.py:127-152` - Función _parse_value
