## Task: 335 - Refactor DialogueUnderstanding Signature Docstring

**ID de tarea:** 335
**Hito:** NLU Improvements
**Dependencias:** task-334 (documentation must exist for reference)
**Duración estimada:** 2-3 horas

### Objetivo

Refactor the `DialogueUnderstanding` signature docstring and field descriptions to be concise, clear, and focused on general task description rather than detailed instructions. Move verbose implementation details to documentation and training examples.

### Contexto

The current `DialogueUnderstanding` signature (src/soni/du/signatures.py:8-62) has a 40+ line docstring mixing task description with detailed edge case handling instructions. This is not aligned with DSPy best practices.

According to DSPy patterns (ref/dspy/dspy/predict/avatar/signatures.py), signatures should:
- Have short docstrings explaining the general task
- Use brief field descriptions (what the field IS, not instructions)
- Let the optimizer discover detailed rules through examples and optimization

Long, instruction-heavy docstrings can:
- Confuse the optimizer with too many specific rules
- Make prompts unnecessarily verbose
- Reduce flexibility for optimization
- Mix "what to do" (task) with "how to do it" (implementation)

### Entregables

- [ ] Refactored `DialogueUnderstanding` signature with concise docstring
- [ ] Simplified field descriptions (InputField/OutputField)
- [ ] Removed verbose CRITICAL/Exception instructions from docstring
- [ ] Docstring is self-contained (NO external file references - LLM won't see them)
- [ ] All tests still pass after refactoring

### Implementación Detallada

#### Paso 1: Refactor Main Docstring

**Archivo a modificar:** `src/soni/du/signatures.py`

**Current docstring (lines 9-40):**
```python
class DialogueUnderstanding(dspy.Signature):
    """Analyze user message in dialogue context to determine intent and extract all slot values.

    Extract ALL slot values mentioned in the message. Each slot gets an action
    (provide/correct/modify) based on whether it's new or changing an existing value.

    When available_flows contains flow descriptions, map user intent to the appropriate
    flow name based on semantic matching. For example, if available_flows contains
    {"book_flight": "Book a flight from origin to destination"}, and the user says
    "I want to book a flight", set command="book_flight".

    CRITICAL: Use context.conversation_state to determine message_type:
    - If context.conversation_state is "confirming" or "ready_for_confirmation":
      * The user is responding to a confirmation request
      ...
    [30 more lines of detailed instructions]
    """
```

**New concise docstring:**
```python
class DialogueUnderstanding(dspy.Signature):
    """Analyze user messages in dialogue context to determine intent and extract slot values.

    Given a user message and dialogue context (current flow, expected slots, conversation state),
    classify the message type and extract relevant information:
    - Slot values being provided or modified
    - Intent changes or confirmations
    - Digressions or clarification requests

    Use conversation_state to distinguish between different dialogue phases:
    - Slot collection: User providing values for prompted slots (waiting_for_slot)
    - Confirmation: User confirming or denying proposed values (confirming)
    - Interruption: User changing intent during conversation

    Extract slot values with appropriate actions:
    - provide: New slot value (slot not in current_slots)
    - correct: Fixing wrong value (reactive, user said "no, I meant...")
    - modify: Changing value (proactive, user said "can I change...")

    Map user intent to flow name using available_flows descriptions for semantic matching or just set it to None if the user is providing information.
    """
```

**Explicación:**
- Reduced from 40 lines to ~15 lines
- Focuses on WHAT the task is, not HOW to handle every edge case
- Keeps general principles (conversation_state usage, slot actions)
- Removes verbose CRITICAL/Exception instructions
- **NO reference to DATA_STRUCTURES.md** (file not sent to LLM)
- Self-contained with inline examples (waiting_for_slot, confirming)
- More readable and maintainable

#### Paso 2: Simplify Field Descriptions

**Current field descriptions (lines 43-56):**
```python
user_message: str = dspy.InputField(desc="The user's message to analyze")

history: dspy.History = dspy.InputField(desc="Conversation history")

context: DialogueContext = dspy.InputField(
    desc="Dialogue state: current_flow, expected_slots (use these EXACT names), "
    "current_slots (already filled - check for corrections), current_prompted_slot, "
    "conversation_state (CRITICAL: use this to determine if user is responding to confirmation), "
    "available_flows (dict mapping flow names to descriptions - use descriptions to map user intent). "
    "IMPORTANT: If conversation_state is 'confirming' or 'ready_for_confirmation', "
    "the user is responding to a confirmation request - set message_type to CONFIRMATION."
)

current_datetime: str = dspy.InputField(
    desc="Current datetime in ISO format for relative date resolution",
    default="",
)

result: NLUOutput = dspy.OutputField(
    desc="NLU analysis with message_type, optional command, and extracted slots"
)
```

**New simplified descriptions:**
```python
user_message: str = dspy.InputField(
    desc="User's input message to analyze"
)

history: dspy.History = dspy.InputField(
    desc="Conversation history (list of {role, content} messages)"
)

context: DialogueContext = dspy.InputField(
    desc="Current dialogue state including flow, slots, and conversation phase"
)

current_datetime: str = dspy.InputField(
    desc="Current datetime (ISO format) for temporal expressions",
    default="",
)

result: NLUOutput = dspy.OutputField(
    desc="Classified message with type, intent, slots, and confidence"
)
```

**Explicación:**
- Removed instruction-like phrases ("use these EXACT names", "CRITICAL", "IMPORTANT")
- Descriptions now say WHAT the field contains, not HOW to use it
- Kept minimal structure hints ("list of {role, content} messages")
- Much more concise and readable
- Instructions moved to DATA_STRUCTURES.md

#### Paso 3: Complete Refactored Signature

**Full refactored code (src/soni/du/signatures.py):**

```python
"""DSPy signatures for Dialogue Understanding.

For detailed developer documentation of data structures used in these signatures,
see DATA_STRUCTURES.md in this directory.

Note: Signature class docstrings are sent to the LLM and must be self-contained.
      DATA_STRUCTURES.md is for developer reference only.
"""

import dspy

from soni.du.models import DialogueContext, NLUOutput


class DialogueUnderstanding(dspy.Signature):
    """Analyze user messages in dialogue context to determine intent and extract slot values.

    Given a user message and dialogue context (current flow, expected slots, conversation state),
    classify the message type and extract relevant information:
    - Slot values being provided or modified
    - Intent changes or confirmations
    - Digressions or clarification requests

    Use conversation_state to distinguish between different dialogue phases:
    - Slot collection: User providing values for prompted slots (waiting_for_slot)
    - Confirmation: User confirming or denying proposed values (confirming)
    - Interruption: User changing intent during conversation

    Extract slot values with appropriate actions:
    - provide: New slot value (slot not in current_slots)
    - correct: Fixing wrong value (reactive, user said "no, I meant...")
    - modify: Changing value (proactive, user said "can I change...")

    Map user intent to flow name using available_flows descriptions for semantic matching or just set it to None if the user is providing information.
    """

    # Input fields with structured types
    user_message: str = dspy.InputField(
        desc="User's input message to analyze"
    )
    history: dspy.History = dspy.InputField(
        desc="Conversation history (list of {role, content} messages)"
    )
    context: DialogueContext = dspy.InputField(
        desc="Current dialogue state including flow, slots, and conversation phase"
    )
    current_datetime: str = dspy.InputField(
        desc="Current datetime (ISO format) for temporal expressions",
        default="",
    )

    # Output field with structured type
    result: NLUOutput = dspy.OutputField(
        desc="Classified message with type, intent, slots, and confidence"
    )
```

**Changes summary:**
- Docstring: 40 lines → 15 lines (62% reduction)
- File header: Added reference to DATA_STRUCTURES.md (for developers only)
- Field descriptions: Simplified from instruction-style to descriptive-style
- Removed: All CRITICAL, IMPORTANT, Exception markers
- Removed: Reference to DATA_STRUCTURES.md in signature docstring (LLM won't see it)
- Kept: General principles about task and data usage
- Added: Inline examples (waiting_for_slot, confirming) for clarity

#### Paso 4: Verify Integration Tests

**After refactoring, verify integration tests still work:**

The refactoring should not break functionality because:
- The signature structure remains the same (same fields, same types)
- Only docstrings changed (prompts may be different but should work)
- The optimizer will adapt to the new prompts

**Verification:**

```bash
# Run integration tests to verify NLU still works
uv run pytest tests/integration/test_dialogue_manager.py -v -k "test_" --tb=short

# Check if any tests fail due to signature changes
uv run pytest tests/integration/ -v --tb=short
```

If tests fail, it may indicate:
- Prompts are now too vague (need to add back some guidance)
- Examples/training data needed (create datasets for optimizer)
- Specific edge cases need explicit handling (add to training examples)

**Adjustment strategy:**
If integration tests fail significantly:
1. Check which scenarios fail
2. Add minimal guidance back to docstring if needed
3. Consider creating training examples for optimizer (future task)
4. Balance between conciseness and task clarity

### TDD Cycle (MANDATORY for new features)

**This section is MANDATORY for new features. Delete only if test-after exception applies.**

N/A - This is a refactoring task, not a new feature. Existing tests should continue to pass.

### Exception: Test-After

**Reason for test-after:**
- [x] Other: Refactoring existing code - tests already exist

**Justification:**
This task refactors existing signature docstrings without changing functionality. Integration tests already exist and should continue to pass after refactoring.

### Tests Requeridos

**No new tests required.** Verify existing tests pass:

**Archivo de tests:** `tests/integration/test_dialogue_manager.py`

**Tests a verificar:**
- All integration tests that use NLU (DialogueUnderstanding signature)
- Particularly tests involving:
  - Slot collection
  - Confirmations
  - Corrections
  - Intent changes
  - Digressions

```bash
# Run all integration tests
uv run pytest tests/integration/ -v

# Run with coverage to see if NLU paths still covered
uv run pytest tests/integration/ --cov=src/soni/du --cov-report=term-missing
```

### Criterios de Éxito

- [ ] DialogueUnderstanding docstring reduced to ~15 lines
- [ ] Field descriptions simplified (no instruction-style text)
- [ ] Module-level reference to DATA_STRUCTURES.md added (for developers)
- [ ] NO reference to DATA_STRUCTURES.md in signature docstring (LLM won't see file)
- [ ] All integration tests pass
- [ ] No functionality broken by refactoring
- [ ] Code is more readable and maintainable
- [ ] Follows DSPy signature best practices

### Validación Manual

**Comandos para validar:**

```bash
# Check line count of signature docstring
grep -A 30 'class DialogueUnderstanding' src/soni/du/signatures.py | wc -l

# Verify no CRITICAL/IMPORTANT markers remain
grep -i 'critical\|important' src/soni/du/signatures.py

# Run integration tests
uv run pytest tests/integration/ -v --tb=short

# Check signature still loads correctly
python -c "from soni.du.signatures import DialogueUnderstanding; print(DialogueUnderstanding.__doc__[:100])"
```

**Resultado esperado:**
- Docstring is ~15-20 lines (vs 40+ before)
- No CRITICAL/IMPORTANT markers in file
- All integration tests pass
- Signature loads and shows concise docstring

### Referencias

- `src/soni/du/signatures.py` - File to refactor
- `src/soni/du/DATA_STRUCTURES.md` - Detailed documentation (created in task-334)
- `ref/dspy/dspy/predict/avatar/signatures.py` - DSPy signature examples
- `ref/dspy/tests/signatures/test_signature.py` - DSPy signature patterns
- DSPy documentation: Signatures should be concise, let optimizer discover rules

### Notas Adicionales

- The goal is NOT to remove all instructions, but to move detailed/verbose ones to documentation
- Keep general principles in docstring (conversation_state usage, slot actions)
- If integration tests fail significantly after refactor, some guidance may need to be added back
- Consider this a baseline for optimizer to improve (not manual prompt engineering)
- Future task: Create training examples/datasets for optimizer (not in this task)
