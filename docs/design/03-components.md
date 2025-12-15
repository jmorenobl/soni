# Soni Framework - Components

## Overview

Soni's architecture is built around focused, single-responsibility components that work together to enable sophisticated conversational AI. The key innovation is the **Command layer** that separates language understanding from dialogue management execution.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     RuntimeLoop                              │
│                   (Orchestrator)                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐   ┌────────────┐   ┌────────────┐
    │  SoniDU  │   │  Command   │   │   Flow     │
    │  (NLU)   │──▶│  Executor  │──▶│  Manager   │
    └──────────┘   └────────────┘   └────────────┘
          │               │               │
          │               ▼               │
          │        ┌────────────┐         │
          │        │  Handler   │         │
          │        │  Registry  │         │
          │        └────────────┘         │
          │               │               │
          ▼               ▼               ▼
    ┌─────────────────────────────────────────┐
    │            DialogueState                 │
    │         (LangGraph managed)              │
    └─────────────────────────────────────────┘
```

---

## Commands (New in v2.0)

### Responsibility

Pure data objects representing user intent. Commands are the explicit contract between DU and DM.

### Design Philosophy

Commands are **pure Pydantic models** (data only, no behavior):
- Serializable for logging/replay
- Immutable once created
- Easy to test and validate

### Command Types

```python
from pydantic import BaseModel
from typing import Any

class Command(BaseModel):
    """Base class for all commands."""
    pass

# Flow control
class StartFlow(Command):
    """Start a new flow."""
    flow_name: str
    slots: dict[str, Any] = {}

class CancelFlow(Command):
    """Cancel current flow."""
    reason: str | None = None

# Slot management
class SetSlot(Command):
    """Set a slot value."""
    slot_name: str
    value: Any
    confidence: float = 1.0

class CorrectSlot(Command):
    """Correct a previously set slot."""
    slot_name: str
    new_value: Any

# Conversation patterns
class Clarify(Command):
    """User asks for clarification."""
    topic: str

class HumanHandoff(Command):
    """Request human agent."""
    reason: str | None = None

# Confirmation
class AffirmConfirmation(Command):
    """User confirms."""
    pass

class DenyConfirmation(Command):
    """User denies confirmation."""
    slot_to_change: str | None = None
```

---

## Command Handlers

### Responsibility

Execute individual commands. Each handler implements one command type, following SRP.

### Protocol

```python
from typing import Protocol

class CommandHandler(Protocol):
    """Protocol for command handlers."""

    async def execute(
        self,
        command: Command,
        state: DialogueState,
        context: RuntimeContext
    ) -> dict[str, Any]:
        """
        Execute a command and return state updates.

        Args:
            command: The command to execute
            state: Current dialogue state
            context: Runtime context with dependencies

        Returns:
            Partial state updates (dict)
        """
        ...
```

### Example Handlers

```python
class StartFlowHandler:
    """Handler for StartFlow command."""

    async def execute(
        self,
        command: StartFlow,
        state: DialogueState,
        context: RuntimeContext
    ) -> dict[str, Any]:
        # Push new flow to stack
        flow_id = context.flow_manager.push_flow(
            state,
            command.flow_name,
            command.slots
        )

        # Advance through any pre-filled slots
        updates = context.step_manager.advance_through_completed_steps(
            state, context
        )

        return {
            "active_flow_id": flow_id,
            **updates
        }


class SetSlotHandler:
    """Handler for SetSlot command."""

    async def execute(
        self,
        command: SetSlot,
        state: DialogueState,
        context: RuntimeContext
    ) -> dict[str, Any]:
        # Validate slot value
        is_valid = await context.validator.validate(
            command.slot_name,
            command.value,
            state
        )

        if not is_valid:
            return {
                "conversation_state": "waiting_for_slot",
                "last_response": f"Invalid value for {command.slot_name}."
            }

        # Normalize and store
        normalized = await context.normalizer.normalize(
            command.slot_name,
            command.value
        )
        context.flow_manager.set_slot(state, command.slot_name, normalized)

        # Advance through completed steps
        return context.step_manager.advance_through_completed_steps(
            state, context
        )


