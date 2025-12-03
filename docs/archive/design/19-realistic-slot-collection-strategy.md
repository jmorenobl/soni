# Realistic Slot Collection Strategy

**Document Version**: 2.0 (Revised)
**Last Updated**: 2025-12-02
**Status**: ⚠️ **SUPERSEDED** - Design evolved to unified NLU approach

> **IMPORTANT**: This document describes a two-level slot collection approach with a lightweight collector and full NLU fallback. This design has been **superseded** by a simpler unified NLU approach where a single context-aware NLU handles all understanding tasks. This document is kept for historical reference.
>
> **Current design**: See [01-architecture-overview.md](01-architecture-overview.md), [03-message-processing.md](03-message-processing.md), and [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md) for the current unified NLU approach.

## Problem with Previous Approach

The 3-tier approach in `18-hybrid-slot-collection-strategy.md` had a critical flaw:

**Tier 1 (Pattern Extraction)** was too simplistic:
```python
if re.match(r'^[A-Za-z\s]{2,20}$', "Boston"):
    return "Boston"
```

This fails for realistic cases:
- "Actually, I want to cancel" → Matches pattern! ❌
- "What cities do you support?" → Matches pattern! ❌
- "I don't know" → Matches pattern! ❌

**Fundamental Issue**: You can't use simple regex to distinguish:
- Slot value: "New York"
- Intent change: "Actually, cancel"
- Question: "What cities?"
- Clarification: "Why do you need this?"
- Correction: "Change it to Boston"

---

## Revised Strategy: 2 Levels with DSPy

### Level 1: Lightweight Slot Extraction (DSPy-based)

Use a **focused DSPy module** that handles the complexity of human communication but is faster than full NLU.

#### What It Does

Extracts **one of these outcomes**:

1. **Slot value** extracted
2. **Intent change** detected
3. **Question** detected
4. **Clarification request** detected
5. **Correction** detected
6. **Ambiguous** (needs full NLU)

#### DSPy Signature

```python
class LightweightSlotExtraction(dspy.Signature):
    """
    Extract slot value OR detect digression from user message.

    This is LIGHTER than full NLU because:
    - Only considers ONE slot (not multi-slot extraction)
    - Only detects basic digressions (not full intent classification)
    - Focused context (what we're asking vs what user said)
    """

    # Inputs
    user_message: str = dspy.InputField(
        desc="User's message in response to slot request"
    )
    slot_being_collected: str = dspy.InputField(
        desc="Name of slot we're asking for (e.g., 'origin', 'departure_date')"
    )
    slot_prompt: str = dspy.InputField(
        desc="Question we just asked user (e.g., 'Where would you like to fly from?')"
    )
    conversation_context: str = dspy.InputField(
        desc="Brief context: current flow, previously collected slots"
    )

    # Outputs
    outcome_type: str = dspy.OutputField(
        desc="""Type of user response:
        - 'slot_value': User provided the requested slot value
        - 'intent_change': User wants to do something else (cancel, restart, etc.)
        - 'question': User is asking a question
        - 'clarification': User wants to know why we need this info
        - 'correction': User is correcting a previously provided value
        - 'ambiguous': Can't determine (need full NLU)
        """
    )
    extracted_value: str = dspy.OutputField(
        desc="If outcome_type='slot_value', the extracted value. Otherwise empty."
    )
    detected_intent: str = dspy.OutputField(
        desc="If outcome_type='intent_change', the new intent. Otherwise empty."
    )
    detected_question: str = dspy.OutputField(
        desc="If outcome_type='question', the question type. Otherwise empty."
    )
    confidence: float = dspy.OutputField(
        desc="Confidence in classification (0.0-1.0)"
    )
    reasoning: str = dspy.OutputField(
        desc="Brief explanation of classification"
    )
```

#### DSPy Module

