# Hybrid Slot Collection Strategy

**Document Version**: 1.0
**Last Updated**: 2025-12-02
**Status**: ⚠️ **SUPERSEDED** by Document 19

> **WARNING**: This document proposed a 3-tier approach with pattern extraction that was found to be too simplistic for realistic user behavior. See `19-realistic-slot-collection-strategy.md` for the **final design** using DSPy-based lightweight collector.
>
> **Reason for superseding**: Tier 1 (regex pattern extraction) cannot distinguish between slot values and intent changes/questions/corrections. DSPy-based approach in document 19 handles realistic human communication patterns.
>
> **Historical value**: Shows the evolution of thinking from simple pattern matching to intelligent classification.

## Problem Statement

The original "Direct Slot Mapping" design in `00-quick-reference.md` is **too simplistic** and doesn't handle realistic user behavior:

```
System: "Where would you like to fly from?"
User: "Actually, I changed my mind, I want to cancel"
  → Direct mapping would incorrectly set: slots["origin"] = "Actually, I changed my mind..."
```

**Core Issue**: Users don't always provide simple, direct answers. They may:
1. Change their intent mid-flow
2. Provide multiple slots at once
3. Ask questions
4. Correct previous values
5. Give ambiguous values needing normalization

---

## Revised Approach: Smart Hybrid Strategy

Instead of binary "Direct Mapping vs NLU", implement a **tiered approach**:

### Tier 1: Pattern-Based Quick Validation (Fastest)

For **unambiguous, well-formatted values**, use pattern matching:

```python
async def try_pattern_extraction(
    user_msg: str,
    slot_name: str,
    slot_config: SlotConfig,
) -> tuple[bool, Any | None]:
    """
    Try to extract slot value using patterns (no LLM).

    Returns:
        (success, value) tuple
    """

    # Example: City names (simple check)
    if slot_config.type == "city":
        # Check if it's a simple city name (2-20 chars, letters/spaces)
        if re.match(r'^[A-Za-z\s]{2,20}$', user_msg.strip()):
            return (True, user_msg.strip())

    # Example: Dates (check if date-like)
    if slot_config.type == "date":
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # 2025-12-15
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # 12/15/2025
            r'tomorrow',
            r'next (monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        ]
        for pattern in date_patterns:
            if re.search(pattern, user_msg.lower()):
                # Still need normalization, but likely a date
                return (True, user_msg.strip())

    # Example: Numbers
    if slot_config.type == "integer":
        try:
            value = int(user_msg.strip())
            return (True, value)
        except ValueError:
            pass

    # Pattern extraction failed
    return (False, None)
```

**When to use**: Message is very simple and matches expected format exactly.

**Cost**: <1ms (regex)
**Accuracy**: ~95% for simple cases, 0% for complex

---

### Tier 2: Lightweight NLU (Slot Extraction Only)

For **ambiguous but likely slot values**, use **focused NLU**:

```python
async def extract_slot_value_lightweight(
    user_msg: str,
    slot_name: str,
    slot_config: SlotConfig,
    context: dict[str, Any],
) -> tuple[bool, Any | None]:
    """
    Extract slot value using lightweight NLU (slot extraction only, no intent).

    This is cheaper than full NLU because:
    - No intent classification needed
    - No multi-slot extraction
    - Focused prompt (just extract THIS slot)
    """

    # Build focused prompt
    prompt = f"""Extract the value for '{slot_name}' from the user's message.

User message: "{user_msg}"

Context:
- Slot type: {slot_config.type}
- Expected format: {slot_config.description}
- We just asked: "{context.get('last_prompt', '')}"

If the message contains the {slot_name}, extract it.
If the message is a question, intent change, or doesn't contain the value, return null.

Output format: {{"value": "extracted_value" or null, "confidence": 0.0-1.0}}
"""

    # Call LLM with minimal prompt (cheap)
    response = await llm.generate(prompt, max_tokens=50)
    result = json.loads(response)

    if result["confidence"] > 0.7:
        return (True, result["value"])
    else:
        # Not confident, fall back to full NLU
        return (False, None)
```

**When to use**: Pattern extraction failed, but message looks like it might contain the slot value.

**Cost**: ~100ms, ~150 tokens (much cheaper than full NLU)
**Accuracy**: ~85-90%

---

### Tier 3: Full NLU (Intent + Multi-Slot Extraction)

For **complex messages or intent changes**, use **full NLU**:

