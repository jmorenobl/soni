# Step Types

[← Back to Index](00-index.md) | [← Flows](04-flows.md)

---

## 7. Step Types

The DSL provides a minimal but powerful set of step types.

**Universal Fields (available on all step types):**

| Field | Required | Description |
|-------|----------|-------------|
| `step` | Yes | Unique identifier for this step within the flow |
| `type` | Yes | Step type (`collect`, `action`, `branch`, etc.) |
| `when` | No | Condition to execute this step (skip if false). Not available on `branch` which uses `when` differently. |
| `jump_to` | No | Override next step (see Control Flow) |

---

### 7.1 `collect` - Gather Information

Collects a slot value from the user.

```yaml
- step: get_destination
  type: collect
  slot: destination
```

**Behavior:**
1. Check `when` condition → Skip step if false
2. If slot is already filled in state → Skip (unless `force: true`)
3. If slot is empty → Ask `prompt` from slot definition and wait for user
4. User response goes through NLU first (may be slot value, question, or intent change)
5. If value provided → Validate using slot's `validator`
6. If validation fails → Show `invalid_message`, retry up to `max_attempts`
7. If max attempts exceeded → Go to `on_invalid` (see below)

**Default `on_invalid` Behavior:**

If `on_invalid` is not specified and max validation attempts are reached:
1. Show `slot_invalid_max_attempts` response
2. Transfer to human agent (handoff to default queue)

To customize:
```yaml
- step: get_email
  type: collect
  slot: email
  max_attempts: 3
  on_invalid: custom_handler  # Override default handoff
```

**Fields:**
| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `slot` | Yes | - | Name of the slot to collect |
| `force` | No | `false` | Ask even if slot has value (clears current value first) |
| `prompt` | No | From slot | Override the default prompt |
| `when` | No | - | Condition to execute this step |
| `max_attempts` | No | `settings.collection.max_validation_attempts` | Max validation retries |
| `timeout` | No | `settings.collection.validation_timeout` | Seconds to wait for response |
| `on_invalid` | No | handoff | Step after max attempts (default: handoff to human) |
| `on_timeout` | No | re-prompt | Step on timeout (default: show timeout message, re-prompt) |
| `on_cancel` | No | cancel_flow | Step if user cancels (default: pop flow stack) |
| `from` | No | - | State variable containing list to select from |
| `display` | No | `{item}` | Template for displaying each list option |
| `page_size` | No | 10 | Number of options per page |
| `show_more_prompt` | No | (see below) | Prompt for pagination |
| `ui` | No | - | Rich UI component (buttons, carousel, etc.) |

**`force` and `default` Interaction:**

When a slot has both a `default` value and `force: true` is used:
- `force: true` **clears** the current value before prompting
- The `default` value is **NOT** used when `force: true`
- The user must provide a new value

```yaml
slots:
  passenger_count:
    type: integer
    default: 1
    prompt: "How many passengers?"

# force: true clears current value and asks user (ignores default)
- step: change_passengers
  type: collect
  slot: passenger_count
  force: true  # User must provide new value, default is ignored
```

**Conditional Collection:**

Only ask for visa if user is not a local citizen:

```yaml
- step: get_visa
  type: collect
  slot: visa_number
  when: "nationality != 'local'"
```

**Validation Handling:**

```yaml
- step: get_email
  type: collect
  slot: email
  max_attempts: 3
  on_invalid: offer_help

- step: offer_help
  type: say
  message: "Having trouble? You can also call us at 1-800-XXX-XXXX."
  jump_to: end
```

**Timeout Handling:**

```yaml
- step: get_confirmation
  type: collect
  slot: user_confirmation
  timeout: 120  # 2 minutes
  on_timeout: remind_user

- step: remind_user
  type: say
  message: "Are you still there? Take your time."
  jump_to: get_confirmation
```

**Dynamic Prompt with Variables:**

```yaml
- step: get_destination
  type: collect
  slot: destination
  prompt: "Where would you like to fly from {origin}, {session.user_name}?"
```

**Collecting from a List:**

```yaml
- step: select_flight
  type: collect
  slot: selected_flight
  from: flights
  display: "{flight_number} | {departure_time} → {arrival_time} | ${price}"
  page_size: 5  # Show 5 options at a time
  show_more_prompt: "Would you like to see more options?"
```

| Field | Description | Default |
|-------|-------------|---------|
| `from` | State variable containing the list | - |
| `display` | Template for each option | `{item}` (string representation) |
| `page_size` | Options per page | 10 |
| `show_more_prompt` | Prompt for pagination | "Would you like to see more?" |