class CorrectSlotHandler:
    """Handler for CorrectSlot command."""

    async def execute(
        self,
        command: CorrectSlot,
        state: DialogueState,
        context: RuntimeContext
    ) -> dict[str, Any]:
        # Validate new value
        is_valid = await context.validator.validate(
            command.slot_name,
            command.new_value,
            state
        )

        if not is_valid:
            return {
                "conversation_state": "waiting_for_slot",
                "waiting_for_slot": command.slot_name,
                "last_response": f"Invalid value. Please provide a valid {command.slot_name}."
            }

        # Update slot
        normalized = await context.normalizer.normalize(
            command.slot_name,
            command.new_value
        )
        context.flow_manager.set_slot(state, command.slot_name, normalized)

        return {
            "last_response": f"Updated {command.slot_name} to {normalized}."
        }


class CancelFlowHandler:
    """Handler for CancelFlow command."""

    async def execute(
        self,
        command: CancelFlow,
        state: DialogueState,
        context: RuntimeContext
    ) -> dict[str, Any]:
        context.flow_manager.pop_flow(state, result="cancelled")

        if state["flow_stack"]:
            # Resume previous flow
            return {
                "conversation_state": "understanding",
                "last_response": "Cancelled. Returning to previous task."
            }
        else:
            return {
                "conversation_state": "idle",
                "last_response": "Cancelled. How else can I help?"
            }


class ClarifyHandler:
    """Handler for Clarify command (Conversation Pattern)."""

    async def execute(
        self,
        command: Clarify,
        state: DialogueState,
        context: RuntimeContext
    ) -> dict[str, Any]:
        # Generate clarification response
        explanation = await context.help_generator.explain(
            command.topic,
            state
        )

        # Re-prompt current slot
        reprompt = ""
        if state.get("waiting_for_slot"):
            slot_config = context.get_slot_config(state["waiting_for_slot"])
            reprompt = f"\n\n{slot_config.prompt}"

        return {
            "digression_depth": state.get("digression_depth", 0) + 1,
            "last_response": f"{explanation}{reprompt}"
        }
```

---

## Handler Registry

### Responsibility

Maps command types to their handlers. Enables Open/Closed Principle - add new commands without modifying existing code.

### Implementation

```python
class CommandHandlerRegistry:
    """Registry mapping command types to handlers."""

    def __init__(self):
        self._handlers: dict[type[Command], CommandHandler] = {}

    def register(
        self,
        command_type: type[Command],
        handler: CommandHandler
    ) -> None:
        """Register a handler for a command type."""
        self._handlers[command_type] = handler

    def get(self, command_type: type[Command]) -> CommandHandler:
        """Get handler for command type."""
        if command_type not in self._handlers:
            raise KeyError(f"No handler registered for {command_type.__name__}")
        return self._handlers[command_type]

    @classmethod
    def create_default(cls) -> "CommandHandlerRegistry":
        """Create registry with all default handlers."""
        registry = cls()

        # Register all handlers
        registry.register(StartFlow, StartFlowHandler())
        registry.register(SetSlot, SetSlotHandler())
        registry.register(CorrectSlot, CorrectSlotHandler())
        registry.register(CancelFlow, CancelFlowHandler())
        registry.register(Clarify, ClarifyHandler())
        registry.register(HumanHandoff, HumanHandoffHandler())
        registry.register(AffirmConfirmation, AffirmConfirmationHandler())
        registry.register(DenyConfirmation, DenyConfirmationHandler())

        return registry
