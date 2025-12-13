## Task: 205 - Add Comprehensive Tests for Confirmation Flow

**ID de tarea:** 205
**Hito:** Confirmation Flow Fix
**Dependencias:** Task 201, Task 202, Task 203, Task 204
**Duración estimada:** 4-5 horas

### Objetivo

Add comprehensive unit and integration tests for the complete confirmation flow, covering happy path, edge cases, error handling, and defensive checks.

### Contexto

After fixing the confirmation flow issues (Tasks 201-204), we need comprehensive test coverage to:
1. Ensure the fixes work correctly
2. Prevent regressions when making future changes
3. Document expected behavior through tests
4. Validate edge cases and error handling

The confirmation flow involves multiple components:
- NLU extraction of confirmation_value
- Confirmation message display after actions
- User response handling (yes/no/unclear)
- Defensive checks (retry limits)
- State transitions and routing

**References:**
- Analysis: `docs/analysis/ANALISIS_ERROR_CONFIRMACION.md`
- Previous tasks: 201, 202, 203, 204
- Existing tests: `tests/unit/test_nlu_provider.py`, `tests/integration/test_scenarios.py`

### Entregables

- [ ] Unit tests for NLU confirmation extraction (15+ test cases)
- [ ] Unit tests for handle_confirmation_node (10+ test cases)
- [ ] Unit tests for confirm_action_node (5+ test cases)
- [ ] Integration tests for complete confirmation flow (8+ test cases)
- [ ] Tests for defensive checks and error handling (6+ test cases)
- [ ] Tests for correction during confirmation (4+ test cases)
- [ ] Parametrized tests for yes/no variations (20+ combinations)
- [ ] Coverage report showing >90% coverage for confirmation-related code

### Implementación Detallada

#### Paso 1: Unit tests for NLU confirmation extraction

**Archivo de tests:** `tests/unit/test_nlu_confirmation.py`

**Código específico:**

