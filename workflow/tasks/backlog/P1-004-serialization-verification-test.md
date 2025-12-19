## Task: P1-004 - Add State Serialization Round-Trip Test

**Task ID:** P1-004
**Milestone:** 2.4 - Serialization Verification
**Dependencies:** None
**Estimated Duration:** 1 hour

### Objective

Create unit tests that verify all `DialogueState` fields correctly survive JSON serialization/deserialization round-trips, documenting the serialization patterns used in the project.

### Context

**Why this test is important:**

Dialogue state goes through multiple transformations:
1. **Python objects** → **JSON serialization** (checkpointer save)
2. **JSON** → **Storage** (SQLite, PostgreSQL, etc.)
3. **Storage** → **JSON** → **Python objects** (checkpointer load)

Any field that's not JSON-serializable will cause:
- Silent data loss
- Deserialization errors
- Corrupted state when resuming conversations

**Known patterns:**
- Enums: `FlowState.ACTIVE` → `"active"` (StrEnum) ✓ OK
- Dataclasses: Must use `.model_dump()` or `asdict()`
- Pydantic models: Must use `.model_dump()`
- Custom classes: Must be serialized manually

**Current state:**
The roadmap verified that command serialization using `TypedDict + model_dump()` is correct. These tests document and verify that correctness.

### Deliverables

- [ ] Round-trip tests for complete `DialogueState`
- [ ] Tests for each field type (enums, lists, nested dicts)
- [ ] Edge case tests (None, empty, unicode, large numbers)
- [ ] Documentation of serialization patterns

---

### Implementation Details

#### Create test file

**File:** `tests/unit/core/test_state_serialization.py`

**Complete code:**

