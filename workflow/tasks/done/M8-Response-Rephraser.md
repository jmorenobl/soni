# Soni v2 - Milestone 8: Response Rephraser

**Status**: Ready for Review
**Date**: 2025-12-21
**Type**: Design Document
**Depends On**: M0, M1, M2, M3, M4, M5, M6, M7

---

## 1. Objective

Add LLM-powered response polishing for more natural conversations:
- **ResponseRephraser**: Contextual rephrasing of template responses
- **Optional**: Configurable, can be disabled for determinism

---

## 2. User Story

### Without Rephraser (Template)

```
Bot: "Your balance is $1234.56"
```

### With Rephraser (Polished)

```
Bot: "Great news! Your current account balance is $1,234.56. Is there anything else you'd like to know?"
```

---

## 3. Key Concepts

### 3.1 Contextual Rephrasing

Input to rephraser:
- Template response: "Your balance is $1234.56"
- Conversation history (last N turns)
- User name/preferences (if available)
- Tone setting: formal, friendly, professional

Output:
- Polished response maintaining factual accuracy

### 3.2 Selective Rephrasing

Not all responses need rephrasing:
- **Rephrase**: Informational messages, greetings
- **Don't Rephrase**: Confirmations with specific values, errors

Configuration:
```python
class SayStepConfig(BaseModel):
    message: str
    rephrase: bool = True  # Default: rephrase enabled
```

### 3.3 Safety Constraints

The rephraser must:
- **Preserve all facts** (numbers, names, dates)
- **Not add information** not in template
- **Maintain consistent tone**

---

## 4. Legacy Code Reference

No direct legacy code - this is new functionality leveraging DSPy.

---

## 5. New Files

### 5.1 du/rephraser.py

```python
"""ResponseRephraser - DSPy module for polishing responses.

Follows DSPy pattern:
- aforward(): Async runtime implementation
- forward(): Sync implementation for optimization
- module.acall(): Runtime invocation
- module(): Optimization invocation
"""

import dspy
from soni.du.base import OptimizableDSPyModule


class RephraserSignature(dspy.Signature):
    """Polish a template response to sound more natural."""

    template_response: str = dspy.InputField(desc="Original template response")
    conversation_context: str = dspy.InputField(desc="Recent conversation history")
    tone: str = dspy.InputField(desc="Desired tone: friendly, professional, formal")

    polished_response: str = dspy.OutputField(
        desc="Polished response that preserves all factual information"
    )


class ResponseRephraser(OptimizableDSPyModule):
    """DSPy module for contextual response rephrasing.

    Usage:
        # Runtime (async)
        polished = await rephraser.acall(template, context)

        # Optimization (sync)
        polished = rephraser(template, context)
    """

    optimized_files = ["rephraser_miprov2.json"]
    default_use_cot = False  # Simple task, no CoT needed

    def __init__(self, tone: str = "friendly", use_cot: bool | None = None):
        super().__init__(use_cot=use_cot)
        self.tone = tone

    def _create_extractor(self, use_cot: bool) -> dspy.Module:
        if use_cot:
            return dspy.ChainOfThought(RephraserSignature)
        return dspy.Predict(RephraserSignature)

    async def aforward(self, template: str, context: str) -> str:
        """Async runtime implementation."""
        result = await self.extractor.acall(
            template_response=template,
            conversation_context=context,
            tone=self.tone,
        )
        return result.polished_response

    def forward(self, template: str, context: str) -> str:
        """Sync version for DSPy optimization."""
        result = self.extractor(
            template_response=template,
            conversation_context=context,
            tone=self.tone,
        )
        return result.polished_response"
        result = self.predictor(
            template_response=template,
            conversation_context=context,
            tone=self.tone,
        )
        return result.polished_response

    def forward(self, template: str, context: str) -> str:
        """Sync version for DSPy optimization."""
        result = self.predictor(
            template_response=template,
            conversation_context=context,
            tone=self.tone,
        )
        return result.polished_response
```

### 5.2 dm/nodes/respond.py (Update)

```python
"""Respond node with optional rephrasing."""

async def respond_node(state, runtime):
    response = state.get("response")

    if not response:
        return {}

    # Check if rephrasing enabled
    rephraser = runtime.context.get("rephraser")
    rephrase_enabled = runtime.context.config.settings.get("rephrase_responses", False)

    if rephraser and rephrase_enabled:
        context = _build_context(state)
        polished = await rephraser.acall(response, context)
        return {"response": polished}

    return {}


def _build_context(state: dict) -> str:
    """Build conversation context from recent messages."""
    messages = state.get("messages", [])[-5:]  # Last 5 messages
    return "\n".join([f"{m.type}: {m.content}" for m in messages])
```

### 5.3 config/settings.py (Update)

```python
class Settings(BaseModel):
    """Runtime settings."""
    rephrase_responses: bool = False  # Default: disabled
    rephrase_tone: str = "friendly"
```

---

## 6. TDD Tests (AAA Format)

### 6.1 Unit Tests

```python
# tests/unit/du/test_rephraser.py
@pytest.mark.asyncio
async def test_rephraser_preserves_facts():
    """Rephraser preserves numerical facts."""
    # Arrange
    rephraser = ResponseRephraser(tone="friendly", use_cot=False)

    # Act
    result = await rephraser.acall(
        template="Your balance is $1234.56",
        context="User: What's my balance?"
    )

    # Assert
    assert "1234.56" in result or "1,234.56" in result


@pytest.mark.asyncio
async def test_rephraser_changes_tone():
    """Rephraser applies specified tone."""
    # Arrange
    rephraser = ResponseRephraser(tone="professional", use_cot=False)

    # Act
    result = await rephraser.acall(
        template="Balance: $100",
        context=""
    )

    # Assert - Professional tone should be more formal
    assert len(result) > len("Balance: $100")
```

### 6.2 Integration Tests

```python
# tests/integration/test_m8_rephraser.py
@pytest.mark.asyncio
async def test_rephraser_enabled_polishes_response():
    """With rephraser enabled, responses are polished."""
    config = SoniConfig(
        settings=Settings(rephrase_responses=True),
        flows={"test": FlowConfig(steps=[
            SayStepConfig(step="greet", message="Hello")
        ])}
    )

    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("hi")
        # Response should be more than just "Hello"
        assert len(response) > 5


@pytest.mark.asyncio
async def test_rephraser_disabled_keeps_template():
    """With rephraser disabled, template is returned as-is."""
    config = SoniConfig(
        settings=Settings(rephrase_responses=False),
        flows={"test": FlowConfig(steps=[
            SayStepConfig(step="greet", message="Hello")
        ])}
    )

    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("hi")
        assert response == "Hello"
```

---

## 7. DSPy Optimization (Future)

The rephraser can be optimized with DSPy:

```python
# Example optimization
from dspy.teleprompt import MIPROv2

optimizer = MIPROv2()
optimized_rephraser = optimizer.compile(
    rephraser,
    trainset=training_examples,
    metric=factual_preservation_metric,
)
```

---

## 8. Success Criteria

- [ ] Rephraser polishes template responses
- [ ] All facts are preserved
- [ ] Configuration toggle works
- [ ] Tone setting applies correctly

---

## 9. Implementation Order

1. Write tests with mocked LM (RED)
2. Create `du/rephraser.py`
3. Update `dm/nodes/respond.py`
4. Add settings to config
5. Run tests (GREEN)

---

## Final: System Complete

After M8, Soni v2 has feature parity with Rasa CALM and additional advantages:
- ✅ DSPy prompt optimization
- ✅ LangGraph state persistence
- ✅ Streaming support
- ✅ Human-in-the-loop