```python
"""Unit tests for NLU confirmation value extraction."""

import pytest
from soni.du.models import DialogueContext, MessageType, NLUOutput
from soni.du.modules import SoniDU


@pytest.fixture
def du_module():
    """Create SoniDU module for testing."""
    return SoniDU(use_cot=False)


@pytest.fixture
def confirming_context():
    """Create context for confirmation state."""
    return DialogueContext(
        current_slots={
            "origin": "Madrid",
            "destination": "Barcelona",
            "departure_date": "2025-12-10"
        },
        current_flow="book_flight",
        conversation_state="confirming",
        available_flows={"book_flight": "Book a flight"},
        expected_slots=["origin", "destination", "departure_date"],
    )


# === YES VARIATIONS ===
@pytest.mark.parametrize("user_input,expected_confidence", [
    ("yes", 0.95),
    ("Yes", 0.95),
    ("YES", 0.95),
    ("yes please", 0.90),
    ("confirm", 0.95),
    ("correct", 0.90),
    ("that's right", 0.85),
    ("that's correct", 0.85),
    ("sounds good", 0.80),
    ("perfect", 0.80),
    ("absolutely", 0.85),
    ("sure", 0.80),
    ("ok", 0.75),
    ("okay", 0.75),
    ("yep", 0.85),
    ("yup", 0.85),
    ("yeah", 0.85),
    ("affirmative", 0.90),
    ("go ahead", 0.80),
    ("proceed", 0.85),
])
@pytest.mark.asyncio
async def test_confirmation_yes_variations(du_module, confirming_context, user_input, expected_confidence):
    """Test various ways of saying 'yes'"""
    result = du_module(user_message=user_input, context=confirming_context)

    assert isinstance(result, NLUOutput)
    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is True
    assert result.confidence >= expected_confidence - 0.1  # Allow 10% margin


# === NO VARIATIONS ===
@pytest.mark.parametrize("user_input,expected_confidence", [
    ("no", 0.95),
    ("No", 0.95),
    ("NO", 0.95),
    ("no thanks", 0.90),
    ("not correct", 0.90),
    ("wrong", 0.85),
    ("incorrect", 0.85),
    ("that's wrong", 0.85),
    ("that's not right", 0.85),
    ("change it", 0.80),
    ("not right", 0.85),
    ("nope", 0.85),
    ("nah", 0.80),
    ("negative", 0.90),
    ("don't proceed", 0.85),
    ("cancel", 0.90),
])
@pytest.mark.asyncio
async def test_confirmation_no_variations(du_module, confirming_context, user_input, expected_confidence):
    """Test various ways of saying 'no'"""
    result = du_module(user_message=user_input, context=confirming_context)

    assert isinstance(result, NLUOutput)
    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is False
    assert result.confidence >= expected_confidence - 0.1


# === UNCLEAR RESPONSES ===
@pytest.mark.parametrize("user_input", [
    "maybe",
    "I'm not sure",
    "hmm",
    "let me think",
    "can you repeat that?",
    "what?",
    "huh?",
    "I don't know",
    "possibly",
])
@pytest.mark.asyncio
async def test_confirmation_unclear(du_module, confirming_context, user_input):
    """Test that unclear responses have confirmation_value=None"""
    result = du_module(user_message=user_input, context=confirming_context)

    # May be detected as CONFIRMATION or CLARIFICATION
    if result.message_type == MessageType.CONFIRMATION:
        assert result.confirmation_value is None
        assert result.confidence <= 0.6  # Low confidence for unclear
    elif result.message_type == MessageType.CLARIFICATION:
        assert result.confirmation_value is None


# === CONTEXT SENSITIVITY ===
@pytest.mark.asyncio
async def test_confirmation_requires_confirming_context(du_module):
    """Test that 'yes' in non-confirming context is not CONFIRMATION"""
    # Context: waiting for slot, not confirming
    slot_context = DialogueContext(
        current_flow="book_flight",
        conversation_state="waiting_for_slot",
        current_prompted_slot="origin",
        expected_slots=["origin", "destination", "departure_date"],
    )

    result = du_module(user_message="yes", context=slot_context)

    # In slot collection context, "yes" alone should be unclear or continuation
    # NOT a confirmation (that requires confirming context)
    assert result.message_type != MessageType.CONFIRMATION
    assert result.confirmation_value is None


# === CONFIRMATION_VALUE ONLY FOR CONFIRMATION TYPE ===
@pytest.mark.asyncio
async def test_confirmation_value_none_for_slot_messages(du_module):
    """Test that confirmation_value is None for slot_value messages"""
    context = DialogueContext(
        current_flow="book_flight",
        conversation_state="waiting_for_slot",
        current_prompted_slot="origin",
        expected_slots=["origin"],
    )

    result = du_module(user_message="Madrid", context=context)

    assert result.message_type == MessageType.SLOT_VALUE
    assert result.confirmation_value is None


# === EDGE CASES ===
@pytest.mark.asyncio
async def test_confirmation_with_explanation(du_module, confirming_context):
    """Test confirmation with additional explanation"""
    result = du_module(
        user_message="Yes, that looks perfect. Let's book it!",
        context=confirming_context
    )

    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is True


@pytest.mark.asyncio
async def test_denial_with_reason(du_module, confirming_context):
    """Test denial with reason"""
    result = du_module(
        user_message="No, the date is wrong",
        context=confirming_context
    )

    # Could be CONFIRMATION (no) or MODIFICATION (wants to change)
    if result.message_type == MessageType.CONFIRMATION:
        assert result.confirmation_value is False
    elif result.message_type == MessageType.MODIFICATION:
        assert result.confirmation_value is None


@pytest.mark.asyncio
async def test_empty_confirmation_response(du_module, confirming_context):
    """Test empty or whitespace-only response"""
    result = du_module(user_message="", context=confirming_context)

    # Should be unclear
    assert result.confirmation_value is None
    assert result.confidence < 0.5
```

**Coverage goal**: 20+ test cases for NLU confirmation extraction

#### Paso 2: Unit tests for handle_confirmation_node

**Archivo de tests:** `tests/unit/test_handle_confirmation_node.py`

**Código específico:**

