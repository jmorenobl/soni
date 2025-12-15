# Conversational Patterns (Runtime Behavior)

[← Back to Index](00-index.md) | [← Step Types](05-step-types.md)

---

## 8. Conversational Patterns

Human conversations are messy. Users correct themselves, interrupt, ask questions, and change their minds. Soni handles these patterns through **Conversational Patterns**—reusable, declarative logic that runs outside standard flows.

### 8.1 Pattern Configuration

Patterns are configured in `soni.yaml` (see [Configuration](02-configuration.md)):

```yaml
conversation_patterns:
  correction:
    enabled: true
    behavior: reprompt_corrected_slot

  clarification:
    enabled: true
    max_depth: 3
    fallback: human_handoff

  cancellation:
    enabled: true
    confirm_before_cancel: false
```

### 8.2 Supported Patterns

| Pattern | Command Trigger | Description |
|---------|-----------------|-------------|
| **Correction** | `CorrectSlot` | User fixes a previously given value ("I meant Barcelona") |
| **Modification** | `CorrectSlot` | User changes a value ("Actually, make it 2 people") |
| **Cancellation** | `CancelFlow` | User wants to stop ("Forget it") |
| **Clarification** | `Clarify` | User asks why ("Why do you need that?") |
| **Confirmation** | `Affirm`/`Deny` | User responds to confirmation prompt |
| **Handoff** | `HumanHandoff` | User requests human agent |
| **Out of Scope** | `OutOfScope` | User asks something unsupported |

### 8.3 Pattern Behavior

#### Correction & Modification

**Trigger**: `CorrectSlot` command from NLU.

**Behavior**:
1. Update the target slot with the new value.
2. Mark the slot as filled.
3. If inside a `confirm` step:
    - Re-generate the confirmation message.
    - Stay in the `confirm` step.
4. If inside a `collect` step (or elsewhere):
    - Return to the flow to re-validate or proceed.

**Example**:
```
Bot: "Flying from Madrid to San Francisco. Confirm?"
User: "Change destination to San Diego"
→ Command: CorrectSlot(slot="destination", value="San Diego")
→ Bot updates slot
→ Bot: "Flying from Madrid to San Diego. Confirm?"
```

#### Clarification

**Trigger**: `Clarify` command.

**Behavior**:
1. Check `clarification_depth`. If exceeded → Handoff.
2. Generate explanation using LLM (context includes current flow/slot).
3. Send explanation.
4. Re-prompt for the current slot.

**Example**:
```
Bot: "What is your email?"
User: "Why do you need it?"
→ Command: Clarify(topic="email purpose")
→ Bot: "I need your email to send the booking confirmation."
→ Bot: "What is your email?"
```

#### Cancellation

**Trigger**: `CancelFlow` command.

**Behavior**:
1. Check `confirm_before_cancel` setting.
2. If true, ask for confirmation.
3. If confirmed (or false), **pop the current flow**.
4. Resume parent flow (if any) or go to idle.

### 8.4 Multi-Command Processing

Users often combine intents. Soni processes a **list of Commands**:

```
User: "Forget the hotel, book me a flight instead."
```

**NLU Output**:
```python
[
  CancelFlow(reason="user request"),
  StartFlow(flow_name="book_flight")
]
```

**Execution**:
1. `CancelFlow` executes → Pops "book_hotel" flow.
2. `StartFlow` executes → Pushes "book_flight" flow.

### 8.5 State Variables

The runtime sets variables available in conditions/responses:

| Variable | Type | Description |
|----------|------|-------------|
| `_last_command_type` | string | Type of last command (e.g., `SetSlot`, `Clarify`) |
| `_correction_slot` | string | Slot that was corrected |
| `_correction_value` | any | New value |
| `_clarification_topic` | string | Topic of clarification |

### 8.6 Override in Steps

You can override global pattern behavior in specific steps:

```yaml
- step: get_date
  type: collect
  slot: departure_date
  on_cancel: custom_cancel_handler  # Overrides global cancellation
```

[Next: Control Flow & Errors →](07-control-error.md)
