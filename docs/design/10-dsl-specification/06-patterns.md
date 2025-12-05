# Conversational Patterns (Runtime Behavior)

[← Back to Index](00-index.md) | [← Step Types](05-step-types.md)

---

## 8. Conversational Patterns

Human conversations are messy. Users correct themselves, interrupt, ask questions, and change their minds. The runtime handles these patterns **automatically** without requiring explicit DSL configuration.

### 8.1 Pattern Types

| Pattern | Description | Example | Runtime Behavior |
|---------|-------------|---------|------------------|
| **Correction** | User fixes a previously given value | "No wait, I said San Diego not San Francisco" | Update slot, return to current step |
| **Slot Modification** | User wants to change a specific slot | "Change the destination to LA" | Update slot, return to confirmation |
| **Interruption** | User starts a completely new task | "Actually, first check hotel prices" | Push new flow, pause current |
| **Digression** | Off-topic question without changing flow | "What airlines fly that route?" | Answer, return to same point |
| **Clarification** | User asks why information is needed | "Why do you need my email?" | Explain, re-prompt same slot |
| **Cancellation** | User wants to abandon | "Forget it, cancel everything" | Pop flow, return to previous or idle |
| **Partial Confirmation** | User confirms but requests a change | "Yes, but make it 2 passengers" | Update slot, re-confirm |

**Cancellation During `collect`:**

Users can cancel at any point, not just during `confirm`:

```
Bot: "What date would you like to depart?"
User: "Never mind, forget it"
→ Runtime detects CANCELLATION
→ Current flow is popped from stack
→ Returns to parent flow or idle state
```

To handle cancellation explicitly in a `collect` step:

```yaml
- step: get_date
  type: collect
  slot: departure_date
  on_cancel: handle_cancel  # Optional: custom handler

- step: handle_cancel
  type: say
  message: "No problem. Let me know if you change your mind!"
  jump_to: end
```

If `on_cancel` is not specified, the default behavior applies (pop flow, return to previous).

### 8.2 Correction vs Modification

**Correction**: User realizes they made a mistake in what they said:
```
Bot: "Flying from Madrid to San Francisco on Dec 15th. Confirm?"
User: "Sorry, I said San Francisco but I meant San Diego"
→ Runtime detects correction of 'destination'
→ Updates destination = "San Diego"
→ Returns to confirmation step (NOT restart)
```

**Modification**: User wants to intentionally change a value:
```
Bot: "Flying from Madrid to San Francisco on Dec 15th. Confirm?"
User: "Change the date to December 20th"
→ Runtime detects modification request for 'departure_date'
→ Updates departure_date = "2024-12-20"
→ Returns to confirmation step
```

Both patterns are handled the same way: **update the slot, return to current step**.

### 8.3 Multi-Slot Extraction

Users often provide multiple pieces of information in a single message:

```
User: "I want to fly from Madrid to Paris on December 15th"
```

The NLU extracts **all slots** from a single utterance:
- `origin` = "Madrid"
- `destination` = "Paris"
- `departure_date` = "2024-12-15"

**Behavior:**
1. All extracted slots are stored in flow state
2. Subsequent `collect` steps for those slots are **skipped** (already filled)
3. Flow continues to the next unfilled slot or action

**Example Flow:**

```yaml
process:
  - step: get_origin
    type: collect
    slot: origin          # SKIPPED if already extracted

  - step: get_destination
    type: collect
    slot: destination     # SKIPPED if already extracted

  - step: get_date
    type: collect
    slot: departure_date  # SKIPPED if already extracted

  - step: search
    type: action
    call: search_flights  # Proceeds directly here
```

**Partial Extraction:**

If user only provides some slots:
```
User: "I want to fly to Paris"
```
- `destination` = "Paris" (extracted)
- `origin` = ? (will be asked)
- `departure_date` = ? (will be asked)

### 8.4 NLU Detection

The NLU classifies each user message into one of these types:

