## Task: 6.1.4 - Add Detailed Logging in Routing Functions

**ID de tarea:** 614
**Hito:** Bug Fix - Graph Recursion Issue
**Dependencias:** Task 613 (Fix Enum Serialization)
**Duración estimada:** 30 minutos - 1 hora

### Objetivo

Add detailed logging to routing functions to help debug routing decisions and identify why the graph enters infinite loops. This will make it easier to diagnose routing issues in the future.

### Contexto

When debugging the graph recursion issue, it was difficult to understand:
1. What `message_type` value the routing function received
2. What `command` was extracted by NLU
3. Why the routing function chose a particular path
4. What slots were extracted

Adding detailed logging will help diagnose these issues quickly.

**Reference:** Analysis in conversation about graph recursion limit errors

### Entregables

- [ ] `src/soni/dm/routing.py` updated with detailed logging
- [ ] `route_after_understand` logs message_type, command, and slots
- [ ] `route_after_validate` logs conversation_state
- [ ] `route_after_action` logs conversation_state (already has some logging)
- [ ] Logging uses appropriate levels (INFO for routing decisions, DEBUG for details)

### Implementación Detallada

#### Paso 1: Add Detailed Logging to route_after_understand

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

**Código específico:**

Replace line 265:

```python
logger.debug(f"route_after_understand: message_type={message_type}")
```

With:

```python
slots = nlu_result.get("slots", [])
logger.info(
    f"route_after_understand: message_type={message_type}, command={nlu_result.get('command')}, "
    f"slots_count={len(slots)}",
    extra={
        "message_type": message_type,
        "command": nlu_result.get("command"),
        "slots": [s["name"] for s in slots],  # Slots are always dicts after model_dump(mode='json')
        "confidence": nlu_result.get("confidence"),
    }
)
```

**Explicación:**
- Use `logger.info` instead of `logger.debug` for routing decisions (important for debugging)
- Include command and slots count in the log message
- Add structured logging with `extra` parameter for better log analysis
- **NO retrocompatibilidad**: Slots are always dicts after `model_dump(mode='json')` - no need to handle object format

#### Paso 2: Add Logging to route_after_validate

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

**Código específico:**

Add after line 303 (after `conv_state = state.get("conversation_state")`):

```python
logger.info(
    f"route_after_validate: conversation_state={conv_state}",
    extra={
        "conversation_state": conv_state,
        "has_nlu_result": "nlu_result" in state,
        "has_flow_slots": bool(state.get("flow_slots")),
    }
)
```

**Explicación:**
- Log the conversation_state that determines routing
- Include context about NLU result and flow_slots presence
- Keep it simple - no need for complex slot counting in routing logs

#### Paso 3: Add Warning for Unknown Message Types

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

**Código específico:**

Replace lines 290-291:

```python
case _:
    return "generate_response"
```

With:

```python
case _:
    logger.warning(
        f"Unknown message_type '{message_type}' in route_after_understand, "
        f"falling back to generate_response. NLU result: {nlu_result}",
        extra={
            "message_type": message_type,
            "command": nlu_result.get("command"),
            "nlu_result_keys": list(nlu_result.keys()) if isinstance(nlu_result, dict) else [],
        }
    )
    return "generate_response"
```

**Explicación:**
- Add warning when message_type doesn't match any case
- Include full NLU result in log for debugging
- Use structured logging for better analysis

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_routing.py` (create if doesn't exist)

**Tests específicos a implementar:**

```python
def test_route_after_understand_logs_message_type(caplog):
    """Test that route_after_understand logs message_type correctly."""
    # Arrange
    state = {
        "nlu_result": {
            "message_type": "slot_value",
            "command": "test_command",
            "slots": [{"name": "test_slot"}],
            "confidence": 0.9,
        }
    }

    # Act
    with caplog.at_level(logging.INFO):
        result = route_after_understand(state)

    # Assert
    assert "route_after_understand" in caplog.text
    assert "message_type=slot_value" in caplog.text
    assert "command=test_command" in caplog.text

def test_route_after_understand_warns_unknown_message_type(caplog):
    """Test that route_after_understand warns on unknown message_type."""
    # Arrange
    state = {
        "nlu_result": {
            "message_type": "unknown_type",
            "command": "test_command",
        }
    }

    # Act
    with caplog.at_level(logging.WARNING):
        result = route_after_understand(state)

    # Assert
    assert "Unknown message_type" in caplog.text
    assert result == "generate_response"
```

### Criterios de Éxito

- [ ] `route_after_understand` logs message_type, command, and slots
- [ ] `route_after_validate` logs conversation_state
- [ ] Unknown message_type triggers warning log
- [ ] Logging uses appropriate levels (INFO/WARNING)
- [ ] Structured logging with `extra` parameter
- [ ] All existing tests pass
- [ ] New tests pass
- [ ] Linting passes without errors

### Validación Manual

**Comandos para validar:**

```bash
# Run debug scenarios with logging
uv run python scripts/debug_scenarios.py 1

# Check logs for routing decisions
# Verify that message_type, command, and slots are logged
```

**Resultado esperado:**
- Logs show routing decisions with full context
- Unknown message types trigger warnings
- Easy to trace routing path through logs

### Referencias

- `src/soni/dm/routing.py` - Current routing implementation
- Python logging documentation
- Structured logging best practices

### Notas Adicionales

**Logging Levels:**
- Use INFO level for routing decisions (important operational information)
- Use WARNING level for unexpected cases (unknown message types)
- Structured logging with `extra` parameter allows better log analysis tools
- This logging will be invaluable for debugging future routing issues

**NO Retrocompatibilidad (Pre-v1.0 Policy):**
- `nlu_result` is always a dict with string values (from `model_dump(mode='json')`)
- Slots are always dicts with string keys - no need to handle object format
- Don't add code to handle multiple formats - fix the source instead