**Selection Behavior:**
- User can select by **number** ("option 2") or by **matching text** ("the 10am flight")
- The **entire item** from the list is stored in the slot (not just an ID)
- If items are objects, the full object is stored

```yaml
# If flights = [{id: "F1", price: 100}, {id: "F2", price: 200}]
# And user selects option 1
# Then selected_flight = {id: "F1", price: 100}  (the full object)
```

---

### 7.2 `action` - Execute Business Logic

Calls a registered Python function.

```yaml
- step: search
  type: action
  call: search_flights
```

**Behavior:**
1. Inputs are automatically injected from state based on action contract
2. Action executes (async)
3. Outputs are merged into **flow state**

**Fields:**
| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `call` | Yes | - | Semantic name of the action |
| `map_outputs` | No | - | Rename outputs when storing |
| `on_error` | No | flow's `on_error` | Step on failure (default: use flow's handler, or end with error) |
| `timeout` | No | - | Max seconds per attempt |
| `retry` | No | - | Retry policy (see below) |
| `when` | No | - | Condition to execute this step |

**Error Propagation:**
1. If step has `on_error` → Jump to that step
2. Else if flow has `on_error` → Jump to flow's error handler
3. Else → Flow ends with error state (exits to parent flow or idle)

**Output Behavior on Error:**
- If action **succeeds**: Outputs are merged into flow state
- If action **fails**: Outputs are **NOT** modified (previous values preserved)
- Error variables (`_error`, `_error_type`, etc.) are always set on failure

**Output Mapping:**

Map action outputs to different state variable names. Format: `action_output: state_variable`

```yaml
- step: search
  type: action
  call: search_flights
  map_outputs:
    flights: available_flights      # Action returns 'flights' → stored as 'available_flights'
    total_results: result_count     # Action returns 'total_results' → stored as 'result_count'
```

**Timeout and Retry Policy:**

Timeout and retry are orthogonal and can be combined:

```yaml
- step: book
  type: action
  call: book_flight
  timeout: 30          # Max seconds per attempt
  retry:
    max_attempts: 3    # Total attempts (including first)
    delay: 2           # Seconds between retries
    backoff: exponential  # Optional: linear, exponential, or fixed (default)
    retry_on:          # Optional: only retry on specific errors
      - timeout
      - connection_error
      - rate_limited
  on_error: booking_failed  # Called after all retries exhausted
```

| Field | Description | Default |
|-------|-------------|---------|
| `timeout` | Max seconds per attempt | No timeout |
| `retry.max_attempts` | Total attempts | 1 (no retry) |
| `retry.delay` | Seconds between retries | 1 |
| `retry.backoff` | `fixed`, `linear`, `exponential` | `fixed` |
| `retry.retry_on` | Error types to retry | All errors |

**Backoff strategies:**
- `fixed`: Always wait `delay` seconds
- `linear`: Wait `delay * attempt` seconds (2s, 4s, 6s...)
- `exponential`: Wait `delay * 2^attempt` seconds (2s, 4s, 8s...)

**Example: API call with timeout + retry:**

```yaml
- step: search
  type: action
  call: search_flights
  timeout: 10
  retry:
    max_attempts: 3
    delay: 1
    backoff: exponential
    retry_on: [timeout, connection_error]
  on_error: search_failed
```

This will:
1. Try the action (max 10s)
2. If timeout/connection error → wait 1s → retry (max 10s)
3. If fails again → wait 2s → retry (max 10s)
4. If fails again → jump to `search_failed`

---

### 7.3 `branch` - Conditional Logic

Routes execution based on state values or expressions.

```yaml
- step: check_results
  type: branch
  when:
    - condition: "result_count == 0"
      then: no_flights
    - else: show_flights
```

**Fields:**
| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `when` | Yes | - | List of condition/then pairs with optional `else` |

**Note:** The `when` field in `branch` has a **different structure** than in other step types. In other steps, `when` is a simple condition string. In `branch`, `when` is a list of routing rules.

**Special target values:**
- `continue` - Go to next sequential step
- `end` - End the current flow

#### Simple Value Matching

```yaml
- step: check_status
  type: branch
  when:
    - condition: "booking_status == 'confirmed'"
      then: show_confirmation
    - condition: "booking_status == 'pending'"
      then: show_pending
    - condition: "booking_status == 'cancelled'"
      then: show_cancellation
    - else: show_error
```

#### Numeric Comparisons

```yaml
- step: check_age
  type: branch
  when:
    - condition: "user_age >= 18"
      then: adult_path
    - condition: "user_age >= 13"
      then: teen_path
    - else: minor_path
```

