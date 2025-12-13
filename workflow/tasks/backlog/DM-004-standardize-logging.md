## Task: DM-004 - Standardize Routing Logging

**ID de tarea:** DM-004
**Hito:** Dialog Manager Enterprise Hardening
**Dependencias:** DM-001 (Facilita aplicar a handlers individuales)
**Duración estimada:** 2 horas

### Objetivo

Estandarizar el logging en el módulo de routing creando un decorador o helper que capture automáticamente decisiones de routing con formato consistente.

### Contexto

El logging actual es inconsistente:
- Algunas funciones usan `verbose_logging=True` con `logger.info("=" * 80)`
- Otras usan logging mínimo
- Los mensajes de log varían en formato y nivel de detalle

Para debugging en producción, necesitamos:
- Formato consistente
- Niveles apropiados (INFO para routing normal, DEBUG para detalles)
- Información estructurada (usando `extra={}`)

### Entregables

- [ ] Crear decorador `@log_routing_decision` o helper function
- [ ] Estandarizar formato de logs de routing
- [ ] Aplicar a todas las funciones de routing
- [ ] Eliminar logs ad-hoc redundantes

### Implementación Detallada

#### Paso 1: Crear decorador de logging

**Archivo(s) a crear/modificar:** `src/soni/dm/routing.py`

```python
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R", bound=str)


def log_routing_decision(func):
    """Decorator that logs routing decisions consistently.

    Logs entry with state summary, and logs the routing result.
    Uses structured logging with extra fields for production monitoring.
    """
    @wraps(func)
    def wrapper(state: DialogueStateType, *args, **kwargs) -> str:
        router_name = func.__name__
        conv_state = state.get("conversation_state")

        logger.debug(
            f"[{router_name}] START",
            extra={
                "router": router_name,
                "conversation_state": conv_state,
                "user_message": state.get("user_message", "")[:50],  # Truncate
            }
        )

        result = func(state, *args, **kwargs)

        logger.info(
            f"[{router_name}] -> {result}",
            extra={
                "router": router_name,
                "conversation_state": conv_state,
                "next_node": result,
            }
        )

        return result

    return wrapper


# Usage:
@log_routing_decision
def route_after_understand(state: DialogueStateType) -> str:
    # No need for manual logging - decorator handles it
    ...
```

#### Paso 2: Definir formato estándar

```python
# Standard log format for routing:
# DEBUG: [router_name] START (with state context in extra)
# INFO:  [router_name] -> next_node (final decision)
# WARNING: [router_name] Unexpected state... (anomalies)

# Example output:
# 2024-01-15 10:30:45 DEBUG [route_after_understand] START
# 2024-01-15 10:30:45 INFO  [route_after_understand] -> validate_slot
```

#### Paso 3: Crear verbose logging helper para debugging

```python
def log_routing_verbose(
    router_name: str,
    state: DialogueStateType,
    *,
    show_separator: bool = True,
) -> None:
    """Log detailed state for debugging complex routing issues.

    Only enabled when logger level is DEBUG.

    Args:
        router_name: Name of the routing function
        state: Current dialogue state
        show_separator: Whether to show visual separator lines
    """
    if not logger.isEnabledFor(logging.DEBUG):
        return

    if show_separator:
        logger.debug("=" * 60)

    logger.debug(f"ROUTING after {router_name}:")
    logger.debug(f"  conversation_state: {state.get('conversation_state')}")
    logger.debug(f"  waiting_for_slot: {state.get('waiting_for_slot')}")
    logger.debug(f"  flow_stack depth: {len(state.get('flow_stack', []))}")

    if show_separator:
        logger.debug("=" * 60)
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/dm/test_routing_logging.py`

```python
import logging
import pytest
from soni.dm.routing import log_routing_decision


class TestRoutingLogging:
    """Test routing logging decorator."""

    def test_decorator_logs_result(self, caplog):
        """Decorator should log the routing result."""
        @log_routing_decision
        def mock_router(state):
            return "next_node"

        with caplog.at_level(logging.INFO):
            result = mock_router({"conversation_state": "testing"})

        assert result == "next_node"
        assert "mock_router" in caplog.text
        assert "next_node" in caplog.text

    def test_decorator_includes_extra_fields(self, caplog):
        """Decorator should include structured extra fields."""
        @log_routing_decision
        def mock_router(state):
            return "result"

        with caplog.at_level(logging.DEBUG):
            mock_router({"conversation_state": "confirming"})

        # Check extra fields are present in record
        for record in caplog.records:
            if hasattr(record, "router"):
                assert record.router == "mock_router"
                break
        else:
            pytest.fail("No log record with router extra field")
```

### Criterios de Éxito

- [ ] Decorador `@log_routing_decision` implementado y testeado
- [ ] Todas las funciones `route_after_*` usan el decorador
- [ ] Logs tienen formato consistente: `[router_name] -> next_node`
- [ ] No hay duplicación de `logger.info("=" * 80)` ad-hoc
- [ ] Structured logging con `extra={}` para monitoring tools
- [ ] DEBUG level para estado detallado, INFO para decisiones

### Validación Manual

```bash
# Run with debug logging to see verbose output
SONI_LOG_LEVEL=DEBUG uv run pytest tests/integration/test_simple_flow.py -v -s

# Verify production logs are clean (INFO level)
uv run pytest tests/integration/ -v 2>&1 | grep -E "route_after|ROUTING"
```

### Referencias

- [Python logging best practices](https://docs.python.org/3/howto/logging.html)
- [Structured logging](https://www.structlog.org/)

### Notas Adicionales

- Considerar integración con structlog para JSON logs en producción
- El decorador debe ser transparente para type hints (usar ParamSpec)
- Truncar `user_message` en logs para evitar PII leaks
