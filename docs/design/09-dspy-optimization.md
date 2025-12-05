# Soni Framework - DSPy Optimization

## Overview

Soni uses DSPy to automatically optimize NLU prompts based on business metrics. This eliminates manual prompt engineering and enables systematic improvement of dialogue understanding.

## DSPy Fundamentals

### What is DSPy?

DSPy is a framework for programming with language models using:
- **Signatures**: Define input/output specifications
- **Modules**: Composable LM components
- **Optimizers**: Automatically improve prompts based on metrics
- **Compilation**: Generate optimized prompts from training data

### Why DSPy for Soni?

**Benefits**:
- **Automatic optimization**: No manual prompt engineering
- **Metric-driven**: Optimize for business KPIs (accuracy, F1, etc.)
- **Systematic improvement**: Reproducible, data-driven approach
- **Multiple optimizers**: Choose best for your use case

## Signature Design

### Structured Types with Pydantic

Soni uses structured Pydantic models for robust type safety and validation:

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Any
import dspy

class MessageType(str, Enum):
    """Type of user message."""
    SLOT_VALUE = "slot_value"
    INTENT_CHANGE = "intent_change"
    QUESTION = "question"
    CONFIRMATION = "confirmation"
    CONTINUE = "continue"

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
    """Current dialogue context."""
    current_slots: dict[str, Any] = Field(default_factory=dict, description="Filled slots")
    available_actions: list[str] = Field(default_factory=list, description="Available actions")
    available_flows: list[str] = Field(default_factory=list, description="Available flows")
    current_flow: str = Field(default="none", description="Active flow")
    expected_slots: list[str] = Field(default_factory=list, description="Expected slot names")
```

### Understanding Signature

Primary signature for general dialogue understanding with structured types:

```python
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

**Benefits of Structured Types**:
- ✅ Automatic validation via Pydantic
- ✅ Type safety throughout the pipeline
- ✅ Better IDE support and autocomplete
- ✅ Clearer data contracts
- ✅ No manual JSON parsing needed
- ✅ Field-level constraints (ge, le, etc.)
- ✅ Native conversation history with `dspy.History`

### Signature Best Practices

1. **Use Pydantic models**: Structured types instead of strings
2. **Use dspy.History**: Native conversation history support
3. **Clear descriptions**: Explain what each field means
4. **Reasoning field**: Help LLM show its work
5. **Confidence scores**: Enable fallback strategies
6. **Field constraints**: Use Pydantic validators (ge, le, etc.)

## Pydantic Validation in DSPy Signatures

### How DSPy Validates Structured Types

When you use Pydantic models in signatures, DSPy automatically validates LLM outputs:

```python
# 1. LLM generates output
# 2. DSPy adapter parses output
# 3. Pydantic validates and constructs model
# 4. If validation fails → ValidationError

# Example signature with validation
class NLUOutput(BaseModel):
    message_type: MessageType  # Must be valid enum value
    confidence: float = Field(ge=0.0, le=1.0)  # Must be in [0, 1]
    slots: list[SlotValue]  # Must be list of SlotValue objects
```

### Field-Level Constraints

Pydantic constraints are enforced automatically:

```python
from pydantic import BaseModel, Field

class SlotValue(BaseModel):
    name: str = Field(min_length=1, max_length=50)  # Length constraints
    confidence: float = Field(ge=0.0, le=1.0)  # Numeric bounds
    value: str = Field(pattern=r"^[A-Z][a-z]+$")  # Regex validation
```

**When LLM violates constraints**:

```python
# LLM outputs: confidence = 1.5  (invalid - exceeds 1.0)
# Result: ValidationError raised

# Your code should handle this:
try:
    prediction = await module.acall(...)
    result = prediction.result  # NLUOutput validated
except ValidationError as e:
    logger.error(f"LLM output validation failed: {e}")
    # Provide fallback result
    result = NLUOutput(
        message_type=MessageType.CONTINUE,
        command="unknown",
        slots=[],
        confidence=0.0,
        reasoning="Validation error"
    )
```

### Validation Performance

**Impact**:
- ✅ Minimal overhead (microseconds per validation)
- ✅ Catches errors early (before corrupt data enters system)
- ✅ Self-documenting (constraints visible in model definition)

**Best Practices**:
1. **Use constraints**: Add `ge`, `le`, `min_length`, etc. for safety
2. **Custom validators**: Use `@field_validator` for complex validation
3. **Handle ValidationError**: Always wrap predictions in try/except
4. **Log failures**: Track validation failures to improve prompts

### Custom Validators

