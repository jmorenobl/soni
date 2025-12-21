# Soni Framework - NLU System

## Overview

Soni uses a **DSPy-powered Natural Language Understanding (NLU)** system that produces **Commands** from user input. The LLM's role is limited to interpretation - it produces structured Commands that the DM executes deterministically.

**Key Principle**: NLU produces Commands (pure data), DM executes them.

## Architecture

### Command-Based Output

The NLU system produces a list of Commands, not classifications:

```python
from pydantic import BaseModel, Field
from typing import Any

# Commands are pure data (Pydantic models)
class Command(BaseModel):
    """Base class for all commands."""
    pass

class StartFlow(Command):
    flow_name: str
    slots: dict[str, Any] = {}

class SetSlot(Command):
    slot_name: str
    value: Any
    confidence: float = 1.0

class CorrectSlot(Command):
    slot_name: str
    new_value: Any

class CancelFlow(Command):
    reason: str | None = None

class Clarify(Command):
    topic: str

class AffirmConfirmation(Command):
    pass

class DenyConfirmation(Command):
    slot_to_change: str | None = None

class HumanHandoff(Command):
    reason: str | None = None


class ExtractedEntity(BaseModel):
    """Raw extracted entity (before slot mapping)."""
    entity_type: str
    value: Any
    start: int | None = None
    end: int | None = None


class NLUOutput(BaseModel):
    """NLU output with Commands."""
    commands: list[Command] = Field(
        description="List of commands extracted from user message"
    )
    entities: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Raw extracted entities"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Overall extraction confidence"
    )
    reasoning: str = Field(
        description="Step-by-step reasoning for command extraction"
    )
```

### DSPy Module Structure

```python
import dspy
from datetime import datetime
from cachetools import TTLCache

class SoniDU(dspy.Module):
    """Soni Dialogue Understanding module.

    Produces Commands from user input using DSPy.
    The LLM's ONLY role is to interpret - never to decide what to do.
    """

    def __init__(self, cache_size: int = 1000, cache_ttl: int = 300) -> None:
        super().__init__()

        # Predictor with command extraction signature
        self.predictor = dspy.ChainOfThought(CommandExtraction)

        # Optional caching layer
        self.cache: TTLCache[str, NLUOutput] = TTLCache(
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
        """Sync forward pass for DSPy optimizers."""
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
        """Async forward pass for production runtime."""
        return await self.predictor.acall(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=current_datetime,
        )

    async def understand(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
    ) -> NLUOutput:
        """
        Main entry point for NLU.

        Returns NLUOutput with list of Commands.
        """
        cache_key = self._cache_key(user_message, history, context)

        if cache_key in self.cache:
            return self.cache[cache_key]

        prediction = await self.acall(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=datetime.now().isoformat(),
        )

        result: NLUOutput = prediction.result
        self.cache[cache_key] = result

        return result
```

### Signature Definition

```python
class DialogueContext(BaseModel):
    """Current dialogue context for NLU."""
    current_slots: dict[str, Any] = Field(
        default_factory=dict,
        description="Currently filled slots in active flow"
    )
    available_flows: list[str] = Field(
        default_factory=list,
        description="Available flow names"
    )
    current_flow: str = Field(
        default="none",
        description="Currently active flow name"
    )
    expected_slots: list[str] = Field(
        default_factory=list,
        description="Slots expected from user"
    )
    waiting_for_slot: str | None = Field(
        default=None,
        description="Specific slot we're waiting for"
    )


class CommandExtraction(dspy.Signature):
    """Extract Commands from user message.

    The LLM's role is ONLY to interpret what the user said,
    producing structured Commands. The DM executes these deterministically.

    Multiple commands can be extracted from a single message.
    Examples:
    - "Cancel this and check my balance" → [CancelFlow(), StartFlow("check_balance")]
    - "Actually, change it to Barcelona" → [CorrectSlot("destination", "Barcelona")]
    """

    # Inputs
    user_message: str = dspy.InputField(
        desc="The user's current message"
    )
    history: dspy.History = dspy.InputField(
        desc="Conversation history"
    )
    context: DialogueContext = dspy.InputField(
        desc="Current dialogue context"
    )
    current_datetime: str = dspy.InputField(
        desc="Current datetime for relative date resolution",
        default=""
    )

    # Output
    result: NLUOutput = dspy.OutputField(
        desc="Extracted commands and entities"
    )
```