```python
"""Unit tests for handle_confirmation_node."""

import pytest
from soni.dm.nodes.handle_confirmation import handle_confirmation_node
from soni.core.types import DialogueState


class MockRuntime:
    """Mock runtime for testing."""
    def __init__(self):
        self.context = {}


@pytest.fixture
def mock_runtime():
    return MockRuntime()


# === HAPPY PATH ===
@pytest.mark.asyncio
async def test_handle_confirmation_confirmed(mock_runtime):
    """Test handling user confirmation (yes)"""
    state: DialogueState = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": True,
        },
        "metadata": {},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "ready_for_action"
    assert "confirmation_attempts" not in result.get("metadata", {})


@pytest.mark.asyncio
async def test_handle_confirmation_denied(mock_runtime):
    """Test handling user denial (no)"""
    state: DialogueState = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": False,
        },
        "metadata": {},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "understanding"
    assert "change" in result["last_response"].lower()


# === UNCLEAR RESPONSE ===
@pytest.mark.asyncio
async def test_handle_confirmation_unclear_first_attempt(mock_runtime):
    """Test handling unclear response (first attempt)"""
    state: DialogueState = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": None,
        },
        "metadata": {},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "confirming"
    assert result["metadata"]["_confirmation_attempts"] == 1
    assert "didn't understand" in result["last_response"].lower()


# === RETRY COUNTER ===
@pytest.mark.asyncio
async def test_handle_confirmation_max_retries_exceeded(mock_runtime):
    """Test that exceeding max retries triggers error state"""
    state: DialogueState = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": None,
        },
        "metadata": {"_confirmation_attempts": 3},  # Already at max
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "error"
    assert "_confirmation_attempts" not in result["metadata"]
    assert "trouble understanding" in result["last_response"].lower()


@pytest.mark.asyncio
async def test_handle_confirmation_retry_counter_cleared_on_success(mock_runtime):
    """Test that retry counter is cleared on successful confirmation"""
    state: DialogueState = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": True,
        },
        "metadata": {"_confirmation_attempts": 2},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "ready_for_action"
    assert "_confirmation_attempts" not in result["metadata"]


# === EDGE CASES ===
@pytest.mark.asyncio
async def test_handle_confirmation_missing_nlu_result(mock_runtime):
    """Test handling when NLU result is missing"""
    state: DialogueState = {
        "nlu_result": None,
        "metadata": {},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    # Should treat as unclear and increment retries
    assert result["conversation_state"] in ("confirming", "error", "understanding")


@pytest.mark.asyncio
async def test_handle_confirmation_wrong_message_type(mock_runtime):
    """Test handling when message_type is not confirmation"""
    state: DialogueState = {
        "nlu_result": {
            "message_type": "slot_value",  # Wrong type
            "confirmation_value": None,
        },
        "metadata": {},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    # Should handle gracefully (treat as digression or re-prompt)
    assert result["conversation_state"] in ("confirming", "understanding")
```

**Coverage goal**: 10+ test cases for handle_confirmation_node

#### Paso 3: Integration tests for complete confirmation flow

**Archivo de tests:** `tests/integration/test_confirmation_flow_complete.py`

**Código específico:**