```python
class LightweightSlotCollector(dspy.Module):
    """
    Lightweight slot collector using DSPy.

    Faster than full NLU because:
    1. Single slot focus (not multi-slot)
    2. Limited intent detection (just digressions)
    3. Smaller prompt context
    """

    def __init__(self):
        super().__init__()
        self.extract = dspy.ChainOfThought(LightweightSlotExtraction)

    async def aforward(
        self,
        user_message: str,
        slot_being_collected: str,
        slot_prompt: str,
        conversation_context: str,
    ) -> dspy.Prediction:
        """
        Extract slot value or detect digression.

        Returns:
            Prediction with outcome_type, extracted_value, etc.
        """
        return await self.extract.acall(
            user_message=user_message,
            slot_being_collected=slot_being_collected,
            slot_prompt=slot_prompt,
            conversation_context=conversation_context,
        )
```

#### Example Usage

```python
# Scenario 1: Simple value
result = await collector.aforward(
    user_message="New York",
    slot_being_collected="origin",
    slot_prompt="Where would you like to fly from?",
    conversation_context="Flow: book_flight. Collected: destination=LA",
)
# Result:
# outcome_type: "slot_value"
# extracted_value: "New York"
# confidence: 0.95

# Scenario 2: Intent change
result = await collector.aforward(
    user_message="Actually, I want to cancel",
    slot_being_collected="origin",
    slot_prompt="Where would you like to fly from?",
    conversation_context="Flow: book_flight. Collected: destination=LA",
)
# Result:
# outcome_type: "intent_change"
# detected_intent: "cancel_booking"
# confidence: 0.90

# Scenario 3: Question
result = await collector.aforward(
    user_message="What cities do you support?",
    slot_being_collected="origin",
    slot_prompt="Where would you like to fly from?",
    conversation_context="Flow: book_flight",
)
# Result:
# outcome_type: "question"
# detected_question: "supported_cities"
# confidence: 0.85

# Scenario 4: Correction
result = await collector.aforward(
    user_message="Change the origin to Boston",
    slot_being_collected="destination",
    slot_prompt="Where would you like to fly to?",
    conversation_context="Flow: book_flight. Collected: origin=New York",
)
# Result:
# outcome_type: "correction"
# extracted_value: "Boston"
# confidence: 0.90

# Scenario 5: Multiple slots (ambiguous for lightweight)
result = await collector.aforward(
    user_message="I'm flying from NYC to LA tomorrow",
    slot_being_collected="origin",
    slot_prompt="Where would you like to fly from?",
    conversation_context="Flow: book_flight",
)
# Result:
# outcome_type: "ambiguous"
# confidence: 0.60
# reasoning: "Multiple slots detected, need full NLU"
```

---

### Level 2: Full NLU (Existing)

When lightweight extraction returns:
- `outcome_type == "ambiguous"` (confidence < 0.7)
- `outcome_type == "intent_change"` BUT detected_intent is complex
- Any error or unexpected response

Use the existing full NLU module.

---

## Decision Flow

```
User message received (while WAITING_FOR_SLOT)
  ↓
Level 1: Lightweight Slot Extraction (DSPy)
  ↓
Outcome: slot_value (confidence > 0.8)
  → Extract value
  → Validate + Normalize
  → Update slot
  → Continue flow
  ↓
Outcome: intent_change (confidence > 0.8)
  → Route to new intent
  → Use full NLU for new flow
  ↓
Outcome: question (confidence > 0.8)
  → Answer question
  → Re-prompt for slot
  ↓
Outcome: clarification (confidence > 0.8)
  → Provide clarification
  → Re-prompt for slot
  ↓
Outcome: correction (confidence > 0.8)
  → Update corrected slot
  → Continue flow
  ↓
Outcome: ambiguous OR confidence < 0.8
  → Fall back to Level 2 (Full NLU)
```

---

## Implementation

### Lightweight Collector Integration

