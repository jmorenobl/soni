# Phase 3: NLU System with DSPy

**Goal**: Production-ready NLU system with structured types and DSPy optimization support.

**Duration**: 3-4 days

**Dependencies**: Phase 1 (Core Foundation), Phase 2 (State Management)

## Overview

This phase implements the complete NLU pipeline using DSPy:
- Pydantic models for structured types
- DSPy signatures
- SoniDU module with async support
- Testing with DummyLM
- Training data preparation

## Tasks

### Task 3.1: Pydantic Models

**Status**: 📋 Backlog

**File**: `src/soni/du/models.py`

**What**: Define Pydantic models for NLU inputs and outputs.

**Why**: Structured types provide validation and type safety (see `docs/design/09-dspy-optimization.md`).

**Implementation**:

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Any

class MessageType(str, Enum):
    """Type of user message."""
    SLOT_VALUE = "slot_value"           # Direct answer to current prompt
    CORRECTION = "correction"            # Fixing a previous value
    MODIFICATION = "modification"        # Requesting to change a slot
    INTERRUPTION = "interruption"        # New intent/flow
    DIGRESSION = "digression"            # Question without flow change
    CLARIFICATION = "clarification"      # Asking for explanation
    CANCELLATION = "cancellation"        # Wants to stop
    CONFIRMATION = "confirmation"        # Yes/no to confirm prompt
    CONTINUATION = "continuation"        # General continuation

class SlotValue(BaseModel):
    """Extracted slot value with metadata."""
    name: str = Field(description="Slot name (must match expected_slots)")
    value: Any = Field(description="Extracted value")
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence")

class NLUOutput(BaseModel):
    """Structured NLU output."""
    message_type: MessageType = Field(description="Type of user message")
    command: str = Field(description="User's intent/command")
    slots: list[SlotValue] = Field(default_factory=list, description="Extracted slot values")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence")
    reasoning: str = Field(description="Step-by-step reasoning")

class DialogueContext(BaseModel):
    """Current dialogue context for NLU."""
    current_slots: dict[str, Any] = Field(default_factory=dict, description="Filled slots")
    available_actions: list[str] = Field(default_factory=list, description="Available actions")
    available_flows: list[str] = Field(default_factory=list, description="Available flows")
    current_flow: str = Field(default="none", description="Active flow")
    expected_slots: list[str] = Field(default_factory=list, description="Expected slot names")
```

**Tests**:

`tests/unit/test_nlu_models.py`:
```python
import pytest
from pydantic import ValidationError
from soni.du.models import NLUOutput, MessageType, SlotValue, DialogueContext

def test_nlu_output_valid():
    """Test NLUOutput with valid data."""
    # Arrange & Act
    output = NLUOutput(
        message_type=MessageType.INTERRUPTION,
        command="book_flight",
        slots=[],
        confidence=0.95,
        reasoning="User explicitly states booking intent"
    )

    # Assert
    assert output.command == "book_flight"
    assert output.confidence == 0.95