```python
from pydantic import BaseModel, field_validator

class NLUOutput(BaseModel):
    command: str
    slots: list[SlotValue]
    confidence: float

    @field_validator('command')
    @classmethod
    def command_not_empty(cls, v: str) -> str:
        """Validate command is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("Command cannot be empty")
        return v.strip()

    @field_validator('slots')
    @classmethod
    def slots_must_be_unique(cls, v: list[SlotValue]) -> list[SlotValue]:
        """Validate no duplicate slot names."""
        names = [slot.name for slot in v]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate slot names not allowed")
        return v
```

**Important Note on Domain-Specific Validation**:

Pydantic validators should only validate **structural properties** (format, uniqueness, non-empty). Do NOT hardcode domain-specific commands in Pydantic models - this violates Zero-Leakage Architecture.

Domain validation (checking if command is valid for current dialogue) happens at **runtime** in the dialogue manager:

```python
async def validate_nlu_result(
    nlu_result: NLUOutput,
    context: DialogueContext
) -> bool:
    """Validate NLU result against current dialogue context.

    This is where domain-specific validation happens, NOT in Pydantic.
    """
    # Check if command is in available actions (from YAML configuration)
    if nlu_result.command not in context.available_actions:
        logger.warning(
            f"LLM generated unknown command: {nlu_result.command}. "
            f"Available: {context.available_actions}"
        )
        return False

    # Check if slot names match expected slots (from YAML configuration)
    expected_slot_names = set(context.expected_slots)
    actual_slot_names = {slot.name for slot in nlu_result.slots}

    if actual_slot_names - expected_slot_names:
        logger.warning(f"Unexpected slots: {actual_slot_names - expected_slot_names}")
        return False

    return True
```

This separation ensures:
- ✅ Framework remains domain-agnostic
- ✅ YAML defines available commands/slots (WHAT)
- ✅ Python validates against runtime context (HOW)
- ✅ Different dialogues can have different commands without code changes

### Validation in Training

During optimization, validation errors affect training:

```python
def safe_metric(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """Metric with validation error handling."""
    try:
        # Access structured result (may raise ValidationError)
        result: NLUOutput = prediction.result
        expected: NLUOutput = example.result

        # Compute metric
        return float(result.command == expected.command)

    except ValidationError as e:
        # Validation failure = metric score 0.0
        logger.debug(f"Validation failed during training: {e}")
        return 0.0
```

**Why this matters**: Optimizers learn to generate valid outputs because invalid outputs get score 0.0.

## Module Architecture

### SoniDU Module

```python
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
        from cachetools import TTLCache
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

### Understanding DSPy Module Call Chain

DSPy provides two calling patterns for modules:

**Sync Pattern**:
```python
# Public sync interface
prediction = module(user_message=msg, ...)  # Calls __call__()
    ↓
# Internal implementation
prediction = module.forward(user_message=msg, ...)  # Called by __call__()
```

**Async Pattern**:
```python
# Public async interface
prediction = await module.acall(user_message=msg, ...)  # Public async method
    ↓
# Internal implementation
prediction = await module.aforward(user_message=msg, ...)  # Called by acall()
```

**Best Practices**:
- ✅ Use `module()` or `module.acall()` in production code
- ⚠️ `forward()` and `aforward()` are internal - DSPy optimizers call them directly
- ✅ Implement both `forward()` (for sync optimizers) and `aforward()` (for runtime)

**Note**: While you can call `forward()` and `aforward()` directly, using the public interfaces (`__call__` and `acall`) enables proper callback handling and usage tracking.

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
        from soni.utils.hashing import generate_cache_key_from_dict

        return generate_cache_key_from_dict({
            "message": user_message,
            "history_length": len(history.messages),
            "context": context.model_dump(),
        })
```

### Predictor Types

DSPy provides different predictor types optimized for different scenarios.

#### Decision Guide

**When to use ChainOfThought**:
```python
self.predictor = dspy.ChainOfThought(DialogueUnderstanding)
```
- ✅ Complex understanding tasks (NLU, intent detection)
- ✅ Need high accuracy with reasoning
- ✅ Acceptable higher latency (adds reasoning step)
- ✅ **Recommended for Soni NLU**

**When to use Predict**:
```python
self.predictor = dspy.Predict(DialogueUnderstanding)
```
- ✅ Simple classification tasks
- ✅ Need lower latency
- ✅ Acceptable slightly lower accuracy
- ⚠️ No reasoning trace for debugging

**When to use ReAct**:
```python
self.predictor = dspy.ReAct(DialogueUnderstanding, tools=[search_tool, calc_tool])
```
- ✅ Need external tool calls (search, APIs, calculations)
- ✅ Multi-step reasoning with actions
- ⚠️ Highest latency (multiple LM calls + tool execution)

