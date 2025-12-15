# Soni Framework - Overview

## What is Soni?

Soni is a **command-driven conversational dialogue system** designed to build reliable, task-oriented chatbots using a declarative YAML configuration combined with automatic prompt optimization. The framework separates language understanding from dialogue management, enabling deterministic, auditable conversations.

**Key Innovation**: Soni uses an explicit **Command layer** between Dialogue Understanding (DU) and Dialogue Management (DM). The LLM interprets user intent, but the DM executes deterministically.

## Core Architecture

```
User Message → Dialogue Understanding → [Commands] → Dialogue Manager → Action → Response
                      (LLM)              (Explicit)    (Deterministic)
```

### Why Command-Driven?

| Traditional Approach | Soni's Approach |
|---------------------|-----------------|
| LLM classifies → DM routes on classification | LLM produces Commands → DM executes Commands |
| LLM influences execution flow | LLM only interprets, DM decides |
| Hard to audit/debug | Explicit command log, fully auditable |
| Single intent per message | Multiple commands per message |

## Core Features

### Command-Based Dialogue Understanding

NLU produces structured Commands that the DM executes deterministically:

```python
# User: "Actually, change the destination to Barcelona"
commands = [
    CorrectSlot(slot_name="destination", new_value="Barcelona")
]

# User: "Cancel this and check my balance"
commands = [
    CancelFlow(reason="user_request"),
    StartFlow(flow_name="check_balance")
]
```

### Conversation Patterns

Declarative handling of non-happy-path scenarios:

```yaml
conversation_patterns:
  correction:
    enabled: true
    behavior: reprompt_corrected_slot

  clarification:
    enabled: true
    max_depth: 3
    fallback: human_handoff

  human_handoff:
    enabled: true
    trigger_conditions:
      - clarification_depth > 3
      - explicit_request
```

**Built-in Patterns**:
- **Correction**: User fixes previously provided values
- **Clarification**: User asks for explanation
- **Cancellation**: User wants to stop current flow
- **Interruption**: User wants to do something else
- **Human Handoff**: User requests human agent
- **Out of Scope**: Request outside bot capabilities

### Declarative Flow Definition

Define dialogue flows in YAML without writing Python code:

```yaml
flows:
  book_flight:
    description: "Book a new flight reservation"

    slots:
      origin:
        type: city
        prompt: "Where would you like to fly from?"

      destination:
        type: city
        prompt: "Where would you like to fly to?"

      departure_date:
        type: date
        prompt: "What date would you like to depart?"

    steps:
      - collect: [origin, destination, departure_date]
      - action: search_flights
      - confirm: "Confirm your booking?"
      - action: book_flight
```

### Automatic Prompt Optimization

Use DSPy to optimize NLU prompts for Command extraction:

```python
def command_accuracy(example, prediction):
    """Measure command extraction accuracy."""
    expected = {type(c).__name__ for c in example.commands}
    predicted = {type(c).__name__ for c in prediction.commands}
    return len(expected & predicted) / len(expected | predicted)

optimizer = MIPROv2(metric=command_accuracy)
optimized_module = optimizer.compile(module, trainset=examples)
```

### Complex Conversation Support

Handle realistic human communication patterns:
- **Flow interruptions**: User starts new task mid-conversation
- **Corrections**: User fixes previously provided information
- **Clarifications**: User asks questions without leaving flow
- **Flow resumption**: User returns to previous tasks
- **Multiple intents**: Handle compound requests in single message

### Zero-Leakage Architecture

Clear separation between semantics and implementation:
- **YAML**: Describes WHAT should happen (flows, patterns, slots)
- **Python**: Implements HOW it happens (actions, validators, normalizers)

Business analysts can modify flows without touching code.

### State Persistence

Multi-turn conversations with automatic checkpointing:
- Conversations persist across sessions
- Automatic state saving after each turn
- Support for SQLite, PostgreSQL, and Redis backends

## System Goals

### Primary Goals

1. **Deterministic Execution**: DM behavior is predictable and auditable
2. **Reliability**: Conversations follow defined flows, no hallucination
3. **Developer Experience**: Easy to configure, debug, and extend
4. **User Experience**: Natural, responsive conversations
5. **Scalability**: Support hundreds of concurrent conversations

### Non-Goals

- **General-purpose chatbot**: Soni focuses on task-oriented dialogues with specific goals
- **Multilingual support**: v2.0 supports English only (internationalization planned)
- **Voice/speech processing**: Text-only interface (voice added at integration layer)

## How It Works

### Message Processing Flow

```
User Message
  ↓
Dialogue Understanding (SoniDU)
  ├─ Extract entities
  ├─ Analyze intent
  └─ Produce Commands (pure data)
  ↓
Command Executor (Deterministic)
  ├─ For each Command:
  │   ├─ Lookup Handler in Registry
  │   └─ Handler.execute(command, state, context)
  ├─ Merge state updates
  └─ Log commands for audit
  ↓
DM State Machine (Deterministic)
  ├─ Determine next step
  ├─ Check if action needed
  └─ Update conversation state
  ↓
Execute Action (if needed)
  ↓
Generate Response
  ↓
Save State (automatic checkpoint)
  ↓
Return Response to User
```

### Handler Registry Pattern

