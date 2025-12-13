## Task: 6.1.3 - Fix Enum Serialization in Understand Node

**ID de tarea:** 613
**Hito:** Bug Fix - Graph Recursion Issue
**Dependencias:** Ninguna
**Duración estimada:** 1-2 horas

### Objetivo

Fix the enum serialization issue in `understand_node` that causes routing failures. When `NLUOutput` is serialized using `model_dump()`, enums (`MessageType`, `SlotAction`) may not be properly converted to strings, causing the routing function to fail to match message types correctly.

### Contexto

The graph recursion error occurs because:
1. `understand_node` calls `nlu_result_raw.model_dump()` which may not properly serialize enums
2. The routing function `route_after_understand` expects `message_type` to be a string
3. If the enum is not serialized correctly, the routing fails to match any case and falls back to `generate_response`
4. This can create infinite loops if the state doesn't properly terminate

**Reference:** Analysis in conversation about graph recursion limit errors in `scripts/debug_scenarios.py`

### Entregables

- [ ] `src/soni/dm/nodes/understand.py` updated with proper enum serialization
- [ ] `MessageType` enum properly converted to string in `nlu_result`
- [ ] `SlotAction` enum properly converted to string in slot dictionaries
- [ ] Tests verify enum serialization works correctly
- [ ] Graph recursion errors resolved

### Implementación Detallada

#### Paso 1: Update understand_node Enum Serialization

**Archivo(s) a modificar:** `src/soni/dm/nodes/understand.py`

**Código específico:**

Replace lines 92-98:

```python
# Convert NLUOutput to dict for state storage
# (DialogueState uses dict, not Pydantic models)
if hasattr(nlu_result_raw, "model_dump"):
    nlu_result = nlu_result_raw.model_dump()
else:
    # Fallback if already a dict (shouldn't happen with SoniDU)
    nlu_result = nlu_result_raw if isinstance(nlu_result_raw, dict) else {}
```

With:

```python
# Convert NLUOutput to dict for state storage
# mode='json' ensures enums are serialized as strings (not enum objects)
# This is required for routing functions to match message_type correctly
nlu_result = nlu_result_raw.model_dump(mode='json')
```

**Explicación:**
- Use `mode='json'` in `model_dump()` to serialize enums as strings directly
- This is the clean, Pydantic-native way to handle enum serialization
- **NO retrocompatibilidad**: SoniDU always returns `NLUOutput`, no fallback needed
- **NO código defensivo**: Pydantic handles all serialization correctly with `mode='json'`

**Por qué `mode='json'` y no `mode='python'`:**
- `mode='python'`: Keeps enums as Python enum objects → routing fails
- `mode='json'`: Converts enums to their string values → routing works

**Referencia Pydantic:**
- `model_dump(mode='json')` converts all types to JSON-compatible formats
- For `str` enums like `MessageType(str, Enum)`, this outputs the string value directly

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_nodes_understand.py`

**Tests específicos a implementar:**

```python
@pytest.mark.asyncio
async def test_understand_node_serializes_message_type_enum():
    """Test that understand_node properly serializes MessageType enum to string."""
    # Arrange
    from soni.du.models import MessageType, NLUOutput, SlotValue, SlotAction

    nlu_output = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="test_command",
        slots=[SlotValue(name="test_slot", value="test_value", confidence=0.9, action=SlotAction.PROVIDE)],
        confidence=0.9,
        reasoning="Test reasoning"
    )

    # Mock nlu_provider to return NLUOutput
    # ... setup mock ...

    # Act
    result = await understand_node(state, runtime)

    # Assert
    assert "nlu_result" in result
    assert isinstance(result["nlu_result"]["message_type"], str)
    assert result["nlu_result"]["message_type"] == "slot_value"
    assert isinstance(result["nlu_result"]["slots"][0]["action"], str)
    assert result["nlu_result"]["slots"][0]["action"] == "provide"

def test_nlu_output_model_dump_json_mode():
    """Test that NLUOutput.model_dump(mode='json') serializes enums to strings."""
    from soni.du.models import MessageType, NLUOutput, SlotValue, SlotAction

    # Arrange
    nlu_output = NLUOutput(
        message_type=MessageType.INTERRUPTION,
        command="book_flight",
        slots=[SlotValue(name="origin", value="Madrid", confidence=0.9, action=SlotAction.PROVIDE)],
        confidence=0.95,
        reasoning="User wants to book a flight"
    )

    # Act
    result = nlu_output.model_dump(mode='json')

    # Assert - enums are strings, not enum objects or dicts
    assert result["message_type"] == "interruption"
    assert result["slots"][0]["action"] == "provide"
    assert isinstance(result["message_type"], str)
    assert isinstance(result["slots"][0]["action"], str)
```

### Criterios de Éxito

- [ ] `understand_node` properly serializes `MessageType` enum to string
- [ ] `understand_node` properly serializes `SlotAction` enum to string
- [ ] Routing function can correctly match message types
- [ ] Graph recursion errors no longer occur
- [ ] All existing tests pass
- [ ] New tests pass
- [ ] Linting passes without errors
- [ ] Type checking passes without errors

### Validación Manual

**Comandos para validar:**

```bash
# Run the debug scenarios script
uv run python scripts/debug_scenarios.py 1

# Check that no recursion errors occur
# Verify that message_type is a string in logs
```

**Resultado esperado:**
- No "Recursion limit of 25 reached" errors
- `message_type` in `nlu_result` is always a string
- Routing correctly identifies message types
- Graph execution completes successfully

### Referencias

- `src/soni/dm/nodes/understand.py` - Current implementation
- `src/soni/du/models.py` - MessageType and SlotAction enum definitions
- `src/soni/dm/routing.py` - Routing function that uses message_type
- Pydantic documentation on `model_dump(mode='python')`

### Notas Adicionales

**NO Retrocompatibilidad (Pre-v1.0 Policy):**
- SoniDU **always** returns `NLUOutput` - no fallback for dict needed
- Pydantic's `model_dump(mode='json')` handles enum serialization correctly - no manual conversion needed
- We use a single, clean solution instead of defensive code for multiple formats

**Why This Works:**
- `MessageType(str, Enum)` is a string enum → `mode='json'` outputs the string value
- `SlotAction(str, Enum)` is a string enum → same behavior
- This is the Pydantic-native approach, not a workaround

**This fix is critical:** Without proper enum serialization, routing functions cannot match message types and the graph enters infinite loops