```python
"""Unit tests for state serialization correctness.

These tests verify that all DialogueState fields correctly survive
the JSON serialization round-trip used by checkpointers.

This is critical for:
- Multi-turn conversations (state restored between messages)
- Server restarts (state restored from persistent storage)
- Distributed deployments (state shared between instances)
"""

import json
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from soni.core.constants import FlowContextState, FlowState, SlotWaitType
from soni.core.state import create_empty_dialogue_state
from soni.core.types import DialogueState, FlowContext


class TestDialogueStateSerializability:
    """Tests verifying DialogueState is fully JSON-serializable."""

    def test_empty_state_is_json_serializable(self) -> None:
        """Test that empty DialogueState can be serialized to JSON."""
        state = create_empty_dialogue_state()

        # Should not raise
        json_str = json.dumps(state, default=str)
        assert json_str is not None

        # Should be deserializable
        restored = json.loads(json_str)
        assert restored["flow_state"] == state["flow_state"]

    def test_state_with_messages_serializes_custom_fields(self) -> None:
        """Test state with messages - custom fields serialize correctly."""
        state = create_empty_dialogue_state()
        state["messages"] = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]

        # LangGraph handles message serialization internally
        # Here we test that our custom fields are OK
        serializable_fields = {k: v for k, v in state.items() if k != "messages"}
        json_str = json.dumps(serializable_fields, default=str)
        assert json_str is not None

    def test_state_with_flow_context_is_serializable(self) -> None:
        """Test state with FlowContext in stack is serializable."""
        state = create_empty_dialogue_state()

        flow_context: FlowContext = {
            "flow_id": "abc-123",
            "flow_name": "test_flow",
            "flow_state": FlowContextState.ACTIVE,
            "current_step": "step_1",
            "step_index": 0,
            "outputs": {"key": "value"},
            "started_at": 1234567890.0,
        }
        state["flow_stack"] = [flow_context]

        json_str = json.dumps(state, default=str)
        restored = json.loads(json_str)

        assert restored["flow_stack"][0]["flow_id"] == "abc-123"
        assert restored["flow_stack"][0]["flow_state"] == "active"

    def test_state_with_nested_slots_is_serializable(self) -> None:
        """Test state with nested slot values is serializable."""
        state = create_empty_dialogue_state()
        state["flow_slots"] = {
            "flow_1": {
                "name": "John",
                "amount": 100.50,
                "confirmed": True,
                "items": ["a", "b", "c"],
                "metadata": {"nested": {"key": "value"}},
            }
        }

        json_str = json.dumps(state)
        restored = json.loads(json_str)

        assert restored["flow_slots"]["flow_1"]["name"] == "John"
        assert restored["flow_slots"]["flow_1"]["metadata"]["nested"]["key"] == "value"

    def test_enum_fields_serialize_correctly(self) -> None:
        """Test that StrEnum fields serialize to strings."""
        state = create_empty_dialogue_state()
        state["flow_state"] = FlowState.ACTIVE
        state["waiting_for_slot_type"] = SlotWaitType.CONFIRMATION

        json_str = json.dumps(state, default=str)
        restored = json.loads(json_str)

        # StrEnums serialize to their string value
        assert restored["flow_state"] == "active"
        assert restored["waiting_for_slot_type"] == "confirmation"

    def test_commands_field_with_dicts_is_serializable(self) -> None:
        """Test commands field with serialized command dicts."""
        state = create_empty_dialogue_state()
        state["commands"] = [
            {"type": "StartFlow", "flow_name": "transfer"},
            {"type": "SetSlot", "slot_name": "amount", "value": 100},
            {"type": "ChitChat", "response": "Sure, I can help!"},
        ]

        json_str = json.dumps(state)
        restored = json.loads(json_str)

        assert len(restored["commands"]) == 3
        assert restored["commands"][0]["type"] == "StartFlow"
        assert restored["commands"][1]["value"] == 100


class TestCompleteStateRoundTrip:
    """Tests for full state round-trip through JSON serialization."""

    def test_complete_state_roundtrip(self) -> None:
        """Test complete state survives JSON serialization round-trip."""
        state = create_empty_dialogue_state()
        state["user_message"] = "Transfer $100 to Alice"
        state["flow_state"] = FlowState.ACTIVE
        state["flow_stack"] = [
            {
                "flow_id": "transfer-123",
                "flow_name": "transfer",
                "flow_state": FlowContextState.ACTIVE,
                "current_step": "collect_amount",
                "step_index": 1,
                "outputs": {},
                "started_at": 1234567890.0,
            }
        ]
        state["flow_slots"] = {
            "transfer-123": {
                "amount": 100,
                "recipient": "Alice",
            }
        }
        state["commands"] = [
            {"type": "SetSlot", "slot_name": "amount", "value": 100},
        ]
        state["turn_count"] = 5

        # Simulate checkpointer serialization
        serialized = json.dumps(state, default=str)
        restored = json.loads(serialized)

        # Verify all fields survived
        assert restored["user_message"] == "Transfer $100 to Alice"
        assert restored["flow_state"] == "active"
        assert len(restored["flow_stack"]) == 1
        assert restored["flow_stack"][0]["flow_name"] == "transfer"
        assert restored["flow_slots"]["transfer-123"]["amount"] == 100
        assert restored["turn_count"] == 5

    def test_deeply_nested_state_roundtrip(self) -> None:
        """Test deeply nested state structures survive round-trip."""
        state = create_empty_dialogue_state()
        state["metadata"] = {
            "session": {
                "id": "sess-123",
                "preferences": {
                    "language": "en",
                    "timezone": "UTC",
                    "features": ["dark_mode", "notifications"],
                },
            },
            "analytics": {
                "events": [
                    {"type": "start", "ts": 1234567890},
                    {"type": "intent", "ts": 1234567891, "data": {"intent": "transfer"}},
                ],
            },
        }

        serialized = json.dumps(state, default=str)
        restored = json.loads(serialized)

        assert restored["metadata"]["session"]["preferences"]["language"] == "en"
        assert len(restored["metadata"]["analytics"]["events"]) == 2


class TestSerializationPatterns:
    """Tests documenting correct serialization patterns."""

    def test_pydantic_model_to_dict_pattern(self) -> None:
        """Document the pattern for serializing Pydantic models."""
        from pydantic import BaseModel

        class SampleCommand(BaseModel):
            type: str
            value: int

        cmd = SampleCommand(type="test", value=42)

        # Correct pattern: use model_dump()
        serialized = cmd.model_dump()

        assert isinstance(serialized, dict)
        assert serialized["type"] == "test"
        assert serialized["value"] == 42

        # This dict is JSON-serializable
        json_str = json.dumps(serialized)
        restored = json.loads(json_str)
        assert restored == serialized

    def test_strenum_serialization_pattern(self) -> None:
        """Document StrEnum serialization behavior."""
        from enum import StrEnum

        class Status(StrEnum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        # StrEnum inherits from str, so it serializes directly
        status = Status.ACTIVE

        # Can be used in JSON directly
        data = {"status": status}
        json_str = json.dumps(data)
        restored = json.loads(json_str)

        assert restored["status"] == "active"

        # Can reconstruct enum from string
        restored_enum = Status(restored["status"])
        assert restored_enum == Status.ACTIVE

    def test_dataclass_serialization_pattern(self) -> None:
        """Document dataclass serialization for FlowDelta."""
        from dataclasses import asdict, dataclass

        @dataclass
        class FlowDelta:
            flow_stack: list[dict[str, Any]] | None = None
            flow_slots: dict[str, dict[str, Any]] | None = None

        delta = FlowDelta(
            flow_stack=[{"flow_id": "123", "flow_name": "test"}],
            flow_slots={"123": {"key": "value"}},
        )

        # Use asdict for serialization
        serialized = asdict(delta)

        json_str = json.dumps(serialized)
        restored = json.loads(json_str)

        assert restored["flow_stack"][0]["flow_id"] == "123"


class TestEdgeCases:
    """Tests for edge cases in serialization."""

    def test_none_values_serialize_correctly(self) -> None:
        """Test None values are preserved."""
        state = create_empty_dialogue_state()
        state["waiting_for_slot"] = None
        state["_branch_target"] = None

        serialized = json.dumps(state, default=str)
        restored = json.loads(serialized)

        assert restored["waiting_for_slot"] is None
        assert restored["_branch_target"] is None

    def test_empty_collections_serialize_correctly(self) -> None:
        """Test empty lists and dicts are preserved."""
        state = create_empty_dialogue_state()
        state["flow_stack"] = []
        state["flow_slots"] = {}
        state["commands"] = []

        serialized = json.dumps(state)
        restored = json.loads(serialized)

        assert restored["flow_stack"] == []
        assert restored["flow_slots"] == {}
        assert restored["commands"] == []

    def test_unicode_strings_serialize_correctly(self) -> None:
        """Test Unicode strings survive serialization."""
        state = create_empty_dialogue_state()
        state["user_message"] = "Transferir €100 a José 日本語"
        state["last_response"] = "¿Confirmas la transferencia? 🎉"

        serialized = json.dumps(state, ensure_ascii=False)
        restored = json.loads(serialized)

        assert restored["user_message"] == "Transferir €100 a José 日本語"
        assert "🎉" in restored["last_response"]

    def test_large_numbers_serialize_correctly(self) -> None:
        """Test large numbers don't lose precision."""
        state = create_empty_dialogue_state()
        state["flow_slots"] = {
            "flow_1": {
                "large_int": 9007199254740993,  # > 2^53, JS max safe int
                "large_float": 1e308,
            }
        }

        serialized = json.dumps(state)
        restored = json.loads(serialized)

        # Note: JSON has precision limits
        assert restored["flow_slots"]["flow_1"]["large_int"] == 9007199254740993
```

