## Task: 008 - Dialogue Understanding (DSPy)

**ID de tarea:** 008
**Hito:** 5 - Dialogue Understanding
**Dependencias:** 002, 007
**Duración estimada:** 8 horas

### Objetivo

Implement the NLU module using DSPy to extract Commands from user messages.
Use `.acall()` for native async (NOT asyncify), Pydantic types for structured I/O,
and rich InputField descriptions to guide the LLM.

### Entregables

- [ ] `du/models.py` - Pydantic models for DialogueContext, NLUOutput, Command types
- [ ] `du/signatures.py` - DSPy signatures with rich descriptions and Pydantic types
- [ ] `du/modules.py` - SoniDU module using `.acall()` for async
- [ ] `du/optimizer.py` - MIPROv2 wrapper
- [ ] Command extraction tests with Mock LM

### Implementación Detallada

**Archivo:** `src/soni/du/models.py`

```python
"""Pydantic models for DSPy signature types.

These models define the structured input/output for the NLU signature.
DSPy uses Pydantic for output validation and type coercion.
"""
from pydantic import BaseModel, Field
from typing import Literal


class FlowInfo(BaseModel):
    """Information about an available flow."""
    
    name: str = Field(description="Flow identifier")
    description: str = Field(description="What this flow does")
    trigger_intents: list[str] = Field(
        default_factory=list,
        description="Example phrases that trigger this flow"
    )


class SlotValue(BaseModel):
    """A slot with its current value."""
    
    name: str = Field(description="Slot name")
    value: str | None = Field(description="Current value or None if not set")
    expected_type: str = Field(default="string", description="Expected type: string, date, number")


class CommandInfo(BaseModel):
    """Information about an available command.
    
    Passed dynamically to the LLM so it knows what commands it can generate.
    """
    
    command_type: str = Field(description="Command identifier (e.g., 'start_flow')")
    description: str = Field(description="What this command does")
    required_fields: list[str] = Field(
        default_factory=list,
        description="Fields required when using this command"
    )
    example: str = Field(
        default="",
        description="Example user message that would trigger this command"
    )


class DialogueContext(BaseModel):
    """Complete dialogue context for NLU.
    
    Provides all information the LLM needs to understand user intent.
    """
    
    available_flows: list[FlowInfo] = Field(
        description="Flows the user can start. Each has name, description, and trigger examples"
    )
    available_commands: list[CommandInfo] = Field(
        description="Commands the LLM can generate. Each has type, description, required_fields"
    )
    active_flow: str | None = Field(
        default=None,
        description="Currently active flow name, or None if idle"
    )
    current_slots: list[SlotValue] = Field(
        default_factory=list,
        description="Slots already filled in the current flow"
    )
    expected_slot: str | None = Field(
        default=None,
        description="Slot the system is currently asking for"
    )
    conversation_state: Literal["idle", "collecting", "confirming", "action_pending"] = Field(
        default="idle",
        description="Current conversation phase"
    )


class Command(BaseModel):
    """A command to execute.
    
    The LLM outputs a list of these to drive the dialogue.
    """
    
    command_type: str = Field(
        description="Type of command (must match one from available_commands)"
    )
    
    # Optional fields depending on command type
    flow_name: str | None = Field(default=None, description="For start_flow: which flow to start")
    slot_name: str | None = Field(default=None, description="For set_slot/correct_slot: target slot")
    slot_value: str | None = Field(default=None, description="For set_slot/correct_slot: the value")
    reason: str | None = Field(default=None, description="For cancel_flow/human_handoff: why")


class NLUOutput(BaseModel):
    """Structured output from NLU.
    
    Note: reasoning is NOT included here because ChainOfThought
    adds it automatically as a separate field.
    """
    
    commands: list[Command] = Field(
        description="List of commands to execute in order"
    )
```

**Archivo:** `src/soni/du/signatures.py`

```python
"""DSPy signatures for Dialogue Understanding.

Uses Pydantic types for structured I/O and rich descriptions to guide the LLM.
Based on the proven pattern from the current codebase.
"""
import dspy

from soni.du.models import DialogueContext, NLUOutput


class ExtractCommands(dspy.Signature):
    """Analyze user messages in dialogue context and generate executable commands.

    You are the "Understanding Layer" of a deterministic dialogue system.
    Your job is to translate the User's Message into a list of Commands.

    The available commands are provided in `context.available_commands`.
    Each command has:
    - command_type: The identifier to use
    - description: What it does
    - required_fields: Fields you must populate
    - example: Example user message

    RULES:
    1. ONLY use commands from context.available_commands
    2. If user provides a value and 'expected_slot' is set, generate set_slot
    3. If user corrects a value, check 'current_slots' and generate correct_slot
    4. If user asks to start a task, match against 'available_flows'
    5. If 'conversation_state' is 'confirming':
       - "Yes/Correct" -> affirm
       - "No/Wrong" -> deny (include slot_name if they specify what to change)
    6. Be explicit. Generate exactly the commands needed.
    """

    # Input fields with rich descriptions and Pydantic types
    user_message: str = dspy.InputField(
        desc="User's input message to analyze"
    )
    context: DialogueContext = dspy.InputField(
        desc="Complete dialogue context including available_flows, available_commands, current_slots, expected_slot"
    )
    history: dspy.History = dspy.InputField(
        desc="Recent conversation history (list of {role, content} messages)"
    )

    # Output field with Pydantic type for structured validation
    result: NLUOutput = dspy.OutputField(
        desc="Extracted commands and reasoning"
    )
```

**Archivo:** `src/soni/du/modules.py`