**Supported operators:**
| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equal | `status == "active"` |
| `!=` | Not equal | `status != "cancelled"` |
| `>` | Greater than | `age > 18` |
| `>=` | Greater or equal | `age >= 18` |
| `<` | Less than | `count < 10` |
| `<=` | Less or equal | `price <= 500` |
| `in` | Contains | `country in ["US", "CA", "MX"]` |
| `not in` | Not contains | `status not in ["banned", "suspended"]` |
| `and` | Logical AND | `age >= 18 and age < 65` |
| `or` | Logical OR | `status == "active" or status == "pending"` |
| `not` | Logical NOT | `not is_blocked` |

#### Inline Boolean Expressions

Use `and`, `or`, and `not` directly in condition strings:

```yaml
- step: check_working_age
  type: branch
  when:
    - condition: "user_age >= 18 and user_age < 65"
      then: eligible_worker
    - condition: "user_age >= 65"
      then: retirement_info
    - else: too_young

- step: check_access
  type: branch
  when:
    - condition: "is_admin or (is_member and account_verified)"
      then: grant_access
    - condition: "is_banned or is_suspended"
      then: deny_access
    - else: request_verification
```

**Operator precedence** (highest to lowest):
1. `not`
2. Comparison operators (`==`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `not in`)
3. `and`
4. `or`

Use parentheses `()` to override precedence when needed.

#### Structured Boolean Logic (Alternative)

For complex conditions, you can also use structured `all` (AND) or `any` (OR):

```yaml
- step: check_eligibility
  type: branch
  when:
    - condition:
        all:
          - "user_age >= 18"
          - "account_verified == true"
          - "country in ['US', 'CA']"
      then: proceed_booking
    - condition:
        any:
          - "user_age < 18"
          - "account_verified == false"
      then: show_requirements
    - else: contact_support
```

Both syntaxes are equivalent. Use inline `and`/`or` for simple expressions and structured `all`/`any` for complex multi-line conditions.

**Note on `all`/`any` vs Jinja2:**

The DSL provides `all`/`any` as a YAML-native structure for readability. Under the hood, the runtime converts them to equivalent expressions:
- `all: [a, b, c]` → `a and b and c`
- `any: [a, b, c]` → `a or b or c`

You can also use Jinja2's built-in functions if preferred:
```yaml
# These are equivalent:
condition:
  all:
    - "item.price > 0"
    - "item.in_stock == true"

condition: "item.price > 0 and item.in_stock == true"
```

Choose whichever style is more readable for your use case.

#### Age-Based Routing Example

```yaml
slots:
  user_age:
    type: integer
    description: "User's age in years"
    prompt: "How old are you?"

flows:
  age_verification:
    process:
      - step: ask_age
        type: collect
        slot: user_age

      - step: route_by_age
        type: branch
        when:
          - condition: "user_age >= 21"
            then: full_access
          - condition: "user_age >= 18"
            then: limited_access
          - condition: "user_age >= 13"
            then: teen_access
          - else: parental_consent

      - step: full_access
        type: say
        message: "Welcome! You have full access to all features."
        jump_to: end

      - step: limited_access
        type: say
        message: "Welcome! Some features require you to be 21+."
        jump_to: end

      - step: teen_access
        type: say
        message: "Welcome! Some features are restricted for users under 18."
        jump_to: end

      - step: parental_consent
        type: say
        message: "You need parental consent to use this service."
        jump_to: end
```

---

### 7.4 `say` - Send Message

Sends a message to the user without waiting for input.

```yaml
- step: welcome
  type: say
  message: "Welcome! I can help you book flights, check status, or modify reservations."
```

**Fields:**
| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `message` | Yes* | - | Text to send (supports `{variable}` interpolation) |
| `response` | Yes* | - | Reference to a response template (alternative to `message`) |
| `ui` | No | - | Rich UI component (card, image, etc.) |
| `when` | No | - | Condition to execute this step |

*Either `message` or `response` is required, not both.

**Using Response Templates:**

```yaml
- step: acknowledge_correction
  type: say
  response: correction_acknowledged  # Uses template from responses section
```

**With Rich UI:**

```yaml
- step: show_booking_details
  type: say
  message: "Here's your booking:"
  ui:
    type: card
    title: "Flight {flight_number}"
    subtitle: "{origin} → {destination}"
```

**Dynamic Message:**

```yaml
- step: show_results
  type: say
  message: "I found {result_count} flights from {origin} to {destination}."
```

---

### 7.5 `confirm` - Request Confirmation

Asks the user to confirm before proceeding. This is a **blocking step** that waits for user response.

