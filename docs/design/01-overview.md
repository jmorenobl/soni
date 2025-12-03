# Soni Framework - Overview

## What is Soni?

Soni is a **conversational dialogue system** designed to build task-oriented chatbots using a declarative YAML configuration combined with automatic prompt optimization. The framework enables developers to create sophisticated multi-turn conversations without manual prompt engineering.

## Core Features

### Declarative Flow Definition

Define dialogue flows in YAML without writing Python code:

```yaml
flows:
  book_flight:
    description: "Book a new flight reservation"
    slots:
      - origin
      - destination
      - departure_date
    steps:
      - step: collect_slots
        type: collect
      - step: search_flights
        type: action
        call: search_flights_api
      - step: confirm_booking
        type: confirm
```

### Automatic Prompt Optimization

Use DSPy to optimize NLU prompts based on business metrics:

```python
# Define metrics
def intent_accuracy(example, prediction):
    return prediction.intent == example.intent

# Optimize
optimizer = MIPROv2(metric=intent_accuracy)
optimized_module = optimizer.compile(module, trainset=examples)
```

### Complex Conversation Support

Handle realistic human communication patterns:
- **Flow interruptions**: User starts new task mid-conversation
- **Digressions**: User asks questions, seeks clarifications
- **Flow resumption**: User returns to previous tasks
- **State preservation**: Maintain context across interruptions

### Context-Aware NLU

Single NLU provider with enriched context that handles:
- Slot value extraction
- Intent detection and changes
- Digression detection (questions, clarifications, corrections)
- Resume request identification

### Zero-Leakage Architecture

Clear separation between semantics and implementation:
- **YAML**: Describes WHAT should happen (business logic)
- **Python**: Implements HOW it happens (technical details)

Business analysts can modify flows without touching code.

### State Persistence

Multi-turn conversations with automatic checkpointing:
- Conversations persist across sessions
- Automatic state saving after each turn
- Support for SQLite, PostgreSQL, and Redis backends

## System Goals

### Primary Goals

1. **Correctness**: Dialogue flows execute correctly according to configuration
2. **Efficiency**: Minimize LLM calls, latency, and token usage
3. **Developer Experience**: Easy to configure, debug, and extend
4. **User Experience**: Natural, responsive conversations
5. **Scalability**: Support hundreds of concurrent conversations

### Non-Goals

- **General-purpose chatbot**: Soni focuses on task-oriented dialogues with specific goals
- **Multilingual support**: v0.5 supports English only (internationalization planned for future)
- **Voice/speech processing**: Text-only interface (voice can be added at integration layer)
- **Real-time streaming**: Async responses only (streaming planned for future)

## Use Cases

### Flight Booking System

```yaml
flows:
  book_flight:
    slots: [origin, destination, date]
  modify_booking:
    slots: [booking_ref, new_date]
  cancel_booking:
    slots: [booking_ref, reason]
```

**Conversation example**:
```
User: I want to book a flight
Bot:  Where would you like to fly from?
User: What cities do you support?           # Digression
Bot:  We support NYC, LA, Chicago, Boston, etc.
      Where would you like to fly from?
User: New York
Bot:  Great! Where would you like to fly to?
User: Actually, let me check my booking first  # Flow interruption
Bot:  Sure! What's your booking reference?
[... completes check_booking ...]
Bot:  Would you like to continue booking a new flight?
User: Yes
Bot:  Where would you like to fly to?      # Resumes book_flight
```

### Customer Support System

```yaml
flows:
  check_order_status:
    slots: [order_id]
  track_shipment:
    slots: [tracking_number]
  request_refund:
    slots: [order_id, reason]
  update_address:
    slots: [order_id, new_address]
```

Handles complex scenarios where customers:
- Ask questions about policies
- Switch between different support tasks
- Need clarification on requirements
- Correct information provided earlier

### Appointment Scheduling

```yaml
flows:
  book_appointment:
    slots: [service_type, preferred_date, preferred_time]
  reschedule_appointment:
    slots: [appointment_id, new_date, new_time]
  cancel_appointment:
    slots: [appointment_id, cancellation_reason]
```

Manages:
- Availability checking
- Calendar conflicts
- Multi-step booking process
- Confirmation and reminders

## Key Benefits

### For Developers

- **Fast development**: Define flows in YAML, not code
- **Easy debugging**: Explicit state tracking shows exactly where conversations are
- **Extensible**: Plugin architecture for actions, validators, NLU providers
- **Type-safe**: Full Python type hints throughout
- **Well-tested**: Comprehensive test coverage