```python
async def full_nlu_extraction(
    user_msg: str,
    context: NLUContext,
) -> NLUResult:
    """
    Full NLU: intent detection + multi-slot extraction.

    Use when:
    - Lightweight extraction failed
    - Message contains intent markers
    - Multiple slots might be present
    - User might be changing intent
    """

    return await nlu_provider.predict(
        user_message=user_msg,
        dialogue_history=context.dialogue_history,
        current_slots=context.current_slots,
        available_actions=context.available_actions,
        available_flows=context.available_flows,
        current_flow=context.current_flow,
        expected_slots=context.expected_slots,
    )
```

**When to use**: Lightweight NLU failed or message is complex.

**Cost**: ~300ms, ~500 tokens (full cost)
**Accuracy**: ~95%+ (best)

---

## Complete Hybrid Strategy

### Decision Flow

```
User message received while WAITING_FOR_SLOT
  ↓
Check: Does message have intent markers?
  YES → Tier 3 (Full NLU) - User changing intent
  NO → Continue
  ↓
Tier 1: Try pattern extraction (regex, simple parsing)
  SUCCESS → Validate + Normalize → Done ✅
  FAIL → Continue
  ↓
Tier 2: Try lightweight NLU (slot extraction only)
  SUCCESS (confidence > 0.7) → Validate + Normalize → Done ✅
  FAIL (confidence < 0.7) → Continue
  ↓
Tier 3: Fall back to full NLU
  → Extract intent + all slots → Done ✅
```

### Implementation

```python
async def collect_slot_hybrid(
    user_msg: str,
    slot_name: str,
    slot_config: SlotConfig,
    state: DialogueState,
    context: RuntimeContext,
) -> dict[str, Any]:
    """
    Hybrid slot collection with tiered extraction.

    Tries progressively more expensive methods:
    1. Pattern extraction (fast, <1ms)
    2. Lightweight NLU (medium, ~100ms)
    3. Full NLU (slow, ~300ms)
    """

    # Pre-check: Intent markers?
    if _has_intent_markers(user_msg):
        # User is changing intent, go straight to full NLU
        logger.info("Intent markers detected, using full NLU")
        nlu_result = await _full_nlu_extraction(user_msg, state, context)
        return _process_nlu_result(nlu_result, state)

    # Tier 1: Pattern extraction
    logger.debug(f"Trying pattern extraction for slot '{slot_name}'")
    success, value = await _try_pattern_extraction(user_msg, slot_name, slot_config)

    if success:
        logger.info(f"Pattern extraction succeeded: {value}")
        # Validate
        if _validate_slot_value(slot_name, value, slot_config):
            # Normalize
            normalized = await _normalize_slot_value(slot_name, value, slot_config)
            return {
                "slots": {slot_name: normalized},
                "waiting_for_slot": None,
                "conversation_state": ConversationState.VALIDATING_SLOT,
            }
        else:
            # Pattern matched but validation failed
            logger.warning(f"Pattern extraction succeeded but validation failed for '{value}'")
            # Fall through to Tier 2

    # Tier 2: Lightweight NLU (slot extraction only)
    logger.debug(f"Trying lightweight NLU for slot '{slot_name}'")
    success, value = await _extract_slot_value_lightweight(
        user_msg,
        slot_name,
        slot_config,
        {"last_prompt": state.last_response},
    )

    if success:
        logger.info(f"Lightweight NLU succeeded: {value}")
        # Validate + normalize
        if _validate_slot_value(slot_name, value, slot_config):
            normalized = await _normalize_slot_value(slot_name, value, slot_config)
            return {
                "slots": {slot_name: normalized},
                "waiting_for_slot": None,
                "conversation_state": ConversationState.VALIDATING_SLOT,
            }
        else:
            # Fall through to Tier 3
            logger.warning(f"Lightweight NLU succeeded but validation failed")

    # Tier 3: Full NLU (fallback)
    logger.info(f"Falling back to full NLU")
    nlu_result = await _full_nlu_extraction(user_msg, state, context)
    return _process_nlu_result(nlu_result, state)
```

---

## Performance Analysis

### Typical 4-Turn Flow

**Scenario**: Book flight (origin, destination, date)

