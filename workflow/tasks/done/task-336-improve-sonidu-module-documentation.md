## Task: 336 - Improve SoniDU Module Documentation

**ID de tarea:** 336
**Hito:** NLU Improvements
**Dependencias:** task-334 (DATA_STRUCTURES.md reference)
**Duración estimada:** 2 horas

### Objetivo

Enhance the SoniDU module docstring to clearly explain what the module does, document the data flow (input → output), and clarify the different interfaces (forward, aforward, predict, understand).

### Contexto

The current SoniDU module documentation (src/soni/du/modules.py:18-33) describes features but doesn't explain:
- WHAT the module does (its purpose/responsibility)
- The data flow (what goes in, what comes out)
- WHEN to use each method (forward vs aforward vs predict vs understand)
- The relationship between these methods

Good module documentation should answer:
1. What is this module's purpose?
2. What input does it take?
3. What output does it produce?
4. How do I use it (which method to call)?
5. How does it fit in the larger system?

This improves:
- Developer onboarding
- Code maintainability
- Optimizer understanding (if used in compilation)
- Debugging efficiency

### Entregables

- [ ] Enhanced SoniDU class docstring
- [ ] Clear explanation of module purpose
- [ ] Documented data flow (input → processing → output)
- [ ] Clarified method relationships (forward/aforward/predict/understand)
- [ ] Usage examples added
- [ ] References to DATA_STRUCTURES.md

### Implementación Detallada

#### Paso 1: Rewrite Main Class Docstring

**Archivo a modificar:** `src/soni/du/modules.py`

**Current docstring (lines 18-33):**
```python
class SoniDU(dspy.Module):
    """
    Soni Dialogue Understanding module with structured types.

    This module provides:
    - Type-safe async interface for runtime
    - Sync interface for DSPy optimizers
    - Automatic prompt optimization via DSPy
    - Structured Pydantic models throughout
    - Configurable predictor: Predict (fast) or ChainOfThought (precise)

    Performance Notes:
    - Predict (use_cot=False): Faster, fewer tokens, sufficient for most cases
    - ChainOfThought (use_cot=True): Slower, more tokens, shows reasoning,
      useful when precision is critical or debugging NLU behavior
    """
```

**New enhanced docstring:**
```python
class SoniDU(dspy.Module):
    """
    Natural Language Understanding module for dialogue systems.

    This module analyzes user messages in dialogue context to:
    - Classify message type (slot value, confirmation, correction, interruption, etc.)
    - Extract slot values with metadata (confidence, action type, previous value)
    - Detect intent changes and digressions
    - Resolve temporal expressions using current datetime

    Data Flow
    ---------
    Input:
        - user_message (str): Raw user input
        - history (dspy.History): Conversation history
        - context (DialogueContext): Current state (flow, slots, conversation phase)
        - current_datetime (str): ISO timestamp for temporal resolution

    Output:
        - NLUOutput: Structured analysis with message_type, command, slots, confidence

    For detailed data structure specifications, see DATA_STRUCTURES.md.

    Usage
    -----
    The module provides multiple interfaces for different use cases:

    1. **predict()** - Main async interface for production runtime
       - High-level API with caching and post-processing
       - Accepts structured types (dspy.History, DialogueContext)
       - Returns NLUOutput Pydantic model
       - Use this in production code

    2. **understand()** - Dict-based async interface for compatibility
       - Implements INLUProvider protocol
       - Accepts dict-based dialogue_context
       - Returns dict representation of NLUOutput
       - Use this when integrating with dict-based systems

    3. **forward()** - Sync interface for DSPy optimizers
       - Used during optimization/training
       - Called by MIPROv2, BootstrapFewShot, etc.
       - Do not call directly in production

    4. **aforward()** - Async version of forward()
       - Used internally by predict()
       - Do not call directly

    Optimization
    ------------
    - use_cot=False (default): Use Predict for speed and efficiency
      - Faster inference
      - Fewer tokens
      - Sufficient for most dialogue scenarios

    - use_cot=True: Use ChainOfThought for debugging and precision
      - Slower inference
      - More tokens (shows reasoning)
      - Useful for debugging NLU behavior
      - Useful when precision is critical

    Compatible with DSPy optimizers:
    - MIPROv2 (recommended for dialogue NLU)
    - BootstrapFewShot
    - COPRO
    - Others (see DSPy docs)

    Examples
    --------
    Basic usage with structured types:

    >>> import dspy
    >>> from soni.du.modules import SoniDU
    >>> from soni.du.models import DialogueContext
    >>>
    >>> # Initialize module
    >>> nlu = SoniDU(use_cot=False)
    >>>
    >>> # Prepare inputs
    >>> user_message = "I want to fly to Madrid"
    >>> history = dspy.History(messages=[])
    >>> context = DialogueContext(
    ...     current_flow="book_flight",
    ...     expected_slots=["destination", "departure_date"],
    ...     current_slots={},
    ...     conversation_state="waiting_for_slot"
    ... )
    >>>
    >>> # Call predict
    >>> result = await nlu.predict(user_message, history, context)
    >>> print(result.message_type)  # MessageType.SLOT_VALUE
    >>> print(result.slots[0].name)  # "destination"
    >>> print(result.slots[0].value)  # "Madrid"

    Dict-based interface (for compatibility):

    >>> result_dict = await nlu.understand(
    ...     user_message="Madrid",
    ...     dialogue_context={
    ...         "current_flow": "book_flight",
    ...         "expected_slots": ["destination"],
    ...         "current_slots": {},
    ...         "conversation_state": "waiting_for_slot"
    ...     }
    ... )
    >>> print(result_dict["message_type"])  # "slot_value"
    """
```