## Command Extraction Examples

| User Message | Context | Commands Produced |
|--------------|---------|-------------------|
| "New York" | `waiting_for_slot="origin"` | `[SetSlot("origin", "New York")]` |
| "I want to book a flight" | No active flow | `[StartFlow("book_flight")]` |
| "Book a flight from NYC to LA" | No active flow | `[StartFlow("book_flight"), SetSlot("origin", "NYC"), SetSlot("destination", "LA")]` |
| "Actually, Madrid not Barcelona" | Has `destination=Barcelona` | `[CorrectSlot("destination", "Madrid")]` |
| "Cancel" | In flow | `[CancelFlow()]` |
| "Cancel and check my balance" | In flow | `[CancelFlow(), StartFlow("check_balance")]` |
| "What cities do you support?" | Any | `[Clarify("supported_cities")]` |
| "Yes" | `conversation_state=confirming` | `[AffirmConfirmation()]` |
| "No, change the date" | `conversation_state=confirming` | `[DenyConfirmation(slot_to_change="date")]` |
| "Talk to a human" | Any | `[HumanHandoff(reason="user_request")]` |

## DSPy Optimization

### Training Examples

Training data uses Commands with **descriptions** for clarity and dataset quality:

```python
training_examples = [
    # =====================================================
    # EXAMPLE 1: Flow Start with Multiple Slots
    # Description: User starts a flow and provides multiple
    # slot values in the same message. NLU should extract
    # StartFlow command plus SetSlot for each value.
    # =====================================================
    dspy.Example(
        user_message="I want to book a flight from Madrid to Barcelona",
        history=dspy.History(messages=[]),
        context=DialogueContext(
            available_flows=["book_flight", "check_booking"],
            current_flow="none",
            expected_slots=[]
        ),
        result=NLUOutput(
            commands=[
                StartFlow(flow_name="book_flight"),
                SetSlot(slot_name="origin", value="Madrid"),
                SetSlot(slot_name="destination", value="Barcelona")
            ],
            confidence=0.95,
            reasoning="User wants to start booking, provides origin and destination"
        )
    ).with_inputs("user_message", "history", "context"),

    # =====================================================
    # EXAMPLE 2: Slot Correction
    # Description: User corrects a previously provided value.
    # Context shows destination was already filled with
    # "Barcelona", but user now says "Paris". NLU should
    # produce CorrectSlot, not SetSlot.
    # =====================================================
    dspy.Example(
        user_message="Actually, I meant Paris not Barcelona",
        history=dspy.History(messages=[
            {"user_message": "I want to go to Barcelona", "role": "user"}
        ]),
        context=DialogueContext(
            current_flow="book_flight",
            current_slots={"destination": "Barcelona"},
            waiting_for_slot="departure_date"
        ),
        result=NLUOutput(
            commands=[
                CorrectSlot(slot_name="destination", new_value="Paris")
            ],
            confidence=0.92,
            reasoning="User corrects previous destination value"
        )
    ).with_inputs("user_message", "history", "context"),

    # =====================================================
    # EXAMPLE 3: Cancel and Start New Flow
    # Description: User cancels current flow and starts a
    # different one in the same message. NLU should produce
    # two commands: CancelFlow then StartFlow.
    # =====================================================
    dspy.Example(
        user_message="Never mind, what's my balance?",
        history=dspy.History(messages=[]),
        context=DialogueContext(
            current_flow="book_flight",
            current_slots={"origin": "Madrid"},
            available_flows=["book_flight", "check_balance"]
        ),
        result=NLUOutput(
            commands=[
                CancelFlow(reason="user_changed_mind"),
                StartFlow(flow_name="check_balance")
            ],
            confidence=0.88,
            reasoning="User cancels current flow and wants to check balance"
        )
    ).with_inputs("user_message", "history", "context"),

    # =====================================================
    # EXAMPLE 4: Simple Slot Value
    # Description: User provides a direct answer to slot
    # prompt. waiting_for_slot is "origin", user says
    # "New York". NLU should produce simple SetSlot.
    # =====================================================
    dspy.Example(
        user_message="New York",
        history=dspy.History(messages=[
            {"role": "assistant", "content": "Where would you like to fly from?"}
        ]),
        context=DialogueContext(
            current_flow="book_flight",
            waiting_for_slot="origin",
            expected_slots=["origin", "destination", "date"]
        ),
        result=NLUOutput(
            commands=[
                SetSlot(slot_name="origin", value="New York", confidence=0.98)
            ],
            confidence=0.98,
            reasoning="Direct answer to origin slot prompt"
        )
    ).with_inputs("user_message", "history", "context"),

    # =====================================================
    # EXAMPLE 5: Clarification Request
    # Description: User asks a question instead of providing
    # the expected slot value. NLU should produce Clarify
    # command, NOT SetSlot.
    # =====================================================
    dspy.Example(
        user_message="What cities do you fly to?",
        history=dspy.History(messages=[]),
        context=DialogueContext(
            current_flow="book_flight",
            waiting_for_slot="destination",
            expected_slots=["origin", "destination", "date"]
        ),
        result=NLUOutput(
            commands=[
                Clarify(topic="available_destinations")
            ],
            confidence=0.90,
            reasoning="User asks about options instead of providing destination"
        )
    ).with_inputs("user_message", "history", "context"),

    # =====================================================
    # EXAMPLE 6: Confirmation Affirmation
    # Description: System asked for confirmation, user says
    # yes. conversation_state is "confirming".
    # =====================================================
    dspy.Example(
        user_message="Yes, that's correct",
        history=dspy.History(messages=[
            {"role": "assistant", "content": "Book NYC to LA on Dec 20. Confirm?"}
        ]),
        context=DialogueContext(
            current_flow="book_flight",
            current_slots={"origin": "NYC", "destination": "LA", "date": "2024-12-20"},
            # Note: conversation_state would be "confirming" in actual state
        ),
        result=NLUOutput(
            commands=[
                AffirmConfirmation()
            ],
            confidence=0.95,
            reasoning="User confirms the booking details"
        )
    ).with_inputs("user_message", "history", "context"),

    # =====================================================
    # EXAMPLE 7: Confirmation Denial with Slot Specification
    # Description: User denies confirmation and specifies
    # which slot to change.
    # =====================================================
    dspy.Example(
        user_message="No, change the date to next Friday",
        history=dspy.History(messages=[
            {"role": "assistant", "content": "Book NYC to LA on Dec 20. Confirm?"}
        ]),
        context=DialogueContext(
            current_flow="book_flight",
            current_slots={"origin": "NYC", "destination": "LA", "date": "2024-12-20"}
        ),
        result=NLUOutput(
            commands=[
                DenyConfirmation(slot_to_change="date")
            ],
            confidence=0.92,
            reasoning="User denies and wants to change the date"
        )
    ).with_inputs("user_message", "history", "context"),
]
```