def test_nlu_output_confidence_validation():
    """Test NLUOutput validates confidence bounds."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        NLUOutput(
            message_type=MessageType.INTERRUPTION,
            command="test",
            slots=[],
            confidence=1.5,  # Invalid: > 1.0
            reasoning="test"
        )

def test_slot_value_structure():
    """Test SlotValue with valid data."""
    # Arrange & Act
    slot = SlotValue(
        name="origin",
        value="Madrid",
        confidence=0.9
    )

    # Assert
    assert slot.name == "origin"
    assert slot.value == "Madrid"

def test_dialogue_context_defaults():
    """Test DialogueContext has proper defaults."""
    # Arrange & Act
    context = DialogueContext()

    # Assert
    assert context.current_flow == "none"
    assert len(context.available_actions) == 0
```

**Completion Criteria**:
- [ ] All Pydantic models defined
- [ ] Field validators working
- [ ] Tests passing
- [ ] Mypy passes

---

### Task 3.2: DSPy Signatures

**Status**: 📋 Backlog

**File**: `src/soni/du/signatures.py`

**What**: Define DSPy signatures with structured types.

**Why**: Signatures define the input/output contract for NLU.

**Implementation**:

```python
import dspy
from soni.du.models import NLUOutput, DialogueContext

class DialogueUnderstanding(dspy.Signature):
    """Extract user intent and entities with structured types.

    Uses Pydantic models for robust type safety and validation.
    Uses dspy.History for proper conversation history management.
    """

    # Input fields with structured types
    user_message: str = dspy.InputField(
        desc="The user's current message"
    )
    history: dspy.History = dspy.InputField(
        desc="Conversation history with user messages and assistant responses"
    )
    context: DialogueContext = dspy.InputField(
        desc="Current dialogue context with all relevant information"
    )
    current_datetime: str = dspy.InputField(
        desc="Current datetime in ISO format for relative date resolution",
        default=""
    )

    # Output field with structured type
    result: NLUOutput = dspy.OutputField(
        desc="Complete NLU analysis with type-safe structure"
    )
```

**Tests**:

`tests/unit/test_nlu_signatures.py`:
```python
import pytest
import dspy
from soni.du.signatures import DialogueUnderstanding
from soni.du.models import DialogueContext

def test_signature_has_required_fields():
    """Test signature has all required input/output fields."""
    # Arrange
    sig = DialogueUnderstanding

    # Act
    input_fields = list(sig.input_fields.keys())
    output_fields = list(sig.output_fields.keys())

    # Assert
    assert "user_message" in input_fields
    assert "history" in input_fields
    assert "context" in input_fields
    assert "current_datetime" in input_fields
    assert "result" in output_fields
```

**Completion Criteria**:
- [ ] Signature defined
- [ ] All fields documented
- [ ] Tests verify structure

---

### Task 3.3: SoniDU Module

**Status**: 📋 Backlog

**File**: `src/soni/du/modules.py`

**What**: Implement SoniDU DSPy module with async support.

**Why**: Core NLU component with optimization capability.

**Implementation**:

```python
import dspy
from soni.du.signatures import DialogueUnderstanding
from soni.du.models import NLUOutput, DialogueContext
from cachetools import TTLCache

class SoniDU(dspy.Module):
    """
    Soni Dialogue Understanding module with structured types.

    This module provides:
    - Type-safe async interface for runtime
    - Sync interface for DSPy optimizers
    - Automatic prompt optimization via DSPy
    - Structured Pydantic models throughout
    """

    def __init__(self, cache_size: int = 1000, cache_ttl: int = 300) -> None:
        """Initialize SoniDU module.

        Args:
            cache_size: Maximum number of cached NLU results
            cache_ttl: Time-to-live for cache entries in seconds
        """
        super().__init__()  # CRITICAL: Must call super().__init__()

        # Create predictor with structured signature
        self.predictor = dspy.ChainOfThought(DialogueUnderstanding)

        # Optional caching layer
        self.nlu_cache: TTLCache[str, NLUOutput] = TTLCache(
            maxsize=cache_size,
            ttl=cache_ttl
        )

    def forward(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
        current_datetime: str = "",
    ) -> dspy.Prediction:
        """Sync forward pass for DSPy optimizers.

        Used during optimization/training with MIPROv2, BootstrapFewShot, etc.

        Args:
            user_message: User's input message
            history: Conversation history (dspy.History)
            context: Dialogue context with slots, actions, flows (DialogueContext)
            current_datetime: Current datetime in ISO format

        Returns:
            dspy.Prediction object with result field containing NLUOutput
        """
        return self.predictor(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=current_datetime,
        )

    async def aforward(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
        current_datetime: str = "",
    ) -> dspy.Prediction:
        """Async forward pass for production runtime.

        Called internally by acall(). Uses async LM calls via DSPy's adapter system.

        Args:
            Same as forward()

        Returns:
            dspy.Prediction object with result field containing NLUOutput
        """
        # DSPy's predictor.acall() handles async LM calls
        return await self.predictor.acall(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=current_datetime,
        )

    async def predict(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
    ) -> NLUOutput:
        """High-level async prediction method with caching.

        This is the main entry point for runtime NLU calls. Provides:
        - Structured type inputs (dspy.History, DialogueContext)
        - NLUOutput Pydantic model output
        - Automatic caching
        - Internal datetime management

        Args:
            user_message: User's input message
            history: Conversation history (dspy.History)
            context: Dialogue context (DialogueContext)

        Returns:
            NLUOutput with message_type, command, slots, confidence, and reasoning
        """
        from datetime import datetime

        # Calculate current datetime (encapsulation principle)
        current_datetime_str = datetime.now().isoformat()

        # Check cache
        cache_key = self._get_cache_key(user_message, history, context)

        if cache_key in self.nlu_cache:
            return self.nlu_cache[cache_key]

        # Call via acall() (public async method)
        prediction = await self.acall(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=current_datetime_str,
        )

        # Extract structured result (no parsing needed!)
        result: NLUOutput = prediction.result

        # Cache and return
        self.nlu_cache[cache_key] = result

        return result

    def _get_cache_key(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
    ) -> str:
        """Generate cache key from structured inputs."""
        import hashlib
        import json

        data = {
            "message": user_message,
            "history_length": len(history.messages),
            "context": context.model_dump(),
        }

        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
```

**Tests**:

`tests/unit/test_nlu_module.py`:
```python
import pytest
import dspy
from dspy.utils.dummies import DummyLM
from soni.du.modules import SoniDU
from soni.du.models import DialogueContext, MessageType, NLUOutput

@pytest.fixture
def dummy_lm():
    """Create DummyLM for testing."""
    lm = DummyLM([
        {
            "result": {
                "message_type": "interruption",
                "command": "book_flight",
                "slots": [],
                "confidence": 0.95,
                "reasoning": "User explicitly states intent"
            }
        }
    ])
    dspy.configure(lm=lm)
    return lm

@pytest.mark.asyncio
async def test_soni_du_predict(dummy_lm):
    """Test SoniDU.predict with DummyLM."""
    # Arrange
    module = SoniDU()
    user_message = "I want to book a flight"
    history = dspy.History(messages=[])
    context = DialogueContext(
        current_slots={},
        available_actions=["book_flight"],
        available_flows=["book_flight"],
        current_flow="none",
        expected_slots=[]
    )

    # Act
    result = await module.predict(user_message, history, context)

    # Assert
    assert isinstance(result, NLUOutput)
    assert result.command == "book_flight"
    assert result.message_type == MessageType.INTERRUPTION
    assert result.confidence > 0.7

@pytest.mark.asyncio
async def test_soni_du_caching(dummy_lm):
    """Test SoniDU caches results."""
    # Arrange
    module = SoniDU()
    user_message = "test"
    history = dspy.History(messages=[])
    context = DialogueContext()

    # Act
    result1 = await module.predict(user_message, history, context)
    result2 = await module.predict(user_message, history, context)

    # Assert - Should be same object (cached)
    assert result1 is result2
```

**Completion Criteria**:
- [ ] Module implemented
- [ ] Async/sync methods working
- [ ] Caching working
- [ ] Tests passing with DummyLM
- [ ] Mypy passes

---

### Task 3.4: NLU Provider Implementation

**Status**: 📋 Backlog

**File**: `src/soni/du/provider.py`

**What**: Create concrete NLU provider implementing INLUProvider.

**Why**: Concrete implementation of interface for use in runtime.

**Implementation**:

```python
from soni.core.interfaces import INLUProvider
from soni.core.types import DialogueState
from soni.du.modules import SoniDU
from soni.du.models import DialogueContext, NLUOutput
import dspy

class DSPyNLUProvider(INLUProvider):
    """NLU provider using DSPy SoniDU module."""

    def __init__(self, module: SoniDU) -> None:
        """Initialize provider with SoniDU module.

        Args:
            module: Optimized SoniDU module
        """
        self.module = module

    async def understand(
        self,
        user_message: str,
        dialogue_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Understand user message and return NLU result.

        Args:
            user_message: User's input
            dialogue_context: Context dict with fields:
                - current_slots: dict
                - available_actions: list[str]
                - available_flows: list[str]
                - current_flow: str
                - expected_slots: list[str]
                - history: list[dict] (optional)

        Returns:
            Serialized NLUOutput as dict
        """
        # Build structured context
        context = DialogueContext(
            current_slots=dialogue_context.get("current_slots", {}),
            available_actions=dialogue_context.get("available_actions", []),
            available_flows=dialogue_context.get("available_flows", []),
            current_flow=dialogue_context.get("current_flow", "none"),
            expected_slots=dialogue_context.get("expected_slots", [])
        )

        # Build history
        history_data = dialogue_context.get("history", [])
        history = dspy.History(messages=history_data)

        # Call NLU
        result: NLUOutput = await self.module.predict(
            user_message=user_message,
            history=history,
            context=context
        )

        # Return serialized
        return result.model_dump()