#### Comparison Table

| Predictor | Reasoning | Tools | Latency | Use Case |
|-----------|-----------|-------|---------|----------|
| ChainOfThought | Yes | No | Medium | Complex understanding |
| Predict | No | No | Low | Simple classification |
| ReAct | Yes | Yes | High | Tool-augmented tasks |

**Soni Recommendation**: Use `ChainOfThought` for NLU module to maximize accuracy and provide reasoning traces for debugging.

## Training Data

### Example Structure

```python
import dspy

# Create training example with structured types
example = dspy.Example(
    # Inputs
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

    # Expected output
    result=NLUOutput(
        message_type=MessageType.INTENT_CHANGE,
        command="book_flight",
        slots=[],
        confidence=0.95,
        reasoning="User explicitly states intent to book a flight"
    )
).with_inputs("user_message", "history", "context", "current_datetime")

# Build training set
trainset = [example1, example2, ...]
```

### Data Collection Strategies

**1. Manual Creation**:
```python
def create_training_data():
    """Create training examples manually with structured types"""
    examples = []

    # Intent detection examples
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
            message_type=MessageType.INTENT_CHANGE,
            command="book_flight",
            slots=[],
            confidence=0.95,
            reasoning="User explicitly states intent to book a flight"
        )
    ).with_inputs("user_message", "history", "context", "current_datetime"))

    # Slot extraction examples
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

    return examples
```

**2. From Logs**:
```python
def extract_training_data_from_logs():
    """Extract training data from conversation logs"""
    logs = load_conversation_logs()
    examples = []

    for log in logs:
        # Extract conversation history
        history = dspy.History(messages=log["history"])

        # Build context
        context = DialogueContext(
            current_slots=log["state"]["slots"],
            available_actions=log["state"]["available_actions"],
            available_flows=log["state"]["available_flows"],
            current_flow=log["state"]["current_flow"],
            expected_slots=log["state"]["expected_slots"]
        )

        # Build NLUOutput from metadata
        result = NLUOutput(
            message_type=MessageType(log["nlu_result"]["message_type"]),
            command=log["nlu_result"]["command"],
            slots=[
                SlotValue(**slot) for slot in log["nlu_result"]["slots"]
            ],
            confidence=log["nlu_result"]["confidence"],
            reasoning=log["nlu_result"].get("reasoning", "")
        )

        example = dspy.Example(
            user_message=log["user_message"],
            history=history,
            context=context,
            current_datetime=log["datetime"],
            result=result
        ).with_inputs("user_message", "history", "context", "current_datetime")

        examples.append(example)

    return examples
```

**3. Synthetic Generation**:
```python
async def generate_synthetic_examples():
    """Generate training data using LLM"""

    template = """
Generate 10 variations of a user wanting to book a flight.
Make them realistic and diverse (casual, formal, indirect, etc.)
"""

    variations = await lm.generate(template)

    examples = []
    for variation in variations:
        example = dspy.Example(
            user_message=variation,
            history=dspy.History(messages=[]),
            context=DialogueContext(
                current_slots={},
                available_actions=["book_flight"],
                available_flows=["book_flight"],
                current_flow="none",
                expected_slots=["origin", "destination", "departure_date"]
            ),
            current_datetime="2024-12-02T10:00:00",
            result=NLUOutput(
                message_type=MessageType.INTENT_CHANGE,
                command="book_flight",
                slots=[],
                confidence=0.9,
                reasoning=f"User wants to book flight: '{variation}'"
            )
        ).with_inputs("user_message", "history", "context", "current_datetime")

        examples.append(example)

    return examples
```

## Business Metrics

### Intent Accuracy

```python
def intent_accuracy(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """
    Measure intent detection accuracy with structured types.

    Returns 1.0 if command matches, 0.0 otherwise.
    """
    return float(prediction.result.command == example.result.command)
```

### Message Type Accuracy

```python
def message_type_accuracy(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """Measure message type classification accuracy."""
    return float(prediction.result.message_type == example.result.message_type)
```

### Slot Extraction F1

```python
def slot_extraction_f1(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """
    Measure slot extraction quality with F1 score.

    Accounts for both precision and recall with structured types.
    """
    # Extract slot names from structured SlotValue objects
    predicted_slots = {slot.name for slot in prediction.result.slots}
    expected_slots = {slot.name for slot in example.result.slots}

    # Calculate metrics
    tp = len(predicted_slots & expected_slots)  # True positives
    fp = len(predicted_slots - expected_slots)  # False positives
    fn = len(expected_slots - predicted_slots)  # False negatives

    if tp == 0:
        return 0.0

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    if precision + recall == 0:
        return 0.0

    f1 = 2 * (precision * recall) / (precision + recall)
    return f1
```