```python
"""Integration tests for complete confirmation flow."""

import pytest
from pathlib import Path
from soni.runtime import RuntimeLoop


@pytest.fixture
async def runtime():
    """Create runtime for testing."""
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    runtime.config.settings.persistence.backend = "memory"
    await runtime._ensure_graph_initialized()
    yield runtime
    await runtime.cleanup()


# === HAPPY PATH ===
@pytest.mark.asyncio
async def test_complete_confirmation_flow_yes(runtime):
    """Test complete flow: book flight, confirm with yes, complete booking"""
    user_id = "test_complete_yes"

    # Step 1: Start flow
    response = await runtime.process_message("I want to book a flight", user_id)
    assert "depart" in response.lower()

    # Step 2-4: Provide slots
    await runtime.process_message("Madrid", user_id)
    await runtime.process_message("Barcelona", user_id)
    response = await runtime.process_message("Tomorrow", user_id)

    # Should show confirmation message
    assert "Madrid" in response
    assert "Barcelona" in response
    assert "confirm" in response.lower()

    # Step 5: Confirm
    response = await runtime.process_message("Yes, please confirm", user_id)

    # Should complete booking
    assert "booking" in response.lower() or "confirmed" in response.lower()
    assert "reference" in response.lower() or "ref" in response.lower()


@pytest.mark.asyncio
async def test_complete_confirmation_flow_no_then_modify(runtime):
    """Test flow: book flight, deny confirmation, modify slot, confirm again"""
    user_id = "test_deny_modify"

    # Steps 1-4: Complete to confirmation
    await runtime.process_message("I want to book a flight", user_id)
    await runtime.process_message("New York", user_id)
    await runtime.process_message("Los Angeles", user_id)
    response = await runtime.process_message("2025-12-15", user_id)

    # Should show confirmation
    assert "New York" in response
    assert "confirm" in response.lower()

    # Deny confirmation
    response = await runtime.process_message("No, change the destination", user_id)

    # Should ask what to change
    assert "change" in response.lower() or "modify" in response.lower()

    # Modify destination
    response = await runtime.process_message("San Francisco", user_id)

    # Should show updated confirmation
    assert "San Francisco" in response
    assert "confirm" in response.lower()

    # Confirm now
    response = await runtime.process_message("Yes", user_id)

    # Should complete
    assert "booking" in response.lower() or "confirmed" in response.lower()


# === UNCLEAR RESPONSES ===
@pytest.mark.asyncio
async def test_confirmation_unclear_then_yes(runtime):
    """Test flow: unclear response, retry, then yes"""
    user_id = "test_unclear"

    # Complete to confirmation
    await runtime.process_message("Book a flight", user_id)
    await runtime.process_message("Boston", user_id)
    await runtime.process_message("Seattle", user_id)
    await runtime.process_message("Next week", user_id)

    # Unclear response
    response = await runtime.process_message("hmm, I'm not sure", user_id)

    # Should ask again
    assert "understand" in response.lower() or "yes" in response.lower() or "no" in response.lower()

    # Now confirm clearly
    response = await runtime.process_message("Yes, that's correct", user_id)

    # Should complete
    assert "booking" in response.lower() or "confirmed" in response.lower()


# === RETRY LIMIT ===
@pytest.mark.asyncio
async def test_confirmation_max_retries(runtime):
    """Test that max retries trigger error state"""
    user_id = "test_max_retries"

    # Complete to confirmation
    await runtime.process_message("Book a flight", user_id)
    await runtime.process_message("Chicago", user_id)
    await runtime.process_message("Denver", user_id)
    await runtime.process_message("2025-12-20", user_id)

    # Give unclear responses 3 times
    response1 = await runtime.process_message("maybe", user_id)
    assert "understand" in response1.lower()

    response2 = await runtime.process_message("hmm", user_id)
    assert "understand" in response2.lower()

    response3 = await runtime.process_message("I don't know", user_id)

    # After 3 unclear responses, should error or reset
    assert "trouble" in response3.lower() or "start over" in response3.lower()


# === EDGE CASES ===
@pytest.mark.asyncio
async def test_confirmation_multiple_slots_one_message(runtime):
    """Test flow where user provides multiple slots at once"""
    user_id = "test_multi_slot"

    # Provide multiple slots in one message
    response = await runtime.process_message(
        "I want to fly from Miami to Orlando tomorrow",
        user_id
    )

    # Should skip directly to confirmation
    if "confirm" in response.lower():
        # All slots filled, showing confirmation
        assert "Miami" in response
        assert "Orlando" in response

        # Confirm
        response = await runtime.process_message("Yes", user_id)
        assert "booking" in response.lower() or "confirmed" in response.lower()


@pytest.mark.asyncio
async def test_confirmation_correction_during_confirmation(runtime):
    """Test correction during confirmation step"""
    user_id = "test_correction"

    # Complete to confirmation
    await runtime.process_message("Book a flight", user_id)
    await runtime.process_message("Austin", user_id)
    await runtime.process_message("Dallas", user_id)
    response = await runtime.process_message("2025-12-25", user_id)

    # Correction during confirmation
    response = await runtime.process_message(
        "Actually, the destination should be Houston, not Dallas",
        user_id
    )

    # Should update and re-show confirmation
    assert "Houston" in response
    assert "confirm" in response.lower()
```