```python
class SlotCollectionManager:
    """
    Manages slot collection with two-level strategy.
    """

    def __init__(
        self,
        lightweight_collector: LightweightSlotCollector,
        full_nlu: INLUProvider,
    ):
        self.lightweight = lightweight_collector
        self.full_nlu = full_nlu

    async def collect_slot(
        self,
        user_msg: str,
        slot_name: str,
        state: DialogueState,
        context: RuntimeContext,
    ) -> SlotCollectionResult:
        """
        Collect slot using two-level strategy.
        """

        # Build context for lightweight extraction
        slot_config = context.get_slot_config(slot_name)
        conversation_context = self._build_context_string(state)

        # Level 1: Lightweight extraction
        logger.info(f"Attempting lightweight extraction for slot '{slot_name}'")
        result = await self.lightweight.aforward(
            user_message=user_msg,
            slot_being_collected=slot_name,
            slot_prompt=state.last_response,  # What we just asked
            conversation_context=conversation_context,
        )

        # Handle outcome based on type and confidence
        if result.confidence < 0.7 or result.outcome_type == "ambiguous":
            # Low confidence or explicitly ambiguous → Full NLU
            logger.info(f"Lightweight extraction uncertain (confidence={result.confidence}), "
                       f"falling back to full NLU")
            return await self._full_nlu_extraction(user_msg, state, context)

        # High confidence → Process outcome
        if result.outcome_type == "slot_value":
            # Validate and normalize
            value = result.extracted_value
            if self._validate_slot(slot_name, value, slot_config):
                normalized = await self._normalize_slot(slot_name, value, slot_config)
                return SlotCollectionResult(
                    success=True,
                    slot_name=slot_name,
                    slot_value=normalized,
                    action="continue",
                )
            else:
                # Validation failed → Re-prompt
                return SlotCollectionResult(
                    success=False,
                    slot_name=slot_name,
                    error=f"Invalid value for {slot_name}",
                    action="reprompt",
                )

        elif result.outcome_type == "intent_change":
            # User wants to do something else
            return SlotCollectionResult(
                success=False,
                action="route_to_intent",
                new_intent=result.detected_intent,
            )

        elif result.outcome_type == "question":
            # User asked a question
            answer = await self._answer_question(result.detected_question, context)
            return SlotCollectionResult(
                success=False,
                action="answer_and_reprompt",
                response=answer,
                slot_name=slot_name,
            )

        elif result.outcome_type == "clarification":
            # User wants to know why we need this
            clarification = await self._provide_clarification(slot_name, slot_config)
            return SlotCollectionResult(
                success=False,
                action="clarify_and_reprompt",
                response=clarification,
                slot_name=slot_name,
            )

        elif result.outcome_type == "correction":
            # User is correcting a previous slot
            # Need to determine WHICH slot to correct
            # This might need full NLU if ambiguous
            return await self._handle_correction(result, state, context)

        else:
            # Unknown outcome → Full NLU
            logger.warning(f"Unknown outcome type: {result.outcome_type}, using full NLU")
            return await self._full_nlu_extraction(user_msg, state, context)

    def _build_context_string(self, state: DialogueState) -> str:
        """Build brief context for lightweight extraction."""
        collected_slots = [f"{k}={v}" for k, v in state.slots.items()]
        return f"Flow: {state.current_flow}. Collected: {', '.join(collected_slots)}"

    async def _answer_question(self, question_type: str, context: RuntimeContext) -> str:
        """Answer user question about the system."""
        # Implementation: lookup answer based on question type
        answers = {
            "supported_cities": "We support flights from major US cities including New York, Los Angeles, Chicago, and more.",
            "why_needed": "We need this information to search for available flights for you.",
            # ... more answers
        }
        return answers.get(question_type, "I don't have that information right now.")

    async def _provide_clarification(
        self,
        slot_name: str,
        slot_config: SlotConfig,
    ) -> str:
        """Provide clarification about why we need this slot."""
        return f"I need your {slot_name} to {slot_config.purpose or 'complete your request'}."
```

---

## Performance Analysis

### Lightweight vs Full NLU

**Lightweight Extraction**:
- **Input tokens**: ~200 (focused context)
- **Output tokens**: ~50 (structured output)
- **Latency**: ~150ms
- **Cost**: ~$0.00004 per call