### Slot Value Accuracy

```python
def slot_value_accuracy(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """Measure accuracy of slot values (not just names)."""
    if not example.result.slots or not prediction.result.slots:
        return 0.0

    # Create dicts for comparison
    expected_dict = {slot.name: slot.value for slot in example.result.slots}
    predicted_dict = {slot.name: slot.value for slot in prediction.result.slots}

    # Count exact matches
    matches = sum(
        1 for name, value in expected_dict.items()
        if predicted_dict.get(name) == value
    )

    return matches / len(expected_dict) if expected_dict else 0.0
```

### Combined Metric

```python
def combined_metric(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """
    Combined metric for overall NLU quality with structured types.

    Weights:
    - 40% intent accuracy
    - 20% message type accuracy
    - 20% slot extraction F1
    - 20% slot value accuracy
    """
    intent_score = intent_accuracy(example, prediction)
    msg_type_score = message_type_accuracy(example, prediction)
    slot_f1 = slot_extraction_f1(example, prediction)
    slot_val_score = slot_value_accuracy(example, prediction)

    # Weighted combination
    return (
        0.4 * intent_score +
        0.2 * msg_type_score +
        0.2 * slot_f1 +
        0.2 * slot_val_score
    )
```

## Optimization Strategies

### MIPROv2 (Recommended)

Multi-stage optimization with prompt candidates:

```python
from dspy.teleprompt import MIPROv2

# Configure
lm = dspy.OpenAI(model="gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Create optimizer
optimizer = MIPROv2(
    metric=combined_metric,
    num_candidates=10,  # Generate 10 prompt variations
    init_temperature=1.0
)

# Run optimization
optimized_module = optimizer.compile(
    SoniDU(),
    trainset=trainset,
    num_trials=50,  # Try 50 different combinations
    max_bootstrapped_demos=4,  # Include up to 4 examples in prompt
    max_labeled_demos=4
)

# Save
optimized_module.save("soni_du_optimized.json")
```

**Use when**:
- You have 50+ training examples
- You want best accuracy
- You can afford longer optimization time (30-60 minutes)

### BootstrapFewShot

Learn from successful predictions:

```python
from dspy.teleprompt import BootstrapFewShot

optimizer = BootstrapFewShot(
    metric=combined_metric,
    max_bootstrapped_demos=8,  # Learn from 8 successful examples
    max_labeled_demos=4  # Include 4 provided examples
)

optimized_module = optimizer.compile(
    SoniDU(),
    trainset=trainset
)
```

**Use when**:
- You have 20-50 training examples
- You want faster optimization (5-10 minutes)
- Few-shot learning works for your task

### SIMBA

Similarity-based optimization:

```python
from dspy.teleprompt import SIMBA

optimizer = SIMBA(
    metric=combined_metric,
    num_iterations=10
)

optimized_module = optimizer.compile(
    SoniDU(),
    trainset=trainset,
    valset=valset  # Separate validation set
)
```

**Use when**:
- You have limited training data
- You want to explore prompt space
- You can provide validation set

## Optimization Workflow

### 1. Prepare Data

```python
# Load or create training data
trainset = load_training_data()  # 100 examples
valset = load_validation_data()  # 20 examples
testset = load_test_data()  # 30 examples

# Verify data quality
for example in trainset[:5]:
    print(f"Input: {example.user_message}")
    print(f"Expected: {example.result.command}")
    print()
```

## Training Data Size Guidelines

### Minimum Viable Datasets

| Optimizer | Minimum | Recommended | Optimal | Diminishing Returns |
|-----------|---------|-------------|---------|---------------------|
| BootstrapFewShot | 20 | 50-100 | 200 | >300 |
| MIPROv2 | 50 | 100-300 | 500 | >1000 |
| SIMBA | 10 | 50-100 | 200 | >400 |

### Data Quality vs Quantity

**Quality Factors** (in order of importance):

1. **Diversity**: Cover different intents, slot combinations, edge cases
2. **Accuracy**: Labels must be correct (intent, slots, confidence)
3. **Representativeness**: Match production distribution
4. **Completeness**: All required fields populated

**Decision Matrix**:

```python
# Scenario 1: High-quality data, small dataset (50 examples)
# → Use BootstrapFewShot
optimizer = BootstrapFewShot(metric=combined_metric, max_bootstrapped_demos=8)

# Scenario 2: Medium-quality data, medium dataset (200 examples)
# → Use MIPROv2 with validation split
optimizer = MIPROv2(metric=combined_metric, auto="light")

# Scenario 3: Low-quality data, large dataset (500+ examples)
# → First: clean and validate data
# → Then: use MIPROv2 with valset for quality filtering
trainset = validate_training_data(raw_trainset, signature)
optimizer = MIPROv2(metric=combined_metric, auto="medium")
```

### When to Collect More Data

**Collect more data if**:
- Metric not improving after 3-5 optimization rounds
- Poor performance on specific scenarios (check error analysis)
- Large gap between training and validation metrics (overfitting)

**How to expand dataset**:
1. **Targeted collection**: Focus on error patterns from analysis
2. **Synthetic generation**: Use LLM to generate variations (then human review)
3. **Production logs**: Extract and label real user interactions

### Data Split Strategy

```python
# General guideline: 70/15/15 split
total_examples = len(all_examples)
train_size = int(0.70 * total_examples)
val_size = int(0.15 * total_examples)

trainset = all_examples[:train_size]
valset = all_examples[train_size:train_size + val_size]
testset = all_examples[train_size + val_size:]

# Minimum sizes (override ratio if needed):
# - Training: ≥50 examples
# - Validation: ≥20 examples
# - Test: ≥30 examples
```

### 2. Configure DSPy

```python
import dspy

# Configure LLM
lm = dspy.OpenAI(
    model="gpt-4o-mini",
    temperature=0.0,  # Deterministic for optimization
    max_tokens=1000
)
dspy.configure(lm=lm)
```

### 3. Define Metric

```python
def soni_metric(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """Custom metric for Soni NLU"""

    # Command accuracy (most important)
    command_score = float(prediction.result.command == example.result.command)

    # Slot extraction F1
    slot_score = slot_extraction_f1(example, prediction)

    # Message type accuracy (includes digression detection via QUESTION type)
    msg_type_score = float(prediction.result.message_type == example.result.message_type)

    # Weighted combination
    return (
        0.5 * command_score +
        0.3 * slot_score +
        0.2 * msg_type_score
    )
```

### 4. Run Optimization

```python
from dspy.teleprompt import MIPROv2

# Create module
module = SoniDU()

# Create optimizer
optimizer = MIPROv2(
    metric=soni_metric,
    num_candidates=10,
    init_temperature=1.0
)

# Optimize
print("Starting optimization...")
optimized_module = optimizer.compile(
    module,
    trainset=trainset,
    num_trials=50,
    max_bootstrapped_demos=4,
    max_labeled_demos=4
)
print("Optimization complete!")
```

### 5. Evaluate

```python
def evaluate(module, dataset):
    """Evaluate module on dataset"""

    total = len(dataset)
    correct_commands = 0
    total_slot_f1 = 0.0

    for example in dataset:
        prediction = module(
            user_message=example.user_message,
            history=example.history,
            context=example.context,
            current_datetime=example.current_datetime
        )

        if prediction.result.command == example.result.command:
            correct_commands += 1

        total_slot_f1 += slot_extraction_f1(example, prediction)

    return {
        "command_accuracy": correct_commands / total,
        "avg_slot_f1": total_slot_f1 / total
    }

# Evaluate on test set
results = evaluate(optimized_module, testset)
print(f"Command Accuracy: {results['command_accuracy']:.2%}")
print(f"Avg Slot F1: {results['avg_slot_f1']:.2f}")
```

### 6. Save and Deploy

```python
# Save optimized module
optimized_module.save("soni_du_v1.json")

# Load in production
production_module = SoniDU()
production_module.load("soni_du_v1.json")

# Use
result = await production_module.aforward(user_message, context)
```

## Module Serialization and Deployment

### Save Modes

DSPy modules can be saved in two modes:

#### Mode 1: State-Only (Recommended)

Save only optimized parameters (prompts, demos) to JSON or pickle:

```python
# Save to JSON (recommended - human readable, safe)
optimized_module.save("soni_du_v1.json")

# Save to pickle (for non-JSON-serializable objects)
optimized_module.save("soni_du_v1.pkl")
```

**JSON Format**:
- ✅ Human-readable
- ✅ Safe to load (no code execution)
- ✅ Version control friendly
- ✅ Cross-platform compatible
- ⚠️ Requires module class to be available at load time

**Pickle Format**:
- ✅ Supports any Python object
- ⚠️ Can execute arbitrary code (security risk)
- ⚠️ Python version dependent
- ⚠️ Not human-readable

#### Mode 2: Full Program (Advanced)

Save entire module including architecture:

```python
# Save full program to directory
optimized_module.save(
    "soni_du_v1_full/",
    save_program=True,
    modules_to_serialize=[soni.du.modules]  # Serialize custom modules
)
```