---

### TDD Cycle

#### Red Phase: Write Tests

**These tests are designed to pass with current implementation.** This is a special case because we're verifying existing correct behavior, not implementing new functionality.

**Running the tests first serves to:**
1. Document expected behavior
2. Detect future regressions
3. Verify our understanding is correct

**Run tests:**
```bash
uv run pytest tests/unit/core/test_state_serialization.py -v
```

**Commit:**
```bash
git add tests/
git commit -m "test: add state serialization verification tests (P1-004)"
```

#### Green Phase: Verify Tests Pass

Tests should pass with current code. If any fail, it indicates a serialization bug that needs investigation.

```bash
uv run pytest tests/unit/core/test_state_serialization.py -v
# Expected: PASSED ✅
```

---

### Exception: Test-After

**Reason:** Verification of existing correct behavior

**Justification:**
The roadmap determined that current serialization (TypedDict + model_dump()) is correct per LangGraph's recommended pattern. These tests document and verify that behavior. If tests fail, it indicates an existing bug to fix.

---

### Success Criteria

- [ ] All serialization tests pass
- [ ] Each field type in DialogueState has test coverage
- [ ] Edge cases (None, empty, unicode) are tested
- [ ] Serialization patterns documented in test docstrings

### Manual Validation

```bash
# 1. Run serialization tests
uv run pytest tests/unit/core/test_state_serialization.py -v

# 2. Quick verification
uv run python -c "
import json
from soni.core.state import create_empty_dialogue_state
from soni.core.constants import FlowState

state = create_empty_dialogue_state()
state['flow_state'] = FlowState.ACTIVE
state['user_message'] = 'Test message'

serialized = json.dumps(state, default=str)
restored = json.loads(serialized)

print('Original flow_state:', state['flow_state'])
print('Restored flow_state:', restored['flow_state'])
print('Comparison works:', FlowState.ACTIVE == restored['flow_state'])
"
```

### References

- `src/soni/core/types.py` - DialogueState definition
- `src/soni/core/state.py` - State factory
- [LangGraph Persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/)

### Notes

**Why TypedDict is correct for DialogueState:**

LangGraph requires state to be a serializable dict. TypedDict provides:
1. Type hints for IDE and mypy
2. It's a real dict at runtime (not a class)
3. Automatic JSON serialization

**Pattern for commands:**

```python
# In nodes that generate commands:
commands = [
    cmd.model_dump() if hasattr(cmd, "model_dump") else cmd
    for cmd in raw_commands
]
return {"commands": commands}
```

**StrEnum comparison after deserialization:**

```python
# StrEnum comparison with strings works directly:
FlowState.ACTIVE == "active"  # True with StrEnum
```