```

**Tests**:

`tests/unit/test_nlu_provider.py`:
```python
@pytest.mark.asyncio
async def test_dspy_nlu_provider(dummy_lm):
    """Test DSPyNLUProvider with DummyLM."""
    # Arrange
    module = SoniDU()
    provider = DSPyNLUProvider(module)

    dialogue_context = {
        "current_slots": {},
        "available_actions": ["book_flight"],
        "available_flows": ["book_flight"],
        "current_flow": "none",
        "expected_slots": [],
        "history": []
    }

    # Act
    result = await provider.understand("book a flight", dialogue_context)

    # Assert
    assert result["command"] == "book_flight"
    assert result["message_type"] == "interruption"
```

**Completion Criteria**:
- [ ] Provider implemented
- [ ] Interface compliance verified
- [ ] Tests passing

---

### Task 3.5: Training Data Examples

**Status**: 📋 Backlog

**File**: `examples/training/flight_booking_examples.py`

**What**: Create example training data for optimization.

**Why**: Demonstrate how to prepare training data for DSPy optimization.

**Implementation**:

```python
import dspy
from soni.du.models import NLUOutput, DialogueContext, MessageType, SlotValue

def create_flight_booking_examples() -> list[dspy.Example]:
    """Create training examples for flight booking domain."""

    examples = []

    # Example 1: Intent detection
    examples.append(dspy.Example(
        user_message="I want to book a flight",
        history=dspy.History(messages=[]),
        context=DialogueContext(
            current_slots={},
            available_actions=["book_flight", "search_flights"],
            available_flows=["book_flight"],
            current_flow="none",
            expected_slots=["origin", "destination", "departure_date"]
        ),
        current_datetime="2024-12-02T10:00:00",
        result=NLUOutput(
            message_type=MessageType.INTERRUPTION,
            command="book_flight",
            slots=[],
            confidence=0.95,
            reasoning="User explicitly states intent to book a flight"
        )
    ).with_inputs("user_message", "history", "context", "current_datetime"))

    # Example 2: Slot extraction
    examples.append(dspy.Example(
        user_message="From Madrid to Barcelona",
        history=dspy.History(messages=[
            {"user_message": "I want to book a flight", "result": {"command": "book_flight"}}
        ]),
        context=DialogueContext(
            current_slots={},
            available_actions=["book_flight"],
            available_flows=["book_flight"],
            current_flow="book_flight",
            expected_slots=["origin", "destination", "departure_date"]
        ),
        current_datetime="2024-12-02T10:00:00",
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[
                SlotValue(name="origin", value="Madrid", confidence=0.9),
                SlotValue(name="destination", value="Barcelona", confidence=0.9)
            ],
            confidence=0.9,
            reasoning="User provides origin and destination when expected"
        )
    ).with_inputs("user_message", "history", "context", "current_datetime"))

    # Add more examples...

    return examples
```

**Completion Criteria**:
- [ ] Example data created
- [ ] Covers major scenarios
- [ ] Documentation included

---

## Phase 3 Completion Checklist

Before proceeding to Phase 4, verify:

- [ ] All Task 3.x completed
- [ ] All tests passing
- [ ] Mypy passes: `uv run mypy src/soni`
- [ ] DummyLM tests working
- [ ] Training examples created
- [ ] Code committed

## Phase 3 Validation

```bash
# Type checking
uv run mypy src/soni/du

# Tests
uv run pytest tests/unit/test_nlu_models.py -v
uv run pytest tests/unit/test_nlu_signatures.py -v
uv run pytest tests/unit/test_nlu_module.py -v
uv run pytest tests/unit/test_nlu_provider.py -v

# Coverage
uv run pytest tests/unit/test_nlu*.py --cov=soni.du --cov-report=term-missing
```

## Next Steps

Once Phase 3 is complete:

1. Commit all changes
2. Optionally: Run optimization example
3. Proceed to **[04-phase-4-langgraph.md](04-phase-4-langgraph.md)**

---

**Phase**: 3 of 5
**Status**: 📋 Backlog
**Estimated Duration**: 3-4 days