**Explicación:**
- Clear purpose statement at the start
- Explicit data flow section (input → output)
- Usage section explaining when to use each method
- Optimization section with clear recommendations
- Concrete examples showing actual usage
- References DATA_STRUCTURES.md for details
- Follows NumPy docstring style (sections: Data Flow, Usage, Examples)

#### Paso 2: Enhance __init__ Docstring

**Current __init__ docstring (lines 35-43):**
```python
def __init__(self, cache_size: int = 1000, cache_ttl: int = 300, use_cot: bool = False) -> None:
    """Initialize SoniDU module.

    Args:
        cache_size: Maximum number of cached NLU results
        cache_ttl: Time-to-live for cache entries in seconds
        use_cot: If True, use ChainOfThought (slower, more precise).
                 If False, use Predict (faster, less tokens). Default: False
    """
```

**Enhanced __init__ docstring:**
```python
def __init__(self, cache_size: int = 1000, cache_ttl: int = 300, use_cot: bool = False) -> None:
    """Initialize Natural Language Understanding module.

    Args:
        cache_size: Maximum number of cached NLU results (default: 1000)
        cache_ttl: Cache entry lifetime in seconds (default: 300 = 5 minutes)
        use_cot: Predictor mode selection (default: False)
            - False: Use Predict (faster, recommended for production)
            - True: Use ChainOfThought (slower, better for debugging)

    Note:
        The module requires dspy.configure(lm=...) to be called before use.
        See DSPy documentation for LM configuration.
    """
```

**Explicación:**
- More descriptive first line
- Added default values in docstring
- Clarified use_cot parameter
- Added note about dspy.configure requirement

#### Paso 3: Enhance Key Method Docstrings

**forward() method (lines 64-89):**

```python
def forward(
    self,
    user_message: str,
    history: dspy.History,
    context: DialogueContext,
    current_datetime: str = "",
) -> dspy.Prediction:
    """Synchronous forward pass for DSPy optimizers.

    This method is called by DSPy optimizers during training/optimization.
    Do NOT call this method directly in production code - use predict() instead.

    Args:
        user_message: User's input message to analyze
        history: Conversation history (dspy.History)
        context: Current dialogue state (DialogueContext)
        current_datetime: Current datetime in ISO format (auto-generated if empty)

    Returns:
        dspy.Prediction with result field containing NLUOutput

    Note:
        Used by MIPROv2, BootstrapFewShot, and other DSPy optimizers.
        For production use, call predict() or understand() instead.
    """
```

**aforward() method (lines 91-114):**

```python
async def aforward(
    self,
    user_message: str,
    history: dspy.History,
    context: DialogueContext,
    current_datetime: str = "",
) -> dspy.Prediction:
    """Asynchronous forward pass for production runtime.

    This method is called internally by predict(). Do NOT call directly.

    Args:
        Same as forward()

    Returns:
        dspy.Prediction with result field containing NLUOutput

    Note:
        Uses async LM calls via DSPy's adapter system.
        Called internally by predict() - use that method instead.
    """
```

**predict() method (lines 180-234):**