```python
class MessageType(str, Enum):
    """Type of user message."""
    SLOT_VALUE = "slot_value"           # Direct answer to current prompt
    CORRECTION = "correction"            # Fixing a previous value
    MODIFICATION = "modification"        # Requesting to change a slot
    INTERRUPTION = "interruption"        # New intent/flow
    DIGRESSION = "digression"            # Question without flow change
    CLARIFICATION = "clarification"      # Asking for explanation
    CANCELLATION = "cancellation"        # Wants to stop
    CONFIRMATION = "confirmation"        # Yes/no to confirm prompt
    CONTINUATION = "continuation"        # General continuation
```

For corrections and modifications, the NLU also extracts:
- `target_slot`: Which slot is being corrected/modified
- `new_value`: The new value

### 8.5 Automatic Behavior During Confirmation

The `confirm` step has **built-in intelligence** for handling user responses:

```yaml
- step: confirm_booking
  type: confirm
  message: |
    Please confirm:
    - From: {origin}
    - To: {destination}
    - Date: {departure_date}
```

**User says "Yes"** → Proceed to `on_yes` (or next step)

**User says "No"** → Go to `on_no` (or cancel)

**User says "Change the destination to LA"** →
1. Update `destination = "LA"`
2. Re-display confirmation with updated value
3. Wait for new confirmation

**User says "No wait, I meant December 20th not 15th"** →
1. Detect correction of `departure_date`
2. Update `departure_date = "2024-12-20"`
3. Re-display confirmation with updated value
4. Wait for new confirmation

This happens **automatically**. No DSL configuration needed.

### 8.6 DSL Override (When Needed)

For special cases, you can override the automatic behavior:

```yaml
- step: confirm_booking
  type: confirm
  message: "Confirm flight to {destination}?"
  on_correction: handle_correction_manually  # Override automatic behavior
  on_modification: handle_mod_manually
```

But in most cases, the default behavior is what you want.

### 8.7 Digression Handling

Digressions are questions that don't change the flow:

```
Bot: "What date would you like to depart?"
User: "What's the cheapest day to fly?"
→ Runtime detects digression (question)
→ Answers using knowledge base or LLM
→ Re-prompts: "What date would you like to depart?"
```

**Key principle**: Digressions **never modify the flow stack**. The conversation resumes exactly where it left off.

### 8.8 Interruption vs Digression

| Aspect | Interruption | Digression |
|--------|--------------|------------|
| **Intent** | Start new task | Just asking |
| **Flow Stack** | Push new flow | No change |
| **Example** | "Book me a hotel instead" | "Do you have hotels too?" |
| **After** | Complete new flow, then resume | Immediate return |

The NLU distinguishes between them based on context and phrasing:
- "Book me a hotel" → Interruption (imperative, action request)
- "Do you have hotels?" → Digression (question, information request)

### 8.9 State Variables for Patterns

The runtime sets these state variables that can be used in branches:

**Conversational Pattern Variables:**

| Variable | Type | Description |
|----------|------|-------------|
| `_last_message_type` | string | Type of last user message (see MessageType enum) |
| `_correction_slot` | string | Slot that was corrected (if any) |
| `_correction_value` | any | New value from correction |
| `_modification_slot` | string | Slot that was modified (if any) |
| `_modification_value` | any | New value from modification |
| `_digression_topic` | string | Topic of digression question |
| `_digression_answer` | string | Generated answer to digression |
| `_clarification_slot` | string | Slot being asked about in clarification |
| `_clarification_question` | string | User's clarification question |

**Flow State Variables:**

| Variable | Type | Description |
|----------|------|-------------|
| `_current_step` | string | ID of the currently executing step |
| `_current_flow` | string | Name of the current flow |
| `_flow_stack_depth` | integer | Number of flows in the stack |

**Error Variables (set when action fails):**

| Variable | Type | Description |
|----------|------|-------------|
| `_error` | boolean | `true` if last action failed |
| `_error_type` | string | Error category (e.g., `timeout`, `validation`, `connection`) |
| `_error_message` | string | Human-readable error description |
| `_error_code` | string | Machine-readable error code |
| `_error_details` | object | Additional error context (see below) |