**Coverage goal**: 8+ integration test scenarios

### Criterios de Éxito

- [ ] Unit tests cover all yes/no variations (20+ parametrized cases)
- [ ] Unit tests cover unclear responses and edge cases
- [ ] Unit tests cover retry counter logic
- [ ] Unit tests cover confirmation_value validation
- [ ] Integration tests cover complete happy path
- [ ] Integration tests cover denial and modification
- [ ] Integration tests cover retry limits
- [ ] Integration tests cover corrections during confirmation
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] Coverage >90% for confirmation-related files:
  - `src/soni/dm/nodes/handle_confirmation.py`
  - `src/soni/dm/nodes/confirm_action.py`
  - Confirmation-related routing functions
- [ ] No regressions in existing tests
- [ ] Test execution time <30 seconds

### Validación Manual

**Comandos para validar:**

```bash
# Run all confirmation tests
uv run pytest tests/unit/test_nlu_confirmation.py -v
uv run pytest tests/unit/test_handle_confirmation_node.py -v
uv run pytest tests/integration/test_confirmation_flow_complete.py -v

# Run with coverage
uv run pytest --cov=src/soni/dm/nodes/handle_confirmation --cov=src/soni/dm/nodes/confirm_action --cov-report=term-missing

# Run debug scenarios (should all pass now)
uv run python scripts/debug_scenarios.py

# Run specific scenario
uv run python scripts/debug_scenarios.py 1
```

**Resultado esperado:**
- All confirmation tests pass
- Coverage >90% for confirmation code
- Scenario 1 completes successfully
- No infinite loops or recursion errors
- Clear test output showing what's being tested

### Referencias

- Analysis: `docs/analysis/ANALISIS_ERROR_CONFIRMACION.md`
- Related tasks: 201, 202, 203, 204
- NLU module: `src/soni/du/modules.py`
- handle_confirmation_node: `src/soni/dm/nodes/handle_confirmation.py`
- confirm_action_node: `src/soni/dm/nodes/confirm_action.py`
- Pytest documentation: https://docs.pytest.org/

### Notas Adicionales

**Test organization:**

```
tests/
├── unit/
│   ├── test_nlu_confirmation.py          # NLU extraction tests
│   ├── test_handle_confirmation_node.py  # Node logic tests
│   └── test_confirm_action_node.py       # Confirmation display tests
├── integration/
│   └── test_confirmation_flow_complete.py # End-to-end tests
└── test_defensive_checks.py               # Defensive logic tests (Task 204)
```

**Test coverage targets:**

- NLU confirmation extraction: 20+ test cases
- handle_confirmation_node: 10+ test cases
- Integration flow: 8+ scenarios
- Total: 40+ test cases for confirmation feature

**Parametrized testing:**

Use `@pytest.mark.parametrize` for yes/no variations to avoid repetitive test code:

```python
@pytest.mark.parametrize("input,expected", [
    ("yes", True),
    ("no", False),
    ("maybe", None),
])
def test_confirmation_variations(input, expected):
    # Single test body, multiple inputs
```

**Integration test strategy:**

Each integration test follows the pattern:
1. **Arrange**: Start runtime, initialize user session
2. **Act**: Send messages through complete flow
3. **Assert**: Verify response content and state
4. **Cleanup**: Close runtime

**Edge cases to cover:**

- Empty/whitespace responses
- Very long responses with confirmation
- Mixed language responses
- Typos in confirmation ("yse", "noo")
- Multiple confirmations in one message
- Confirmation + new intent
- Confirmation + slot modification

**Performance consideration:**

Integration tests can be slow. Use fixtures with session scope where possible:

```python
@pytest.fixture(scope="session")
async def runtime_session():
    # Shared runtime for all tests in session
    # Faster but less isolated
```

Balance between test speed and isolation based on needs.