**Use when**:
- Module architecture changes frequently
- Deploying to environment without source code
- Need perfect reproducibility

### Loading Saved Modules

```python
# Load state-only (requires class definition)
production_module = SoniDU()
production_module.load("soni_du_v1.json")

# Load full program (no class needed)
import dspy
production_module = dspy.load("soni_du_v1_full/")
```

### Deployment Best Practices

#### 1. Version Management

```python
import datetime

version = "v1.2"
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"soni_du_{version}_{timestamp}.json"

optimized_module.save(filename)

# Store metadata
metadata = {
    "version": version,
    "timestamp": timestamp,
    "metrics": {
        "command_accuracy": 0.94,
        "slot_f1": 0.89
    },
    "training_size": len(trainset),
    "optimizer": "MIPROv2"
}

import json
with open(f"soni_du_{version}_{timestamp}_metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)
```

#### 2. A/B Testing Deployment

```python
class ModuleRouter:
    """Route requests between module versions for A/B testing."""

    def __init__(self, module_a, module_b, split_ratio=0.5):
        self.module_a = module_a  # Current version
        self.module_b = module_b  # New version
        self.split_ratio = split_ratio

    async def predict(self, user_message, history, context):
        """Route to A or B based on split ratio."""
        import random

        if random.random() < self.split_ratio:
            return await self.module_a.predict(user_message, history, context)
        else:
            return await self.module_b.predict(user_message, history, context)
```

#### 3. Rollback Strategy

```python
# Keep last 3 versions for quick rollback
versions = [
    "soni_du_v1.2_20241204.json",  # Current
    "soni_du_v1.1_20241201.json",  # Previous
    "soni_du_v1.0_20241128.json",  # Stable
]

def load_module_version(version_index=0):
    """Load specific version (0=current, 1=previous, etc.)."""
    module = SoniDU()
    module.load(versions[version_index])
    return module
```

### Compatibility Considerations

```python
# Check version compatibility when loading
from packaging import version as pkg_version

def safe_load_module(path):
    """Load module with version compatibility check."""
    import json

    # Load metadata
    with open(path.replace(".json", "_metadata.json")) as f:
        metadata = json.load(f)

    # Check DSPy version compatibility
    import dspy
    saved_dspy_version = metadata.get("dspy_version", "3.0.0")
    current_dspy_version = dspy.__version__

    if pkg_version.parse(current_dspy_version) < pkg_version.parse(saved_dspy_version):
        logger.warning(
            f"Loading module saved with DSPy {saved_dspy_version}, "
            f"but current version is {current_dspy_version}"
        )

    # Load module
    module = SoniDU()
    module.load(path)
    return module
```

## Iterative Improvement

### Continuous Learning Loop

```python
async def continuous_improvement():
    """Continuous learning from production data"""

    # 1. Collect new examples from production
    new_examples = await collect_production_data()

    # 2. Human review and labeling
    labeled_examples = await human_review(new_examples)

    # 3. Add to training set
    trainset.extend(labeled_examples)

    # 4. Re-optimize
    optimizer = MIPROv2(metric=soni_metric)
    new_module = optimizer.compile(SoniDU(), trainset=trainset)

    # 5. A/B test
    improved = await ab_test(current_module, new_module, test_users)

    # 6. Deploy if better
    if improved:
        new_module.save("soni_du_v2.json")
        deploy_module("soni_du_v2.json")
```

### Error Analysis

```python
def analyze_errors(module, dataset):
    """Find common error patterns"""

    errors = []

    for example in dataset:
        prediction = module(
            user_message=example.user_message,
            history=example.history,
            context=example.context,
            current_datetime=example.current_datetime
        )

        if prediction.result.command != example.result.command:
            errors.append({
                "message": example.user_message,
                "expected": example.result.command,
                "predicted": prediction.result.command,
                "context": example.context
            })

    # Group by error type
    error_patterns = {}
    for error in errors:
        key = f"{error['expected']} → {error['predicted']}"
        if key not in error_patterns:
            error_patterns[key] = []
        error_patterns[key].append(error)

    # Print most common errors
    for pattern, examples in sorted(
        error_patterns.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:5]:
        print(f"\n{pattern}: {len(examples)} errors")
        for ex in examples[:3]:
            print(f"  - {ex['message']}")
```

## Error Handling in Optimization

### Common Errors and Solutions

#### 1. Pydantic Validation Errors

**Scenario**: LLM generates invalid structured output