Commands are **pure data** (Pydantic models), handlers contain **behavior**:

```python
# Commands = Data (serializable, testable)
class StartFlow(Command):
    flow_name: str
    slots: dict[str, Any] = {}

# Handlers = Behavior (one per command type)
class StartFlowHandler(CommandHandler):
    async def execute(self, cmd: StartFlow, state, context) -> dict:
        context.flow_manager.push_flow(state, cmd.flow_name)
        return {"conversation_state": "waiting_for_slot"}

# Registry = Mapping (Open/Closed principle)
registry = {StartFlow: StartFlowHandler(), SetSlot: SetSlotHandler(), ...}

# Executor = Coordinator (cross-cutting concerns)
for command in commands:
    handler = registry[type(command)]
    updates = await handler.execute(command, state, context)
```

**SOLID Benefits:**
- **SRP**: Commands = data, Handlers = execution, Executor = coordination
- **OCP**: New command = new handler class + registry entry (no existing code modified)
- **DIP**: Executor depends on Protocol, not concrete handlers

### Key Pattern: LLM for Understanding Only

The LLM **only** produces Commands, never decides what to do:

```
User: "New York"           → SetSlot(origin, "New York")
User: "What cities?"       → Clarify(topic="supported_cities")
User: "Actually, cancel"   → CancelFlow()
User: "Go back to booking" → StartFlow("book_flight", resume=True)
User: "Change dest to LA"  → CorrectSlot(destination, "Los Angeles")
```

### Flow Stack for Complex Conversations

```
Turn 1: User starts book_flight
Stack: [book_flight(ACTIVE)]

Turn 2: User says "Let me check my booking first"
Commands: [StartFlow("check_booking")]
Stack: [book_flight(PAUSED), check_booking(ACTIVE)]

Turn 3: check_booking completes
Stack: [book_flight(ACTIVE)]  # Automatically resumes
```

## Example Configuration

```yaml
# soni.yaml
project:
  name: "Flight Booking Assistant"
  version: "2.0.0"

nlu:
  provider: "dspy"
  model: "gpt-4o-mini"
  temperature: 0.0

# Conversation patterns (new in v2.0)
conversation_patterns:
  correction:
    enabled: true
  clarification:
    enabled: true
    max_depth: 3
  human_handoff:
    enabled: true

entities:
  city:
    type: "string"
    normalizer: "city_normalizer"
    validator: "valid_airport_city"

  date:
    type: "string"
    normalizer: "date_normalizer"
    validator: "future_date_only"

flows:
  book_flight:
    description: "Book a new flight reservation"

    slots:
      origin:
        entity: city
        prompt: "Where would you like to fly from?"
        required: true

      destination:
        entity: city
        prompt: "Where would you like to fly to?"
        required: true

      departure_date:
        entity: date
        prompt: "What date would you like to depart?"
        required: true

    steps:
      - collect: [origin, destination, departure_date]
      - action: search_flights
      - confirm: "Let me confirm your flight details:"
      - action: book_flight

actions:
  search_flights:
    inputs: [origin, destination, departure_date]
    outputs: [flights, cheapest_price]

  book_flight:
    inputs: [origin, destination, departure_date, selected_flight]
    outputs: [booking_ref]
```

## Use Cases

### Flight Booking System

**Conversation example**:
```
User: I want to book a flight
      → Commands: [StartFlow("book_flight")]
Bot:  Where would you like to fly from?

User: What cities do you support?
      → Commands: [Clarify(topic="supported_cities")]
Bot:  We support NYC, LA, Chicago, Boston, etc.
      Where would you like to fly from?

User: New York
      → Commands: [SetSlot(origin, "New York")]
Bot:  Where would you like to fly to?

User: Actually, let me check my booking first
      → Commands: [StartFlow("check_booking")]
Bot:  Sure! What's your booking reference?

[... completes check_booking ...]

Bot:  Would you like to continue booking a new flight?
User: Yes, to Los Angeles
      → Commands: [SetSlot(destination, "Los Angeles")]
Bot:  What date would you like to depart?
```

### Customer Support System

Handles complex scenarios where customers:
- Ask questions about policies (Clarify command)
- Switch between different support tasks (StartFlow command)
- Correct information provided earlier (CorrectSlot command)
- Request human agent (HumanHandoff command)

## Technology Overview

### Core Stack

- **Python 3.11+**: Modern async/await, type hints, performance
- **LangGraph 1.0.4+**: State graph execution, automatic checkpointing
- **DSPy 3.0.4+**: Automatic prompt optimization
- **FastAPI 0.122.0+**: Async web framework, WebSocket support
- **Pydantic 2.12.5+**: Data validation and schema enforcement

### Persistence Options

- **SQLite**: Development and small deployments
- **PostgreSQL**: Production deployments with high concurrency
- **Redis**: High-performance, distributed deployments

## Next Steps

- **[02-architecture.md](02-architecture.md)** - Understand the command-driven architectural principles
- **[03-components.md](03-components.md)** - Learn about system components
- **[11-commands.md](11-commands.md)** - Complete Command layer specification
- **[12-conversation-patterns.md](12-conversation-patterns.md)** - Conversation Patterns reference

---

**Design Version**: v2.0 (Command-Driven Architecture)
**Status**: Production-ready design specification