```python
async def predict(
    self,
    user_message: str,
    history: dspy.History,
    context: DialogueContext,
) -> NLUOutput:
    """Analyze user message with NLU (main production interface).

    This is the primary method for NLU analysis in production. It provides:
    - Structured type inputs/outputs
    - Automatic caching (avoid re-analyzing same inputs)
    - Post-processing (validate slots, normalize confirmation values)
    - Internal datetime management

    Args:
        user_message: User's input message to analyze
        history: Conversation history (dspy.History)
        context: Current dialogue state (DialogueContext)

    Returns:
        NLUOutput: Structured analysis with message_type, command, slots, confidence

    Example:
        >>> result = await nlu.predict(
        ...     user_message="Madrid",
        ...     history=history,
        ...     context=context
        ... )
        >>> print(result.message_type)  # MessageType.SLOT_VALUE
        >>> print(result.slots[0].name)  # "destination"
    """
```

**understand() method (lines 153-178):**

```python
async def understand(
    self,
    user_message: str,
    dialogue_context: dict[str, Any],
) -> dict[str, Any]:
    """Analyze user message with NLU (dict-based interface for compatibility).

    This method implements the INLUProvider protocol for compatibility with
    dict-based systems. Internally converts dicts to structured types and
    delegates to predict().

    Use this method when integrating with systems that use dict-based state
    (e.g., legacy code, external integrations). For new code, prefer predict().

    Args:
        user_message: User's input message to analyze
        dialogue_context: Dict with keys:
            - current_slots (dict): Already filled slots
            - expected_slots (list[str]): Expected slot names
            - current_flow (str): Active flow name
            - conversation_state (str): Current conversation phase
            - available_flows (dict): Available flows {name: description}
            - available_actions (list[str]): Available action names
            - history (list): Conversation messages

    Returns:
        Dict representation of NLUOutput with keys:
            - message_type (str): Type of message
            - command (str | None): Intent/flow name
            - slots (list[dict]): Extracted slot values
            - confidence (float): Overall confidence
            - confirmation_value (bool | None): For confirmations

    Example:
        >>> result = await nlu.understand(
        ...     user_message="Madrid",
        ...     dialogue_context={
        ...         "current_flow": "book_flight",
        ...         "expected_slots": ["destination"],
        ...         "current_slots": {},
        ...         "conversation_state": "waiting_for_slot"
        ...     }
        ... )
        >>> print(result["message_type"])  # "slot_value"
    """
```

### Exception: Test-After

**Reason for test-after:**
- [x] Other: Documentation improvements - no code changes

**Justification:**
This task only improves docstrings and documentation. No executable code changes, so no new tests required.

### Tests Requeridos

N/A - Documentation task only

### Criterios de Éxito

- [ ] Main class docstring includes purpose, data flow, usage, examples
- [ ] All public methods have enhanced docstrings
- [ ] Clear guidance on which method to use when
- [ ] Examples added to main docstring and key methods
- [ ] References to DATA_STRUCTURES.md added
- [ ] Documentation follows NumPy/Google style conventions
- [ ] All docstrings in English

### Validación Manual

**Comandos para validar:**

```bash
# View enhanced docstring
python -c "from soni.du.modules import SoniDU; help(SoniDU)"

# Check docstring sections exist
grep -A 5 "Data Flow\|Usage\|Examples\|Optimization" src/soni/du/modules.py

# Verify no Spanish text remains
grep -i "español\|español" src/soni/du/modules.py

# Check docstring is well-formed
python -m pydoc soni.du.modules.SoniDU
```

**Resultado esperado:**
- help(SoniDU) shows comprehensive documentation
- All sections present (Data Flow, Usage, Examples, Optimization)
- No Spanish text found
- pydoc renders cleanly

### Referencias

- `src/soni/du/modules.py` - File to enhance
- `src/soni/du/DATA_STRUCTURES.md` - Reference for data structures (task-334)
- NumPy docstring style guide: https://numpydoc.readthedocs.io/en/latest/format.html
- PEP 257 - Docstring Conventions: https://peps.python.org/pep-0257/

### Notas Adicionales

- Use NumPy-style sections (Data Flow, Usage, Examples) for clarity
- Include concrete examples in docstrings (not just abstract descriptions)
- Make it clear which methods are for production vs optimization
- Reference DATA_STRUCTURES.md rather than repeating structure details
- Keep examples simple but realistic (use flight_booking scenario)