```python
"""DSPy modules for dialogue understanding.

Async-first design using native .acall() method (NOT asyncify wrapper).
"""
import dspy

from soni.du.signatures import ExtractCommands
from soni.du.models import DialogueContext, NLUOutput, Command


class SoniDU(dspy.Module):
    """Dialogue Understanding module using DSPy.
    
    Features:
    - Native async with .acall() (more efficient than asyncify)
    - ChainOfThought for reasoning
    - Pydantic types for structured I/O
    - MIPROv2 optimization support
    - Save/load for persistence
    """
    
    def __init__(self):
        super().__init__()
        self.extractor = dspy.ChainOfThought(ExtractCommands)
    
    async def aforward(
        self,
        user_message: str,
        context: DialogueContext,
        history: list[dict[str, str]] | None = None,
    ) -> NLUOutput:
        """Extract commands from user message (async).
        
        Uses native .acall() for async LM calls - more efficient
        than wrapping with asyncify.
        """
        result = await self.extractor.acall(
            user_message=user_message,
            context=context,
            history=history or [],
        )
        
        return result.result  # NLUOutput Pydantic model
    
    def forward(
        self,
        user_message: str,
        context: DialogueContext,
        history: list[dict[str, str]] | None = None,
    ) -> NLUOutput:
        """Sync version (for testing/optimization)."""
        result = self.extractor(
            user_message=user_message,
            context=context,
            history=history or [],
        )
        return result.result
```

**Archivo:** `src/soni/du/optimizer.py`

```python
"""MIPROv2 optimizer for SoniDU.

Uses DSPy's latest MIPROv2 for prompt optimization.
"""
from dspy.teleprompt import MIPROv2
from dspy import Example

from soni.du.modules import SoniDU
from soni.du.models import DialogueContext, NLUOutput


def create_metric(validate_command_fn: callable):
    """Create a metric function for optimization.
    
    Args:
        validate_command_fn: Function to validate if command matches expected
    """
    def metric(example: Example, prediction: NLUOutput, trace=None) -> bool:
        expected = example.expected_commands
        actual = prediction.commands
        
        if len(expected) != len(actual):
            return False
        
        for exp, act in zip(expected, actual):
            if not validate_command_fn(exp, act):
                return False
        
        return True
    
    return metric


def optimize_du(
    trainset: list[Example],
    metric: callable,
    auto: str = "light",  # "light", "medium", "heavy"
) -> SoniDU:
    """Optimize SoniDU with MIPROv2.
    
    Args:
        trainset: Training examples (dspy.Example objects)
        metric: Evaluation metric function
        auto: Optimization intensity
    
    Returns:
        Optimized SoniDU module
    """
    teleprompter = MIPROv2(
        metric=metric,
        auto=auto,
    )
    
    program = SoniDU()
    optimized = teleprompter.compile(
        program.deepcopy(),
        trainset=trainset,
        max_bootstrapped_demos=3,
        max_labeled_demos=4,
    )
    
    return optimized
```

### TDD Cycle

```python
# tests/unit/du/test_modules.py
import pytest
import dspy
from soni.du.modules import SoniDU
from soni.du.models import DialogueContext, FlowInfo


class TestSoniDU:
    @pytest.mark.asyncio
    async def test_extract_start_flow_command(self):
        """
        GIVEN a message "I want to book a flight"
        WHEN processed by SoniDU
        THEN returns start_flow command
        """
        # Arrange
        context = DialogueContext(
            available_flows=[
                FlowInfo(
                    name="book_flight",
                    description="Book a flight ticket",
                    trigger_intents=["book flight", "reserve ticket"]
                ),
            ],
            conversation_state="idle",
        )
        du = SoniDU()
        
        # Act
        result = await du.aforward(
            user_message="I want to book a flight",
            context=context,
        )
        
        # Assert
        assert len(result.commands) == 1
        assert result.commands[0].command_type == "start_flow"
        assert result.commands[0].flow_name == "book_flight"

    @pytest.mark.asyncio
    async def test_extract_set_slot_when_expected(self):
        """
        GIVEN a context expecting "origin" slot
        WHEN user says "Madrid"
        THEN returns set_slot command
        """
        # Arrange
        context = DialogueContext(
            available_flows=[],
            active_flow="book_flight",
            expected_slot="origin",
            conversation_state="collecting",
        )
        du = SoniDU()
        
        # Act
        result = await du.aforward(
            user_message="Madrid",
            context=context,
        )
        
        # Assert
        assert result.commands[0].command_type == "set_slot"
        assert result.commands[0].slot_name == "origin"
        assert result.commands[0].slot_value == "Madrid"

    @pytest.mark.asyncio
    async def test_affirm_during_confirmation(self):
        """
        GIVEN confirmation state
        WHEN user says "yes, that's correct"
        THEN returns affirm command
        """
        # Arrange
        context = DialogueContext(
            available_flows=[],
            active_flow="book_flight",
            conversation_state="confirming",
        )
        du = SoniDU()
        
        # Act
        result = await du.aforward(
            user_message="Yes, that's correct",
            context=context,
        )
        
        # Assert
        assert result.commands[0].command_type == "affirm"
```

### Criterios de Éxito

- [ ] Uses native `.acall()` for async (not asyncify)
- [ ] Pydantic types for DialogueContext and NLUOutput
- [ ] Rich InputField descriptions guide LLM
- [ ] FlowInfo includes description and trigger_intents
- [ ] Commands extracted correctly with structured types
- [ ] MIPROv2 optimizer with trainset/metric pattern
- [ ] All tests pass with Mock LM