```
Turn 1: "I want to book a flight"
  → Full NLU (necessary for intent)
  → Cost: 300ms, 500 tokens

Turn 2: "New York"
  → Pattern extraction ✅ (simple city name)
  → Cost: <1ms, 0 tokens
  → Savings: 300ms, 500 tokens

Turn 3: "Los Angeles"
  → Pattern extraction ✅
  → Cost: <1ms, 0 tokens
  → Savings: 300ms, 500 tokens

Turn 4: "next Friday"
  → Pattern matches date-like ✅
  → Lightweight NLU for normalization (which exact date?)
  → Cost: 100ms, 150 tokens
  → Savings: 200ms, 350 tokens
```

**Total savings**: 800ms, 1350 tokens (vs always using full NLU)

### Complex Scenario: Intent Change

```
Turn 1: "I want to book a flight"
  → Full NLU
  → Cost: 300ms, 500 tokens

Turn 2: "Actually, I want to cancel my booking instead"
  → Intent markers detected ("actually", "cancel")
  → Skip Tier 1 & 2, go directly to Tier 3
  → Full NLU
  → Cost: 300ms, 500 tokens
  → NO SAVINGS (but correct behavior)
```

**Key**: System detects intent change and uses appropriate method.

### Ambiguous Value Scenario

```
Turn 1: "Book a flight"
  → Full NLU

Turn 2: "I'm leaving from New York and going to LA tomorrow"
  → Pattern extraction FAILS (multiple slots)
  → Lightweight NLU FAILS (multiple slots, confidence low)
  → Full NLU ✅ (extracts all 3 slots)
  → Cost: 300ms, 500 tokens
  → NO SAVINGS (but correct behavior - extracted 3 slots at once!)
```

**Key**: When user provides multiple slots, full NLU is appropriate.

---

## Revised Performance Estimates

### Best Case (Simple Answers)
- Pattern extraction: 99% of turns
- **Savings**: 95% latency, 90% tokens

### Typical Case (Mix)
- Pattern extraction: 60%
- Lightweight NLU: 20%
- Full NLU: 20%
- **Savings**: 60% latency, 50% tokens

### Worst Case (Complex)
- Full NLU: 100%
- **Savings**: 0% (but correct behavior)

---

## Implementation Priority

### MVP (Recommended for Initial Implementation)

**Use only Tier 3 (Full NLU)** initially:
- Correct behavior for all cases
- No pattern extraction bugs
- No lightweight NLU complexity

**Why**: Get the system working correctly first.

### Phase 2 Optimization

Add **Tier 1 (Pattern Extraction)** for:
- City names (simple regex)
- Numbers
- Yes/no answers

**Impact**: 40-50% savings in simple cases

### Phase 3 Optimization

Add **Tier 2 (Lightweight NLU)** for:
- Date normalization
- Ambiguous values
- Complex city names

**Impact**: Additional 10-20% savings

---

## Revised Quick Reference Entry

Replace the overly simplistic "Direct Slot Mapping" with:

```markdown
### 4. Hybrid Slot Collection (REVISED)

**What**: Use tiered extraction strategy based on message complexity
**Why**: Balance speed (pattern matching) with accuracy (NLU)

**Tier 1** - Pattern Extraction (<1ms):
- Simple values: "Boston", "42", "yes"
- Regex-based matching
- ~60% of simple responses

**Tier 2** - Lightweight NLU (~100ms):
- Ambiguous but likely slot values
- Slot extraction only (no intent)
- ~20% of responses

**Tier 3** - Full NLU (~300ms):
- Complex messages
- Intent changes
- Multiple slots
- ~20% of responses (or 100% in MVP)

**Impact**:
- Best case: 95% faster (pattern extraction)
- Typical: 60% faster (mixed)
- Worst case: 0% faster but correct (full NLU when needed)
```

---

## Key Insight

**Original assumption**: "User answers what we asked" → Direct mapping works

**Reality**: "User may answer, ask, correct, or change intent" → Need smart hybrid

**Solution**: Start with full NLU (correct), optimize with pattern extraction for proven simple cases (fast).

---

## Recommendation

1. ✅ **Phase 1**: Use Full NLU always (correct behavior)
2. ✅ **Phase 2**: Add pattern extraction for proven simple cases (30% savings)
3. ✅ **Phase 3**: Add lightweight NLU for middle cases (additional 20% savings)

**Don't over-optimize prematurely.** Full NLU is already 70% better than the old system (which called NLU 4 times). Getting to 85-90% better can come later.

---

**Next**: Update `00-quick-reference.md` with this revised strategy