```

---

## Command Executor

### Responsibility

Coordinates command execution with cross-cutting concerns (logging, validation, error handling).

### Implementation

```python
class CommandExecutor:
    """Executes commands via registered handlers."""

    def __init__(self, registry: CommandHandlerRegistry):
        self.registry = registry
        self.logger = logging.getLogger(__name__)

    async def execute(
        self,
        commands: list[Command],
        state: DialogueState,
        context: RuntimeContext
    ) -> dict[str, Any]:
        """
        Execute all commands and merge state updates.

        Args:
            commands: List of commands to execute
            state: Current dialogue state
            context: Runtime context with dependencies

        Returns:
            Merged state updates from all commands
        """
        all_updates: dict[str, Any] = {}

        for command in commands:
            # Log command for audit
            self.logger.info(
                f"Executing command: {type(command).__name__}",
                extra={"command": command.model_dump()}
            )

            try:
                # Get handler and execute
                handler = self.registry.get(type(command))
                updates = await handler.execute(command, state, context)

                # Merge updates
                all_updates = self._merge_updates(all_updates, updates)

                # Apply to state for subsequent commands
                for key, value in updates.items():
                    state[key] = value

            except Exception as e:
                self.logger.error(
                    f"Error executing {type(command).__name__}: {e}",
                    exc_info=True
                )
                return {
                    "conversation_state": "error",
                    "last_response": "Something went wrong. Please try again."
                }

        return all_updates

    def _merge_updates(
        self,
        existing: dict[str, Any],
        new: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge state updates, with special handling for lists."""
        result = existing.copy()
        for key, value in new.items():
            if key in result and isinstance(result[key], list):
                result[key] = result[key] + value
            else:
                result[key] = value
        return result
```

---

## SoniDU (NLU Provider)

### Responsibility

Produces Commands from user input using LLM. The LLM's ONLY job is to interpret, not to decide.

### Interface

```python
class INLUProvider(Protocol):
    """Protocol for NLU providers."""

    async def understand(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext
    ) -> NLUOutput:
        """
        Understand user message and produce commands.

        Returns:
            NLUOutput with list of Commands
        """
        ...
```

### Output Structure

```python
class NLUOutput(BaseModel):
    """Output from NLU containing commands."""

    commands: list[Command]
    """List of commands extracted from user message."""

    entities: list[ExtractedEntity]
    """Raw extracted entities (before slot mapping)."""

    confidence: float
    """Overall confidence in extraction."""

    reasoning: str
    """Step-by-step reasoning (from CoT)."""
```

### Implementation

```python
class SoniDU(dspy.Module):
    """
    Soni Dialogue Understanding module.

    Produces Commands from user input using DSPy.
    """

    def __init__(self, cache_size: int = 1000, cache_ttl: int = 300):
        super().__init__()
        self.predictor = dspy.ChainOfThought(CommandExtraction)
        self.cache: TTLCache[str, NLUOutput] = TTLCache(
            maxsize=cache_size,
            ttl=cache_ttl
        )

    async def understand(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext
    ) -> NLUOutput:
        """Extract commands from user message."""

        cache_key = self._cache_key(user_message, history, context)
        if cache_key in self.cache:
            return self.cache[cache_key]

        prediction = await self.predictor.acall(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=datetime.now().isoformat()
        )

        result: NLUOutput = prediction.result
        self.cache[cache_key] = result

        return result
```

---

## RuntimeLoop

### Responsibility

Main orchestrator. Receives messages, invokes graph, returns responses.

### Implementation

```python
class RuntimeLoop:
    """
    Main orchestrator for conversation management.

    Thin coordinator - delegates all logic to specialized components.
    """

    def __init__(
        self,
        graph: CompiledGraph,
        context: RuntimeContext,
        checkpointer: BaseCheckpointSaver
    ):
        self.graph = graph
        self.context = context
        self.checkpointer = checkpointer

    async def process_message(self, msg: str, user_id: str) -> str:
        """
        Process user message.

        Args:
            msg: User message text
            user_id: Unique user identifier

        Returns:
            Assistant response text
        """
        config = {"configurable": {"thread_id": user_id}}

        # Check for interrupted state
        current_state = await self.graph.aget_state(config)

        if current_state.next:
            # Resume interrupted conversation
            result = await self.graph.ainvoke(
                Command(resume={"user_message": msg}),
                config=config,
                context=self.context
            )
        else:
            # Start new conversation
            input_state = create_initial_state()
            input_state["user_message"] = msg
            result = await self.graph.ainvoke(
                input_state,
                config=config,
                context=self.context
            )

        return result["last_response"]
```

---

## FlowManager

### Responsibility

Manages flow stack (push/pop) and slot storage.

### Interface

```python
class FlowManager:
    """Manages flow stack and flow-scoped data."""

    def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict[str, Any] | None = None
    ) -> str:
        """Start new flow. Returns flow_id."""
        ...

    def pop_flow(
        self,
        state: DialogueState,
        outputs: dict[str, Any] | None = None,
        result: str = "completed"
    ) -> None:
        """Finish current flow."""
        ...

    def get_active_context(self, state: DialogueState) -> FlowContext | None:
        """Get currently active flow."""
        ...

    def get_slot(self, state: DialogueState, slot_name: str) -> Any:
        """Get slot value from active flow."""
        ...

    def set_slot(self, state: DialogueState, slot_name: str, value: Any) -> None:
        """Set slot value in active flow."""
        ...
```

---

## FlowStepManager

### Responsibility

Manages step progression within a flow. Key method: `advance_through_completed_steps`.

### Key Methods

```python
class FlowStepManager:
    """Manages flow step progression."""

    def advance_through_completed_steps(
        self,
        state: DialogueState,
        context: RuntimeContext
    ) -> dict[str, Any]:
        """
        Advance through completed steps until finding incomplete one.

        Used after setting slots - may skip multiple completed steps.
        """
        ...

    def get_current_step_config(
        self,
        state: DialogueState,
        context: RuntimeContext
    ) -> StepConfig | None:
        """Get configuration for current step."""
        ...

    def is_step_complete(
        self,
        state: DialogueState,
        step_config: StepConfig,
        context: RuntimeContext
    ) -> bool:
        """Check if current step is complete."""
        ...
```

---

## RuntimeContext

### Responsibility

Dependency injection container for LangGraph nodes.

### Structure

```python
@dataclass
class RuntimeContext:
    """Runtime context with injected dependencies."""

    config: SoniConfig
    flow_manager: FlowManager
    step_manager: FlowStepManager
    nlu_provider: INLUProvider
    command_executor: CommandExecutor
    action_handler: IActionHandler
    validator: IValidator
    normalizer: INormalizer
    help_generator: IHelpGenerator
```

---

## Component Interactions

```
User Message
  ↓
RuntimeLoop.process_message()
  ├─ Check LangGraph state (interrupted?)
  └─ Invoke graph with context
  ↓
understand_node (LangGraph node)
  ├─ Build NLU context
  ├─ Call SoniDU.understand()
  └─ Returns: NLUOutput with Commands
  ↓
execute_commands_node (LangGraph node)
  ├─ CommandExecutor.execute(commands)
  │   ├─ For each command:
  │   │   ├─ Registry.get(command_type)
  │   │   ├─ Handler.execute(command)
  │   │   └─ Merge state updates
  │   └─ Log all commands (audit)
  └─ Returns: merged state updates
  ↓
Deterministic routing based on conversation_state
  ├─ waiting_for_slot → collect_next_slot → interrupt()
  ├─ executing_action → execute_action_node
  ├─ confirming → confirm_action_node → interrupt()
  └─ completed → generate_response → END
  ↓
Response returned to user
```

---

## Summary

Soni v2.0 components follow strict SOLID principles:

| Component | Responsibility | Pattern |
|-----------|----------------|---------|
| **Commands** | Pure data representing intent | Value Object |
| **Handlers** | Execute individual commands | Strategy |
| **Registry** | Map types to handlers | Registry |
| **Executor** | Coordinate execution | Coordinator |
| **SoniDU** | Produce commands from text | Adapter |
| **RuntimeLoop** | Orchestrate message flow | Facade |
| **FlowManager** | Flow stack operations | Manager |
| **FlowStepManager** | Step progression | Manager |

**Key Benefits**:
- **OCP**: New command = new handler + registry entry
- **SRP**: Each component has single responsibility
- **DIP**: All dependencies injected via RuntimeContext
- **Testability**: Each component testable in isolation

## Next Steps

- **[04-state-machine.md](04-state-machine.md)** - DialogueState schema
- **[11-commands.md](11-commands.md)** - Complete Command specification
- **[12-conversation-patterns.md](12-conversation-patterns.md)** - Pattern reference

---

**Design Version**: v2.0 (Command-Driven Architecture)
**Status**: Production-ready design specification