```python
from pydantic import ValidationError

async def safe_predict(module, **inputs):
    """Predict with graceful error handling."""
    try:
        prediction = await module.acall(**inputs)
        return prediction.result
    except ValidationError as e:
        logger.error(f"Pydantic validation failed: {e}")
        # Fallback: return default result
        return NLUOutput(
            message_type=MessageType.CONTINUE,
            command="unknown",
            slots=[],
            confidence=0.0,
            reasoning=f"Validation error: {str(e)}"
        )
```

#### 2. Optimizer Failures

**Scenario**: Optimization fails to improve metric

```python
def optimize_with_fallback(student, trainset, valset):
    """Optimize with fallback to unoptimized module."""
    try:
        optimizer = MIPROv2(metric=combined_metric)
        optimized = optimizer.compile(
            student,
            trainset=trainset,
            valset=valset,
            num_trials=50
        )
        return optimized
    except Exception as e:
        logger.warning(f"Optimization failed: {e}, using unoptimized module")
        return student
```

#### 3. Training Data Quality Issues

**Scenario**: Examples don't match signature

```python
def validate_training_data(examples: list[dspy.Example], signature) -> list[dspy.Example]:
    """Validate training examples match signature."""
    valid_examples = []

    for idx, example in enumerate(examples):
        try:
            # Check all input fields present
            for field_name in signature.input_fields:
                if field_name not in example:
                    raise ValueError(f"Missing input field: {field_name}")

            # Check all output fields present
            for field_name in signature.output_fields:
                if field_name not in example:
                    raise ValueError(f"Missing output field: {field_name}")

            valid_examples.append(example)
        except Exception as e:
            logger.error(f"Invalid example {idx}: {e}")
            continue

    return valid_examples
```

### Error Handling Best Practices

1. **Graceful Degradation**: Always provide fallback behavior
2. **Detailed Logging**: Log errors with context for debugging
3. **Validation Early**: Validate training data before optimization
4. **Retry Logic**: Implement retries for transient failures
5. **User Feedback**: Provide clear error messages in English

## Best Practices

### 1. Start Simple

Begin with small training set (20-50 examples) and basic metric:

```python
# Start with command accuracy only
def simple_metric(example, prediction):
    return float(prediction.result.command == example.result.command)

# Use fast optimizer
optimizer = BootstrapFewShot(metric=simple_metric)
```

### 2. Iterate Based on Errors

Add examples that fix common errors:

```python
# Find errors
errors = find_errors(module, testset)

# Create examples for most common errors
for error in errors[:10]:
    trainset.append(create_example_from_error(error))

# Re-optimize
optimized_module = optimizer.compile(module, trainset=trainset)
```

### 3. Use Validation Set

Prevent overfitting:

```python
# Split data
trainset, valset, testset = split_data(all_examples, [0.7, 0.15, 0.15])

# Optimize with validation
optimizer = MIPROv2(metric=soni_metric)
optimized_module = optimizer.compile(
    module,
    trainset=trainset,
    valset=valset  # Used to select best prompts
)

# Final evaluation on test set
results = evaluate(optimized_module, testset)
```

### 4. Version Control Modules

```python
# Save with version
optimized_module.save(f"soni_du_{version}_{date}.json")

# Track metrics
save_metrics({
    "version": version,
    "date": date,
    "command_accuracy": results["command_accuracy"],
    "slot_f1": results["avg_slot_f1"],
    "training_size": len(trainset)
})
```

### DummyLM and Adapters

`DummyLM` requires an adapter to format outputs correctly. By default, it uses `ChatAdapter`:

```python
from dspy.utils.dummies import DummyLM

# Uses ChatAdapter by default
lm = DummyLM([{"result": {...}}])

# Custom adapter (for JSON or XML output)
from dspy.adapters import JSONAdapter
lm = DummyLM([{"result": {...}}], adapter=JSONAdapter())
```

**Why adapters matter**: Different adapters format field outputs differently (e.g., `[[## field ##]]` for ChatAdapter vs JSON structure for JSONAdapter). DummyLM needs to mimic the same format your real LM uses.

## Testing with DummyLM

### Overview

DSPy provides `DummyLM` for testing without making real LLM API calls. This is essential for fast, cost-free unit tests.

**Benefits**:
- No API calls or costs
- Deterministic responses
- Three operation modes
- Fast test execution
- Async support

### Three Operation Modes

#### Mode 1: Sequential Responses (List)

Returns responses in order from a list:

