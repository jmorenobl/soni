## Task: DM-001 - Refactor route_after_understand Function

**ID de tarea:** DM-001
**Hito:** Dialog Manager Enterprise Hardening
**Dependencias:** DM-002 ✅ (completa - enums ya disponibles)
**Duración estimada:** 4 horas

### Objetivo

Refactorizar la función `route_after_understand` (~220 líneas) en funciones más pequeñas y manejables, aplicando el patrón de dispatch dictionary para mejorar legibilidad y mantenibilidad.

### Contexto

La función `route_after_understand` en `src/soni/dm/routing.py` viola el Single Responsibility Principle al manejar:
- Normalización de `message_type`
- Casos especiales para estado `confirming`
- Lógica de verificación de flujo activo
- Un `match` statement con ~12 cases

Para código enterprise-ready, cada caso debería ser una función independiente, facilitando testing y mantenimiento.

### Entregables

- [ ] Extraer cada case del match a funciones privadas (`_route_slot_value`, `_route_correction`, etc.)
- [ ] Crear diccionario de dispatch `ROUTE_HANDLERS`
- [ ] Reducir `route_after_understand` a <30 líneas
- [ ] Mantener 100% de cobertura de tests existentes
- [ ] Documentar cada handler con docstrings claros

### Implementación Detallada

#### Paso 1: Crear handlers individuales

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

**Código específico:**

```python
def _route_slot_value(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Route slot_value message type.

    Handles special cases:
    - If confirming: treat as confirmation
    - If understanding after denial: treat as modification
    - If no active flow but has command: start flow first
    """
    conv_state = state.get("conversation_state")
    if conv_state == "confirming":
        logger.warning(
            "NLU detected slot_value but conversation_state=confirming, "
            "treating as confirmation to avoid errors"
        )
        return "handle_confirmation"
    # ... rest of logic extracted from current match case
    return "validate_slot"


def _route_correction(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Route correction message type."""
    # ... extracted logic
    return "handle_correction"


# Similar for: _route_modification, _route_intent_change, _route_digression,
# _route_cancellation, _route_confirmation, _route_continuation, _route_clarification
```

#### Paso 2: Crear dispatch dictionary

```python
from typing import Callable

RouteHandler = Callable[[DialogueStateType, dict[str, Any]], str]

ROUTE_HANDLERS: dict[str, RouteHandler] = {
    "slot_value": _route_slot_value,
    "correction": _route_correction,
    "modification": _route_modification,
    "interruption": _route_intent_change,
    "intent_change": _route_intent_change,
    "clarification": _route_clarification,
    "digression": _route_digression,
    "question": _route_digression,
    "cancellation": _route_cancellation,
    "confirmation": _route_confirmation,
    "continuation": _route_continuation,
}


def _route_fallback(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Fallback handler for unknown message types."""
    logger.warning(f"Unknown message_type in route_after_understand")
    return "generate_response"
```

#### Paso 3: Simplificar route_after_understand

```python
def route_after_understand(state: DialogueStateType) -> str:
    """Route based on NLU result using dispatch pattern."""
    nlu_result = state.get("nlu_result")
    if not nlu_result:
        return "generate_response"

    message_type = _normalize_message_type(nlu_result.get("message_type"))

    logger.info(
        f"route_after_understand: message_type={message_type}",
        extra={"message_type": message_type, "command": nlu_result.get("command")},
    )

    handler = ROUTE_HANDLERS.get(message_type, _route_fallback)
    return handler(state, nlu_result)
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/dm/test_routing_handlers.py`

**Failing tests to write FIRST:**

```python
import pytest
from soni.dm.routing import (
    _route_slot_value,
    _route_correction,
    ROUTE_HANDLERS,
)

class TestRouteHandlersDispatch:
    """Test dispatch pattern for route handlers."""

    def test_route_handlers_has_all_message_types(self):
        """Test that ROUTE_HANDLERS covers all expected message types."""
        expected_types = {
            "slot_value", "correction", "modification", "interruption",
            "intent_change", "clarification", "digression", "question",
            "cancellation", "confirmation", "continuation",
        }
        assert expected_types <= set(ROUTE_HANDLERS.keys())

    def test_route_slot_value_confirming_state(self):
        """Test slot_value routes to confirmation when in confirming state."""
        state = {"conversation_state": "confirming", "nlu_result": {}}
        nlu_result = {"message_type": "slot_value", "slots": []}
        result = _route_slot_value(state, nlu_result)
        assert result == "handle_confirmation"
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/dm/test_routing_handlers.py -v
# Expected: FAILED (handlers not extracted yet)
```

#### Green Phase: Make Tests Pass

Implement the handlers as described in "Implementación Detallada".

**Verify tests pass:**
```bash
uv run pytest tests/unit/dm/test_routing_handlers.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] `route_after_understand` tiene menos de 30 líneas
- [ ] Cada handler tiene su propia función con docstring
- [ ] `ROUTE_HANDLERS` diccionario cubre todos los message types
- [ ] Todos los tests existentes siguen pasando
- [ ] Coverage >= 84% (actual)
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
uv run pytest tests/unit/dm/ -v --cov=src/soni/dm/routing
uv run pytest tests/integration/ -v
uv run ruff check src/soni/dm/routing.py
uv run mypy src/soni/dm/routing.py
```

**Resultado esperado:**
- Todos los tests pasan
- Coverage mantiene o mejora
- No hay nuevos warnings de linting

### Referencias

- [routing.py](file:///Users/jorge/Projects/Playground/soni/src/soni/dm/routing.py)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- Refactoring to Patterns - Joshua Kerievsky

### Notas Adicionales

- NO cambiar comportamiento, solo estructura
- Mantener logging existente en cada handler
- Considerar crear módulo `routing/handlers.py` si el archivo crece demasiado