### For Data Scientists

- **Automatic optimization**: DSPy optimizes prompts based on metrics
- **Measurable quality**: Track intent accuracy, slot extraction F1, etc.
- **Iterative improvement**: Collect conversation data, retrain, deploy
- **Multiple optimizers**: MIPROv2, SIMBA, BootstrapFewShot, etc.

### For Product Managers

- **Declarative configuration**: Flows are readable by non-developers
- **Rapid iteration**: Change flows without redeployment
- **Clear boundaries**: Separate business logic from technical implementation
- **Audit trail**: Complete conversation tracking for analysis

### For End Users

- **Natural conversations**: System handles questions, corrections, interruptions
- **Context preservation**: Return to previous tasks without losing progress
- **Helpful responses**: System can answer questions about its capabilities
- **Error recovery**: Graceful handling of unclear inputs

## Technology Overview

### Core Stack

- **Python 3.11+**: Modern async/await, type hints, performance
- **LangGraph 1.0.4+**: State graph execution, automatic checkpointing
- **DSPy 3.0.4+**: Automatic prompt optimization
- **FastAPI 0.122.0+**: Async web framework, WebSocket support
- **Pydantic 2.12.5+**: Data validation and schema enforcement

### LLM Providers

- **OpenAI**: GPT-4o-mini for fast NLU, GPT-4o for generation
- **Anthropic**: Claude-3-haiku for NLU, Claude-3-sonnet for generation
- **Local models**: Support for local LLMs via LiteLLM

### Persistence Options

- **SQLite**: Development and small deployments
- **PostgreSQL**: Production deployments with high concurrency
- **Redis**: High-performance, distributed deployments

## How It Works

### Message Processing Flow

```
User Message
  ↓
Check LangGraph State
  ├─ If interrupted → Resume with Command(resume=msg)
  └─ If new → Start with initial state
  ↓
Understand Node (NLU with enriched context)
  ↓
Analyze NLU Result
  ├─ Slot value → Validate and store
  ├─ Digression → Answer question, re-prompt
  ├─ Intent change → Push/pop flow stack
  └─ Continue → Next step in flow
  ↓
Execute Action (if needed)
  ↓
Generate Response
  ↓
Save State (automatic checkpoint)
  ↓
Return Response to User
```

### Key Pattern: Always Through NLU

Every user message flows through the NLU first:

```
User: "New York"           → NLU detects: slot value
User: "What cities?"       → NLU detects: digression (question)
User: "Actually, cancel"   → NLU detects: intent change
User: "Go back to booking" → NLU detects: resume request
```

This unified approach handles realistic human communication where users don't always provide direct answers.

### Flow Stack for Complex Conversations

```
Turn 1: User starts book_flight
Stack: [book_flight(ACTIVE)]

Turn 2: User says "Let me check my booking first"
Stack: [book_flight(PAUSED), check_booking(ACTIVE)]

Turn 3: check_booking completes
Stack: [book_flight(ACTIVE)]  # Automatically resumes
```

## Example Configuration

```yaml
# soni.yaml
project:
  name: "Flight Booking Assistant"
  version: "1.0.0"

nlu:
  provider: "dspy"
  model: "gpt-4o-mini"
  temperature: 0.0

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
      - name: origin
        entity: city
        prompt: "Where would you like to fly from?"
        required: true

      - name: destination
        entity: city
        prompt: "Where would you like to fly to?"
        required: true

      - name: departure_date
        entity: date
        prompt: "What date would you like to depart?"
        required: true

    steps:
      - step: collect_slots
        type: collect

      - step: confirm_details
        type: confirm
        message: "Let me confirm your flight details:"

      - step: search_flights
        type: action
        call: search_flights_api
        map_outputs:
          flights: available_flights
          cheapest_price: min_price

      - step: present_options
        type: response
        template: "Found {num_flights} flights. Cheapest: ${min_price}"

actions:
  search_flights_api:
    inputs: [origin, destination, departure_date]
    outputs: [flights, cheapest_price]
```

## Next Steps

- **[02-architecture.md](02-architecture.md)** - Understand the architectural principles and design
- **[03-components.md](03-components.md)** - Learn about system components
- **[examples/](../../examples/)** - See working examples

---

**Design Version**: v0.8 (Production-Ready with Structured Types)
**Status**: Production-ready design specification