**Note:** All error variables are set together atomically. When `_error = true`, all other error variables (`_error_type`, `_error_message`, `_error_code`, `_error_details`) are guaranteed to be set. When `_error = false` (or not set), the other error variables are cleared/undefined.

**`_error_details` Structure by Error Type:**

| Error Type | `_error_details` Fields |
|------------|-------------------------|
| `timeout` | `timeout_seconds`, `action_name` |
| `connection` | `url`, `status_code`, `retry_count` |
| `validation` | `field`, `expected`, `actual` |
| `rate_limited` | `retry_after_seconds`, `limit` |
| `payment_failed` | `reason`, `provider`, `transaction_id` |
| `not_found` | `resource_type`, `resource_id` |
| `permission` | `required_role`, `user_role` |

**Example:**
```yaml
# After a timeout error, _error_details contains:
# { "timeout_seconds": 30, "action_name": "search_flights" }

- step: handle_timeout
  type: branch
  when:
    - condition: "_error_type == 'timeout' and _error_details.timeout_seconds > 20"
      then: apologize_slow_service
    - else: quick_retry
```

**Validation Variables (set during collect):**

| Variable | Type | Description |
|----------|------|-------------|
| `_validation_attempts` | integer | Current attempt count for slot validation |
| `_validation_error` | string | Last validation error message |

**Example: Using error variables in branching:**

```yaml
- step: book_flight
  type: action
  call: book_flight_api
  on_error: handle_error

- step: handle_error
  type: branch
  when:
    - condition: "_error_type == 'payment_failed'"
      then: retry_payment
    - condition: "_error_type == 'sold_out'"
      then: suggest_alternatives
    - condition: "_error_type == 'timeout'"
      then: retry_booking
    - else: escalate_to_human
```

### 8.10 Interpolation Variables for Responses

When using `{variable}` interpolation in `responses` or `message` fields, these special variables are available:

**Slot-Related Variables:**

| Variable | Available In | Description |
|----------|--------------|-------------|
| `{slot_name}` | slot responses | Name of the current slot being collected/corrected |
| `{slot_description}` | slot responses | Description from slot definition |
| `{new_value}` | correction/modification | The new value being set |
| `{old_value}` | correction/modification | The previous value |
| `{validation_message}` | invalid responses | Error message from validator |

**Flow-Related Variables:**

| Variable | Available In | Description |
|----------|--------------|-------------|
| `{flow_name}` | flow responses | Name of current flow |
| `{flow_description}` | flow responses | Description from flow definition |
| `{available_capabilities}` | fallback | List of available flow descriptions |

**System Variables:**

| Variable | Available In | Description |
|----------|--------------|-------------|
| `{answer}` | digression_answered | LLM-generated answer to digression |
| `{conversation_summary}` | handoff_context | Auto-generated summary of conversation |

**Example Usage:**

```yaml
responses:
  correction_acknowledged:
    default: "Got it! Changed {slot_name} from {old_value} to {new_value}."

  clarification_slot:
    default: "I need {slot_description} to complete {flow_description}."

  fallback_out_of_scope:
    default: "I can't help with that, but I can: {available_capabilities}"
```

**Note:** All state variables (flow and session) are also available for interpolation using their standard names: `{origin}`, `{session.user_name}`, `{_error_message}`, etc.

**Undefined Variable Behavior:**

When a variable used in interpolation is not defined:
- **In messages**: Replaced with empty string `""` (silent failure)
- **In conditions**: Evaluates to `null` (falsy)
- **In expressions**: Evaluates to `null`, which may cause expression errors

```yaml
# If origin is undefined:
message: "Flying from {origin}"  # → "Flying from "

# In conditions:
condition: "origin != null"  # → false (can check explicitly)

# Recommended: Check before using
- step: check_data
  type: branch
  when:
    - condition: "origin == null"
      then: get_origin
    - else: continue
```

---

[Next: Control Flow & Errors →](07-control-error.md)
