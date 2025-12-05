# Control Flow & Error Handling

[← Back to Index](00-index.md) | [← Patterns](06-patterns.md)

---

## 9. Control Flow

### 9.1 Sequential Execution (Default)

Steps execute in order unless explicitly redirected.

```yaml
process:
  - step: a
    type: collect
    slot: origin
  - step: b        # Executes after 'a' completes
    type: collect
    slot: destination
  - step: c        # Executes after 'b' completes
    type: action
    call: search_flights
```

### 9.2 Explicit Jumps

Any step can define `jump_to` to alter flow:

```yaml
- step: search
  type: action
  call: search_flights
  jump_to: show_results  # Skip to specific step

- step: error
  type: say
  message: "Something went wrong."
  jump_to: end  # End the flow
```

**Special Targets:**
- `end` - End the current flow normally (outputs are passed to parent)
- `error` - End the flow with error state (see below)
- Step ID - Jump to that step

**`jump_to: error` Behavior:**

Using `jump_to: error` immediately ends the flow with error state:
- Does **NOT** trigger `on_error` handler (that's for action/step failures)
- Flow state is cleared, no outputs passed
- If called from sub-flow, parent flow's `on_error` **IS** triggered
- Use this for intentional error exits (e.g., validation failures you want to propagate)

```yaml
# on_error handles action failures
- step: book
  type: action
  call: book_flight
  on_error: handle_error  # Called if action fails

# jump_to: error is for intentional error exits
- step: check_fraud
  type: branch
  when:
    - condition: "fraud_score > 0.9"
      then: reject_as_fraud
    - else: continue

- step: reject_as_fraud
  type: say
  message: "We cannot process this request."
  jump_to: error  # Intentionally end with error state
```

**Loop Protection:**

The runtime detects and prevents infinite loops:

1. **Step execution limit**: Each step can execute at most `max_step_executions` times per flow (default: 100)
2. **Detection**: If a step is executed more than the limit, flow ends with `loop_detected` error
3. **No progress detection**: `max_turns_without_progress` (see settings) triggers `on_no_progress`

```yaml
settings:
  runtime:
    max_step_executions: 100  # Per step, per flow execution
```

When a loop is detected:
- `_error_type`: `loop_detected`
- `_error_message`: `"Step '{step_id}' executed too many times"`
- Flow ends with error state (triggers `on_error` if defined)

### 9.3 Branching

The `branch` step enables conditional routing:

```yaml
- step: check_count
  type: branch
  when:
    - condition: "result_count == 0"
      then: no_results
    - condition: "result_count == 1"
      then: single_result
    - else: multiple_results

- step: no_results
  type: say
  message: "No flights found. Try different dates?"
  jump_to: get_dates

- step: single_result
  type: say
  message: "I found exactly one flight."

- step: multiple_results
  type: say
  message: "I found {result_count} options."
```

### 9.4 Loops

Create loops using `jump_to`:

```yaml
- step: collect_input
  type: collect
  slot: user_input

- step: validate
  type: action
  call: validate_input

- step: check_valid
  type: branch
  when:
    - condition: "is_valid == true"
      then: process
    - else: retry

- step: retry
  type: say
  message: "That doesn't look right. Please try again."
  jump_to: collect_input  # Loop back

- step: process
  type: action
  call: process_input
```

---

## 10. Error Handling

### 10.1 Action Errors

Handle action failures with `on_error`:

```yaml
- step: book
  type: action
  call: book_flight
  on_error: handle_booking_error

- step: handle_booking_error
  type: branch
  when:
    - condition: "_error_type == 'payment_failed'"
      then: retry_payment
    - condition: "_error_type == 'flight_unavailable'"
      then: search_again
    - else: escalate
```

### 10.2 Flow-Level Error Handler

Define a global error handler for the flow:

```yaml
flows:
  book_flight:
    on_error: error_handler
    process:
      # ... steps ...

      - step: error_handler
        type: say
        message: "I encountered an error: {_error_message}"
        jump_to: end
```

**Error Variables in Flow Handler:**

When `flow.on_error` is triggered, all error variables are available:
- `_error` = `true`
- `_error_type` = error category
- `_error_message` = human-readable message
- `_error_code` = machine-readable code
- `_error_details` = additional context

These are set **before** jumping to the error handler, so you can branch on error type:

```yaml
- step: error_handler
  type: branch
  when:
    - condition: "_error_type == 'timeout'"
      then: handle_timeout
    - condition: "_error_type == 'validation'"
      then: handle_validation
    - else: handle_generic
```

---

[Next: Examples →](08-examples.md)