### Metrics

```python
def command_type_accuracy(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """Measure accuracy of command types extracted."""
    expected_types = {type(cmd).__name__ for cmd in example.result.commands}
    predicted_types = {type(cmd).__name__ for cmd in prediction.result.commands}

    if not expected_types and not predicted_types:
        return 1.0
    if not expected_types or not predicted_types:
        return 0.0

    intersection = expected_types & predicted_types
    union = expected_types | predicted_types

    return len(intersection) / len(union)


def command_args_accuracy(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """Measure accuracy of command arguments."""
    expected = example.result.commands
    predicted = prediction.result.commands

    if not expected and not predicted:
        return 1.0
    if not expected or not predicted:
        return 0.0

    matches = 0
    for exp_cmd in expected:
        for pred_cmd in predicted:
            if type(exp_cmd) == type(pred_cmd):
                if exp_cmd.model_dump() == pred_cmd.model_dump():
                    matches += 1
                    break

    return matches / max(len(expected), len(predicted))


def combined_metric(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """Combined metric for optimization."""
    type_acc = command_type_accuracy(example, prediction)
    args_acc = command_args_accuracy(example, prediction)

    return 0.4 * type_acc + 0.6 * args_acc
```

### Optimization Workflow

```python
import dspy

# Configure LLM
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.settings.configure(lm=lm)

# Create module
module = SoniDU()

# Create optimizer
optimizer = dspy.MIPROv2(
    metric=combined_metric,
    auto="light",
    num_candidates=5
)

# Optimize
optimized_module = optimizer.compile(
    module,
    trainset=training_examples,
    valset=validation_examples
)

# Save optimized module
optimized_module.save("optimized_soni_du.json")
```