```python
from dspy.utils.dummies import DummyLM

# Define sequential responses with structured types
lm = DummyLM([
    {
        "result": {
            "message_type": "intent_change",
            "command": "book_flight",
            "slots": [],
            "confidence": 0.95,
            "reasoning": "User explicitly states intent to book a flight"
        }
    },
    {
        "result": {
            "message_type": "slot_value",
            "command": "book_flight",
            "slots": [
                {"name": "origin", "value": "Madrid", "confidence": 0.9}
            ],
            "confidence": 0.9,
            "reasoning": "User provides origin city"
        }
    }
])

dspy.configure(lm=lm)

# First call returns first response
# Second call returns second response
```

#### Mode 2: Input-Based Responses (Dict)

Returns responses based on input content matching:

```python
# Map inputs to specific responses
lm = DummyLM({
    "book a flight": {
        "result": {
            "message_type": "intent_change",
            "command": "book_flight",
            "slots": [],
            "confidence": 0.95,
            "reasoning": "Booking intent detected"
        }
    },
    "cancel": {
        "result": {
            "message_type": "intent_change",
            "command": "cancel_booking",
            "slots": [],
            "confidence": 0.9,
            "reasoning": "Cancellation intent detected"
        }
    }
})

dspy.configure(lm=lm)

# Input containing "book a flight" returns booking response
# Input containing "cancel" returns cancellation response
```

#### Mode 3: Follow Examples

Returns outputs from demo examples when input matches:

```python
lm = DummyLM([{"result": {}}], follow_examples=True)
dspy.configure(lm=lm)

predictor = dspy.ChainOfThought(DialogueUnderstanding)

# Provide example
demo = dspy.Example(
    user_message="test message",
    history=dspy.History(messages=[]),
    context=DialogueContext(),
    current_datetime="2024-12-02T10:00:00",
    result=NLUOutput(
        command="demo_command",
        message_type=MessageType.INTENT_CHANGE,
        slots=[],
        confidence=1.0,
        reasoning="From demo"
    )
)

# When input matches, returns demo output
result = predictor(
    user_message="test message",
    history=dspy.History(messages=[]),
    context=DialogueContext(),
    current_datetime="2024-12-02T10:00:00",
    demos=[demo]
)
```

### Test Example

```python
import pytest
import dspy
from dspy.utils.dummies import DummyLM

@pytest.fixture
def nlu_module() -> SoniDU:
    """Create NLU module for testing with DummyLM."""
    lm = DummyLM([
        {
            "result": {
                "message_type": "intent_change",
                "command": "book_flight",
                "slots": [],
                "confidence": 0.95,
                "reasoning": "User explicitly states intent"
            }
        }
    ])

    dspy.configure(lm=lm)
    return SoniDU()

@pytest.mark.asyncio
async def test_nlu_intent_detection(nlu_module: SoniDU):
    """Test intent detection with DummyLM."""
    # Arrange
    user_message = "I want to book a flight"
    history = dspy.History(messages=[])
    context = DialogueContext(
        current_slots={},
        available_actions=["book_flight", "cancel_booking"],
        available_flows=["book_flight", "cancel_booking"],
        current_flow="none",
        expected_slots=[]
    )

    # Act
    result: NLUOutput = await nlu_module.predict(
        user_message=user_message,
        history=history,
        context=context
    )

    # Assert
    assert result.command == "book_flight"
    assert result.message_type == MessageType.INTENT_CHANGE
    assert result.confidence > 0.7
```

### When to Use Each Mode

| Mode | Use Case | Example |
|------|----------|---------|
| Sequential (List) | Simple tests with predictable flow | Testing multi-turn conversations |
| Input-Based (Dict) | Tests with specific input/output pairs | Testing intent classification |
| Follow Examples | Testing few-shot behavior | Testing DSPy optimizers |

For more testing examples and patterns, see [06-nlu-system.md](06-nlu-system.md#testing).

## Summary

DSPy optimization in Soni provides:

1. **Automatic prompt optimization** - No manual engineering
2. **Metric-driven** - Optimize for business KPIs
3. **Multiple optimizers** - Choose best for your needs
4. **Iterative improvement** - Continuous learning from production
5. **Version control** - Track and deploy improvements

This enables systematic, data-driven improvement of dialogue understanding quality.

## Next Steps

- **[06-nlu-system.md](06-nlu-system.md)** - NLU architecture and implementation
- **[03-components.md](03-components.md)** - How NLU fits in overall system
- **[examples/](../../examples/)** - Working optimization examples

---

**Design Version**: v0.8 (Future State with Structured Types)
**Status**: Design specification for post-refactor implementation
**Current Implementation**: v0.5 (see README.md for production status)

**Note**: This document describes the target architecture using Pydantic structured types and dspy.History. The current v0.5 implementation uses JSON strings. This design will be implemented during the planned refactoring. See [`docs/design/README.md`](docs/design/README.md) for current production state.
