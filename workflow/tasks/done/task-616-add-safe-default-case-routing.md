## Task: 6.1.6 - Add Safe Default Case in Routing

**ID de tarea:** 616
**Hito:** Bug Fix - Graph Recursion Issue
**Dependencias:** Task 614 (Add Detailed Logging)
**Duración estimada:** 30 minutos

### Objetivo

Add safe default case handling in routing functions to prevent infinite loops when unexpected states occur. This is a defensive programming measure to ensure the graph always has a valid path forward.

### Contexto

When routing functions encounter unexpected states (e.g., None values, missing fields, unexpected enum values), they should:
1. Log a warning with full context
2. Return a safe default route that doesn't create loops
3. Provide enough information for debugging

Currently, some routing functions have default cases but don't log warnings, making it hard to debug issues.

**Reference:** Analysis in conversation about graph recursion limit errors

### Entregables

- [ ] `src/soni/dm/routing.py` updated with safe default cases
- [ ] All routing functions log warnings for unexpected states
- [ ] Default cases return safe routes (usually "generate_response" → END)
- [ ] Logging includes full context for debugging

### Implementación Detallada

#### Paso 1: Add Safe Default Case to route_after_understand

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

**Código específico:**

The default case is already handled in Task 614 (line 290-291), but ensure it's complete:

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
- Already implemented in Task 614
- This ensures we always return a valid route
- "generate_response" → END is a safe default that terminates the graph

#### Paso 2: Add Safe Default Case to route_after_validate

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

**Código específico:**

Replace lines 314-316:

```python
else:
    # Default fallback
    return "generate_response"
```

With:

```python
else:
    # Default fallback - unexpected conversation_state
    logger.warning(
        f"Unexpected conversation_state '{conv_state}' in route_after_validate, "
        f"falling back to generate_response",
        extra={
            "conversation_state": conv_state,
            "state_keys": list(state.keys()) if isinstance(state, dict) else [],
        }
    )
    return "generate_response"
```

**Explicación:**
- Log warning for unexpected conversation_state
- Return safe default route
- Include state context for debugging

#### Paso 3: Verify route_after_action Has Safe Default

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

**Código específico:**

The default case at lines 353-356 already exists and logs, but verify it's complete:

```python
else:
    # Default: flow complete
    logger.info(f"Routing to generate_response (default, state={conv_state})")
    return "generate_response"
```

**Explicación:**
- Already has logging (good!)
- Returns safe default route
- No changes needed, but verify it's working

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_routing.py`

**Tests específicos a implementar:**

```python
def test_route_after_validate_handles_unexpected_state(caplog):
    """Test that route_after_validate handles unexpected conversation_state."""
    # Arrange
    state = {
        "conversation_state": "unexpected_state",
    }

    # Act
    with caplog.at_level(logging.WARNING):
        result = route_after_validate(state)

    # Assert
    assert result == "generate_response"
    assert "Unexpected conversation_state" in caplog.text
    assert "unexpected_state" in caplog.text

def test_route_after_understand_handles_none_message_type(caplog):
    """Test that route_after_understand handles None message_type."""
    # Arrange
    state = {
        "nlu_result": {
            "message_type": None,
            "command": "test",
        }
    }

    # Act
    with caplog.at_level(logging.WARNING):
        result = route_after_understand(state)

    # Assert
    assert result == "generate_response"
    assert "Unknown message_type" in caplog.text
```

### Criterios de Éxito

- [ ] All routing functions have safe default cases
- [ ] Default cases log warnings with full context
- [ ] Default cases return safe routes (usually "generate_response")
- [ ] No routing function can return None or invalid route
- [ ] All existing tests pass
- [ ] New tests pass
- [ ] Linting passes without errors

### Validación Manual

**Comandos para validar:**

```bash
# Run debug scenarios
uv run python scripts/debug_scenarios.py

# Check logs for warnings on unexpected states
# Verify graph always terminates (no recursion errors)
```

**Resultado esperado:**
- No recursion errors even with unexpected states
- Warnings logged for unexpected states
- Graph always finds a valid route forward
- Easy to identify issues from logs

### Referencias

- `src/soni/dm/routing.py` - Current routing implementation
- Defensive programming best practices
- Graph termination guarantees

### Notas Adicionales

**Defensive Programming (NOT Retrocompatibility):**
- This is defensive programming for **unexpected runtime errors**, not backwards compatibility
- Safe defaults ensure the graph always terminates even with bugs
- Logging helps identify issues without breaking the system
- "generate_response" → END is always a safe termination point

**NO Retrocompatibilidad (Pre-v1.0 Policy):**
- Don't add code to handle old data formats - fix the source
- Default cases are for **unexpected errors**, not **expected variations**
- If you find yourself adding multiple format handlers, refactor the source instead

**This complements:**
- Task 613: Fix enum serialization (eliminates the main source of routing failures)
- Task 614: Add logging (helps identify remaining issues quickly)