```yaml
- step: confirm_booking
  type: confirm
  message: |
    Please confirm your booking:
    - From: {origin}
    - To: {destination}
    - Date: {departure_date}
    - Flight: {selected_flight.flight_number}
    - Total: {selected_flight.price}
  on_yes: execute_booking
  on_no: modify_selection
```

**Fields:**
| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `message` | Yes | - | Confirmation prompt with slot interpolation |
| `on_yes` | No | next step | Step if user confirms (or `end` if last step) |
| `on_no` | No | cancel_flow | Step if user denies |
| `on_change` | No | auto | General handler for any change request |
| `on_correction` | No | auto | Handler for corrections ("I said X but meant Y") |
| `on_modification` | No | auto | Handler for modifications ("Change X to Y") |
| `on_cancel` | No | cancel_flow | Step if user cancels ("forget it") |
| `timeout` | No | `settings.collection.validation_timeout` | Seconds to wait for response |
| `on_timeout` | No | re-prompt | Step on timeout (default: show `error_timeout`, wait again) |
| `ui` | No | - | Rich UI component (quick_replies, buttons) |
| `when` | No | - | Condition to execute this step |

**Handler Priority:** `on_correction`/`on_modification` > `on_change` > auto-handle

**Default Behaviors:**

| Handler | Default Behavior |
|---------|------------------|
| `on_yes` | Go to next step in flow |
| `on_no` | Cancel current flow, return to previous flow (or idle if none) |
| `on_change` | Auto-detect slot, update value, re-display confirmation |
| `on_correction` | Same as `on_change` |
| `on_modification` | Same as `on_change` |
| `on_timeout` | Show `error_timeout` response, wait again |

**What "Cancel Flow" Means:**
- Current flow is **popped** from the flow stack
- If there's a parent flow (via `call_flow`), execution **resumes** there
- If no parent flow, conversation returns to **idle state** (waiting for new trigger)
- Flow state is **cleared** (slots collected in this flow are lost)
- Session state is **preserved**

**Behavior:**
1. Check `when` condition → Skip if false
2. Display confirmation message
3. Wait for user response
4. NLU classifies: confirm, deny, correction, modification
5. Route to handler (auto-handle updates slot and re-confirms if not overridden)

**With Rich UI:**

```yaml
- step: confirm_booking
  type: confirm
  message: "Confirm your flight to {destination}?"
  ui:
    type: quick_replies
    options:
      - label: "✓ Yes, book it"
        value: "yes"
      - label: "✗ No, cancel"
        value: "no"
      - label: "✎ Change something"
        value: "change"
  on_yes: execute_booking
  on_no: cancel_flow
```

---

### 7.6 `generate` - LLM Response

Generates a dynamic response using the LLM.

```yaml
- step: explain_options
  type: generate
  instruction: "Explain the flight options to the user in a friendly way"
  context:
    - flights
    - user_preferences
```

**Fields:**
| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `instruction` | Yes | - | What to generate |
| `context` | No | - | State variables to include as context |
| `store_as` | No | - | Save generated text to this slot |
| `on_error` | No | flow's `on_error` | Step if LLM fails (timeout, rate limit, etc.) |
| `when` | No | - | Condition to execute this step |

**Error Handling:** If the LLM call fails, error propagation follows the same rules as `action`.

---

### 7.7 `call_flow` - Invoke Sub-flow

Invokes another flow and waits for it to complete.

```yaml
- step: get_payment
  type: call_flow
  flow: collect_payment
  inputs:
    amount: selected_flight.price      # Pass 'selected_flight.price' as 'amount'
    description: "Flight booking"      # Pass literal value as 'description'
  outputs:
    payment_status: payment_confirmed  # Sub-flow returns 'payment_status' → stored as 'payment_confirmed'
```

**Behavior:**
1. Push current flow to stack (paused)
2. Start target flow with given inputs
3. When target completes, resume current flow
4. Map target outputs to current flow state

**Fields:**
| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `flow` | Yes | - | Name of flow to invoke |
| `inputs` | No | - | Map: `target_input: source_value` |
| `outputs` | No | - | Map: `subflow_output: local_variable` |
| `on_error` | No | flow's `on_error` | Step if sub-flow fails (same propagation as `action`) |
| `when` | No | - | Condition to execute this step |

**Note:** Output mapping follows the same convention as `action`: `source: destination`

**Error Propagation:** Same as `action` - if sub-flow ends with error:
1. If step has `on_error` → Jump to that step
2. Else if parent flow has `on_error` → Jump to flow's error handler
3. Else → Parent flow ends with error state