**Full NLU**:
- **Input tokens**: ~500 (full context, history, all slots)
- **Output tokens**: ~100 (intent + multi-slot extraction)
- **Latency**: ~300ms
- **Cost**: ~$0.00010 per call

**Savings**: ~50% latency, ~60% cost when lightweight succeeds

### Expected Distribution

**Simple slot collection** (60% of cases):
- Lightweight extracts slot successfully
- Savings: 50% latency, 60% tokens

**Digression** (30% of cases):
- Lightweight detects digression correctly
- Routes appropriately (answer question, handle intent change, etc.)
- No full NLU needed
- Savings: 50% latency, 60% tokens

**Ambiguous** (10% of cases):
- Lightweight confidence < 0.7
- Falls back to full NLU
- No savings, but correct behavior

**Overall**: ~45% savings in latency, ~55% savings in tokens

---

## Optimization with DSPy

The lightweight collector can be **optimized separately** from full NLU:

```python
# Optimization dataset: examples of each outcome type
train_data = [
    dspy.Example(
        user_message="New York",
        slot_being_collected="origin",
        slot_prompt="Where would you like to fly from?",
        conversation_context="Flow: book_flight",
        outcome_type="slot_value",
        extracted_value="New York",
        confidence=0.95,
    ).with_inputs("user_message", "slot_being_collected", "slot_prompt", "conversation_context"),

    dspy.Example(
        user_message="Actually, I want to cancel",
        slot_being_collected="origin",
        slot_prompt="Where would you like to fly from?",
        conversation_context="Flow: book_flight",
        outcome_type="intent_change",
        detected_intent="cancel_booking",
        confidence=0.90,
    ).with_inputs("user_message", "slot_being_collected", "slot_prompt", "conversation_context"),

    # ... more examples
]

# Optimize
optimizer = dspy.MIPROv2(
    metric=slot_extraction_accuracy,
    num_candidates=10,
)

optimized_collector = optimizer.compile(
    lightweight_collector,
    trainset=train_data,
)
```

This allows the lightweight module to get better at:
- Detecting intent changes
- Recognizing questions
- Handling corrections
- Knowing when to be uncertain (fallback to full NLU)

---

## Revised Quick Reference Entry

```markdown
### 4. Lightweight Slot Collection (FINAL)

**What**: Two-level strategy using DSPy for intelligent slot collection

**Level 1** - Lightweight DSPy Module (~150ms, ~250 tokens):
- Extracts slot value OR detects digression
- Handles: slot values, intent changes, questions, clarifications, corrections
- Falls back to Level 2 if ambiguous or low confidence

**Level 2** - Full NLU (~300ms, ~500 tokens):
- Complete intent + multi-slot extraction
- Used when lightweight is uncertain

**Impact**:
- Simple cases: 50% faster (lightweight succeeds)
- Digressions: 50% faster + correct handling
- Ambiguous: 0% faster but correct (uses full NLU)
- Overall: ~45% latency savings, ~55% token savings
```

---

## Key Advantages of This Approach

1. ✅ **Realistic**: Handles actual human communication (questions, intent changes, corrections)
2. ✅ **DSPy-based**: Uses LLM intelligence, not naive regex
3. ✅ **Optimizable**: Can improve accuracy with DSPy optimization
4. ✅ **Safe**: Falls back to full NLU when uncertain
5. ✅ **Efficient**: ~50% savings when successful
6. ✅ **Maintainable**: Single focused module, clear contract

---

## Implementation Priority

### Phase 1 (MVP)
- Use **only Level 2 (Full NLU)** for correctness
- Get system working end-to-end

### Phase 2
- Implement **Level 1 (Lightweight DSPy collector)**
- Collect real conversation data
- Optimize with DSPy

### Phase 3
- Fine-tune confidence thresholds
- Optimize fallback decision
- Add more digression types

---

**Status**: This is the FINAL design for slot collection
**Replaces**: Documents 18 (too simplistic regex approach)
