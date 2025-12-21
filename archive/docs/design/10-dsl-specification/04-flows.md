# Flows (Conversation Logic)

[← Back to Index](00-index.md) | [← Data Model](03-data-model.md)

---

## 6. Flows

Flows define the sequences of interaction. Each flow is a named process with:
- **Triggers**: When to activate the flow
- **Inputs/Outputs**: Data interface with other flows
- **Process**: Sequence of steps

### 6.1 Flow Structure

```yaml
flows:
  book_flight:
    description: "Complete flight booking process"

    trigger:
      intents:
        - "I want to book a flight"
        - "Book me a flight to Paris"
        - "I need to fly to London next week"

    inputs:
      - origin?        # Optional: may come from previous flow
      - destination?   # Optional

    outputs:
      - booking_reference
      - confirmation_details

    process:
      # Steps defined here (Section 7)
      ...
```

### 6.2 Flow Fields

| Field | Required | Description |
|-------|----------|-------------|
| `description` | Yes | Human-readable purpose |
| `trigger.intents` | No | Example phrases that activate this flow |
| `trigger.condition` | No | Condition that must be true to trigger |
| `inputs` | No | Slots passed in when flow starts (`?` = optional) |
| `outputs` | No | Slots returned when flow completes |
| `process` | Yes | List of steps |
| `on_error` | No | Global error handler for this flow |
| `interruptible` | No | If `false`, flow cannot be interrupted (default: `true`) |

**Using `trigger.condition`:**

In addition to `StartFlow` command training (via `intents`), you can require a condition to be true:

```yaml
flows:
  premium_support:
    description: "Premium customer support flow"
    trigger:
      intents:
        - "I need help"
        - "Support please"
      condition: "session.membership_level == 'premium'"
    process:
      - step: greet
        type: say
        message: "Welcome to premium support! How can I help?"

  modify_booking:
    description: "Modify an existing booking"
    trigger:
      intents:
        - "Change my booking"
        - "Modify reservation"
      condition: "session.has_active_booking == true"
    process:
      # ... steps ...
```

**Trigger Logic:**
- If only `intents`: Soni uses these examples to train the NLU to generate a `StartFlow` command for this flow.
- If only `condition`: Flow activates when condition is true (evaluated each turn)
- If both: Flow activates when intent matches **AND** condition is true
- If `intents: []` (empty): Same as no `intents` - only `condition` is used
- If no `trigger` at all: Flow can only be invoked via `call_flow` or API

**⚠️ Warning:** Using only `condition` without `intents` creates a "passive trigger" that is evaluated on every user message while no flow is active. Ensure the condition is specific enough to prevent unintended activations:

```yaml
# GOOD: Specific condition
trigger:
  condition: "session.pending_payment == true and session.payment_reminder_sent == false"

# BAD: Always-true condition (will trigger on every message!)
trigger:
  condition: "session.user_id != null"  # Almost always true
```

### 6.3 Special Flows

Certain flow names have special meaning:

```yaml
flows:
  # ─── Required Special Flows ───

  welcome:
    description: "Initial flow when conversation starts"
    process:
      - step: greet
        type: say
        message: "Hello! I'm your flight assistant. How can I help you today?"

  fallback:
    description: "Flow when no trigger matches"
    process:
      - step: apologize
        type: say
        response: fallback_no_match
      - step: suggest
        type: generate
        instruction: "Suggest what the user can do based on available flows"

  # ─── Optional Special Flows ───

  goodbye:
    description: "Flow when user wants to end conversation"
    trigger:
      intents:
        - "bye"
        - "goodbye"
        - "that's all"
    process:
      - step: farewell
        type: say
        message: "Goodbye! Have a great day."

  help:
    description: "Flow when user asks for help"
    trigger:
      intents:
        - "help"
        - "what can you do"
    process:
      - step: explain
        type: generate
        instruction: "Explain available capabilities based on defined flows"
```

| Special Flow | Purpose | Required |
|--------------|---------|----------|
| `welcome` | First interaction in a new session | Yes |
| `fallback` | No trigger matches user input | Yes |
| `goodbye` | User wants to end conversation | No |
| `help` | User asks for assistance | No |

**Flows Without Triggers:**

Flows without `trigger` can only be invoked via:
- `call_flow` from another flow
- Direct API call: `runtime.start_flow(session_id, "flow_name")`

This is useful for reusable sub-flows (e.g., `collect_payment`, `verify_identity`).

### 6.4 Flow Inputs/Outputs

Flows can receive inputs and produce outputs, enabling **composition**:

```yaml
flows:
  select_from_list:
    description: "Generic flow to let user select from a list"
    inputs:
      - items          # List to select from
      - prompt_text    # Question to ask
    outputs:
      - selected_item  # User's selection
    process:
      - step: show_options
        type: say
        message: "{prompt_text}"
      - step: get_selection
        type: collect
        slot: selected_item
```

**Output Behavior:**
- Declared `outputs` are copied to parent flow state when flow completes
- If a declared output is not set, it is passed as `null` to the parent
- Undeclared variables are **not** passed (flow state is isolated)
- If flow ends via `error`, no outputs are passed

```yaml
# Parent flow
- step: get_selection
  type: call_flow
  flow: select_from_list
  inputs:
    items: flights
  outputs:
    selected_item: chosen_flight  # Will be null if not set in sub-flow
```

---

[Next: Step Types →](05-step-types.md)