---

### 7.8 `set` - Set Variables

Sets state variables without user interaction. Useful for initialization, calculations, or flags.

```yaml
- step: init_defaults
  type: set
  values:
    passenger_count: 1
    currency: "USD"
    is_round_trip: false
```

**Fields:**
| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `values` | Yes | - | Map of variable names → values |
| `when` | No | - | Condition to execute this step (skip if false) |

**Dynamic Values with Jinja2:**

The DSL uses **Jinja2** for templating. Two syntaxes are available:

| Syntax | Purpose | Result Type |
|--------|---------|-------------|
| `{variable}` | String interpolation | Always string |
| `{{ expression }}` | Expression evaluation | Preserves type |

```yaml
- step: calculate_total
  type: set
  values:
    # Literal values
    currency: "USD"
    is_premium: false

    # String interpolation (always produces string)
    summary: "Flight from {origin} to {destination}"

    # Expression evaluation (preserves type)
    total_price: "{{ selected_flight.price * passenger_count }}"
    discounted_price: "{{ total_price * (1 - discount_rate) }}"
    is_expensive: "{{ total_price > 500 }}"

    # Built-in function
    booking_date: "{{ today() }}"
```

**Expression Capabilities:**
- Arithmetic: `+`, `-`, `*`, `/`, `//` (floor div), `%` (modulo), `**` (power)
- Comparison: `==`, `!=`, `>`, `>=`, `<`, `<=`
- Logical: `and`, `or`, `not`
- Access nested: `{{ selected_flight.price }}`
- Filters: `{{ name | upper }}`, `{{ items | length }}`
- Conditionals: `{{ 'yes' if confirmed else 'no' }}`

**When to Use Each:**

| Context | Syntax | Reason |
|---------|--------|--------|
| Messages (`say`, `confirm`) | `{var}` | Always need strings for display |
| Set values (literals) | `value: 1` | Direct YAML value |
| Set values (expressions) | `"{{ expr }}"` | Need `{{ }}` to distinguish from literal strings |
| Conditions (`when`, `branch`) | `"expr"` | Always expressions, no ambiguity |
| Response templates | `{var}` | String interpolation only |
| UI templates | `{var}` | String interpolation only |

**Why Conditions Don't Need `{{ }}`:**

In `set` values, the runtime needs to distinguish between:
- Literal string: `name: "John"`
- Expression: `total: "{{ price * 2 }}"`

In conditions, the value is **always** an expression - there's no ambiguity:
```yaml
# Conditions are always expressions - no {{ }} needed
condition: "price > 100"          # ✓ Evaluated as expression
condition: "{{ price > 100 }}"    # ✗ Redundant, don't use
```

**Conditional Execution (skip entire step):**

```yaml
- step: set_premium_benefits
  type: set
  when: "session.membership_level == 'premium'"
  values:
    priority_boarding: true
    lounge_access: true
```

**Conditional Values (use branch for complex logic):**

For if/else logic within values, use a `branch` step followed by `set`:

```yaml
- step: check_discount_eligibility
  type: branch
  when:
    - condition: "user_age < 18 or user_age >= 65"
      then: apply_discount
    - else: no_discount

- step: apply_discount
  type: set
  values:
    discount_rate: 0.15
  jump_to: continue_flow

- step: no_discount
  type: set
  values:
    discount_rate: 0.0

- step: continue_flow
  # ...
```

**Built-in Functions:**

| Function | Description | Example |
|----------|-------------|---------|
| `today()` | Current date | `booking_date: "{{ today() }}"` |
| `now()` | Current datetime | `timestamp: "{{ now() }}"` |
| `uuid()` | Generate UUID | `request_id: "{{ uuid() }}"` |

---

### 7.9 `handoff` - Transfer to Human

Transfers the conversation to a human agent.

```yaml
- step: escalate
  type: handoff
  queue: customer_support
  context:
    - booking_reference
    - error_details
  message: "I'm connecting you with a support agent who can help with this issue."
```

**Fields:**
| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `queue` | No | `settings.handoff.default_queue` | Target queue/department |
| `context` | No | - | State variables to pass to agent |
| `message` | No | `handoff_initiated` | Message shown to user during handoff |
| `on_error` | No | flow's `on_error` | Step if handoff fails (queue unavailable, etc.) |
| `when` | No | - | Condition to execute this step |

**Error Handling:** If the handoff system is unavailable or the queue doesn't exist, error propagation follows the same rules as `action`. Common error types: `queue_not_found`, `handoff_unavailable`, `timeout`.

---

[Next: Patterns →](06-patterns.md)
