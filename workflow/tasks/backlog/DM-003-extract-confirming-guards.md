## Task: DM-003 - Extract Confirming State Guards

**ID de tarea:** DM-003
**Hito:** Dialog Manager Enterprise Hardening
**Dependencias:** DM-002 (Enums ayudan, pero no bloquea)
**Duración estimada:** 2 horas

### Objetivo

Extraer la lógica repetida de "si estamos en estado confirming, redirigir a handle_confirmation" a un decorador o guardia reutilizable para eliminar duplicación.

### Contexto

El patrón aparece en 3+ lugares de `route_after_understand`:

```python
# En slot_value case:
if conv_state == "confirming":
    return "handle_confirmation"

# En correction case:
if conv_state == "confirming":
    return "handle_confirmation"

# En modification case:
if conv_state == "confirming":
    return "handle_confirmation"
```

Esta duplicación viola DRY y crea riesgo de inconsistencia si se necesita cambiar el comportamiento.

### Entregables

- [ ] Crear función `_redirect_if_confirming()` o decorador `@confirming_guard`
- [ ] Aplicar en todos los handlers afectados
- [ ] Eliminar código duplicado
- [ ] Tests para el nuevo guardia

### Implementación Detallada

#### Opción A: Función Guard (Recomendada)

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

```python
def _redirect_if_confirming(
    state: DialogueStateType,
    message_type: str,
) -> str | None:
    """Check if we should redirect to confirmation handler.

    When in confirming state, many message types should be
    treated as confirmation responses, not their literal meaning.

    Args:
        state: Current dialogue state
        message_type: Detected message type from NLU

    Returns:
        "handle_confirmation" if should redirect, None otherwise
    """
    conv_state = state.get("conversation_state")
    if conv_state == ConversationState.CONFIRMING:
        logger.info(
            f"NLU detected {message_type} during confirming state, "
            "routing to handle_confirmation"
        )
        return NodeName.HANDLE_CONFIRMATION
    return None


# Usage in handlers:
def _route_slot_value(state: DialogueStateType, nlu_result: dict) -> str:
    """Route slot_value message type."""
    if redirect := _redirect_if_confirming(state, "slot_value"):
        return redirect
    # ... rest of logic
```

#### Opción B: Decorador (Alternativa)

```python
from functools import wraps

def confirming_guard(func):
    """Decorator that redirects to confirmation if in confirming state."""
    @wraps(func)
    def wrapper(state: DialogueStateType, nlu_result: dict) -> str:
        if state.get("conversation_state") == ConversationState.CONFIRMING:
            return NodeName.HANDLE_CONFIRMATION
        return func(state, nlu_result)
    return wrapper


@confirming_guard
def _route_slot_value(state: DialogueStateType, nlu_result: dict) -> str:
    # No need to check confirming - decorator handles it
    return "validate_slot"
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/dm/test_routing_guards.py`

```python
import pytest
from soni.dm.routing import _redirect_if_confirming
from soni.core.constants import ConversationState, NodeName


class TestConfirmingGuard:
    """Test confirming state guard logic."""

    def test_redirects_when_confirming(self):
        """Guard should redirect when in confirming state."""
        state = {"conversation_state": ConversationState.CONFIRMING}
        result = _redirect_if_confirming(state, "slot_value")
        assert result == NodeName.HANDLE_CONFIRMATION

    def test_passes_through_when_not_confirming(self):
        """Guard should return None when not confirming."""
        state = {"conversation_state": ConversationState.WAITING_FOR_SLOT}
        result = _redirect_if_confirming(state, "slot_value")
        assert result is None

    def test_passes_through_when_no_state(self):
        """Guard should return None when no conversation_state."""
        state = {}
        result = _redirect_if_confirming(state, "slot_value")
        assert result is None

    @pytest.mark.parametrize("message_type", [
        "slot_value", "correction", "modification"
    ])
    def test_logs_message_type(self, message_type, caplog):
        """Guard should log the message type being redirected."""
        state = {"conversation_state": ConversationState.CONFIRMING}
        _redirect_if_confirming(state, message_type)
        assert message_type in caplog.text
```

### Criterios de Éxito

- [ ] Lógica de confirming guard extraída a función/decorador único
- [ ] No hay duplicación del patrón en handlers
- [ ] Tests cubren casos edge (no state, otros states)
- [ ] Logging mantiene información de debug
- [ ] Todos los tests existentes siguen pasando

### Validación Manual

```bash
uv run pytest tests/unit/dm/test_routing_guards.py -v
uv run pytest tests/integration/ -v  # Verificar no hay regresiones
```

### Referencias

- [routing.py líneas 343-353, 396-404, 425-433](file:///Users/jorge/Projects/Playground/soni/src/soni/dm/routing.py)

### Notas Adicionales

- Opción A (función) es más explícita y fácil de debugear
- Opción B (decorador) es más elegante pero puede ocultar flujo
- Considerar si otros estados necesitan guardias similares en el futuro