## Integration with CommandExecutor

```python
async def understand_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict[str, Any]:
    """
    Understand node - produces Commands from user message.
    """
    context = runtime.context
    user_message = state["user_message"]

    # Build NLU context
    active_ctx = context.flow_manager.get_active_context(state)

    dialogue_context = DialogueContext(
        current_slots=state["flow_slots"].get(
            active_ctx["flow_id"], {}
        ) if active_ctx else {},
        available_flows=context.scope_manager.get_available_flows(state),
        current_flow=active_ctx["flow_name"] if active_ctx else "none",
        expected_slots=get_expected_slots(state, context.config),
        waiting_for_slot=state.get("waiting_for_slot")
    )

    history = dspy.History(messages=[
        {"user_message": msg["content"], "role": msg["role"]}
        for msg in state["messages"][-10:]
    ])

    # NLU produces Commands
    nlu_result: NLUOutput = await context.nlu_provider.understand(
        user_message=user_message,
        history=history,
        context=dialogue_context
    )

    return {
        "nlu_result": nlu_result.model_dump(),
        "last_nlu_call": time.time()
    }


async def execute_commands_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict[str, Any]:
    """
    Execute Commands via CommandExecutor.

    Deterministic - no LLM involved.
    """
    context = runtime.context

    nlu_result = NLUOutput.model_validate(state["nlu_result"])
    commands = nlu_result.commands

    # Execute via CommandExecutor (deterministic)
    updates = await context.command_executor.execute(
        commands=commands,
        state=state,
        context=context
    )

    return updates
```

## Error Handling

```python
async def understand(
    self,
    user_message: str,
    history: dspy.History,
    context: DialogueContext,
) -> NLUOutput:
    """Main entry point with error handling."""

    try:
        prediction = await self.acall(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=datetime.now().isoformat(),
        )

        return prediction.result

    except Exception as e:
        logger.error(f"NLU error: {e}", exc_info=True)

        # Fallback: If waiting for slot, assume slot value
        if context.waiting_for_slot:
            return NLUOutput(
                commands=[
                    SetSlot(
                        slot_name=context.waiting_for_slot,
                        value=user_message,
                        confidence=0.3
                    )
                ],
                confidence=0.3,
                reasoning=f"Fallback: assumed slot value due to error"
            )

        # Otherwise, empty commands (DM will handle)
        return NLUOutput(
            commands=[],
            confidence=0.0,
            reasoning=f"Error: {type(e).__name__}"
        )
```

## Summary

Soni v2.0 NLU system:

1. ✅ **Produces Commands**: Not classifications, but structured Commands
2. ✅ **Multiple Commands**: Handle compound user messages
3. ✅ **Type-Safe**: Pydantic models throughout
4. ✅ **DSPy-Optimized**: Automatic prompt optimization
5. ✅ **Async-First**: Native async throughout
6. ✅ **Cached**: TTL cache for efficiency
7. ✅ **Error Handling**: Graceful fallback on errors

## Next Steps

- **[11-commands.md](11-commands.md)** - Complete Command specification
- **[03-components.md](03-components.md)** - Component reference
- **[05-message-flow.md](05-message-flow.md)** - Message flow

---

**Design Version**: v2.0 (Command-Driven Architecture)
**Status**: Production-ready design specification
