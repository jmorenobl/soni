# DSL Guide - Procedural Flow Compiler

## Overview

Soni Framework v0.4.0 introduces a procedural DSL for defining complex dialogue flows with branching logic and explicit control flow. The compiler translates YAML procedural steps into LangGraph StateGraph for execution.

**Zero-Leakage Architecture (v0.4.0):** YAML configuration is completely semantic - no technical details (Python paths, regex patterns) in YAML. Actions and validators are registered via decorators in Python code.

## Step Types

### Collect Step

Collects a slot value from the user:

```yaml
- step: collect_destination
  type: collect
  slot: destination
```

**Fields:**
- `step`: Unique identifier for this step
- `type`: Must be `collect`
- `slot`: Name of the slot to collect (must be defined in `slots` section)

### Action Step

Calls an action handler:

```yaml
- step: verify_booking
  type: action
  call: check_booking_status
  map_outputs:
    status: api_status
    reason: rejection_reason
```

**Fields:**
- `step`: Unique identifier for this step
- `type`: Must be `action`
- `call`: Name of the action to call (must be defined in `actions` section)
- `map_outputs`: (Optional) Maps action outputs to flat state variables
  - Format: `{state_variable: action_output_field}`
  - Example: `{"flights": "api_flights", "price": "api_price"}`
  - Implements zero-leakage: actions can return technical structures that are mapped to simple state variables
  - If omitted, action outputs are used directly (backward compatible)

### Branch Step

Conditional routing based on a value:

```yaml
- step: decide_path
  type: branch
  input: api_status
  cases:
    available: continue
    unavailable: suggest_alternatives
    error: jump_to_retry
```

**Fields:**
- `step`: Unique identifier for this step
- `type`: Must be `branch`
- `input`: Variable name to check (from state)
- `cases`: Dictionary mapping values to targets
  - `continue`: Routes to next sequential step
  - `jump_to_<step_id>`: Routes to specific step
  - `<step_id>`: Routes to that step directly

**Note:** Branch steps cannot use `jump_to` field (they use `cases` instead).

## Control Flow

### Sequential Flow

Steps execute sequentially by default:

```yaml
flows:
  simple_flow:
    process:
      - step: step1
        type: collect
        slot: input1
      - step: step2
        type: action
        call: process
      - step: step3
        type: collect
        slot: input2
```

Each step automatically connects to the next step unless overridden by `jump_to` or branch routing.

### Explicit Jumps

Use `jump_to` to break sequentiality:

```yaml
- step: retry
  type: action
  call: retry_operation
  jump_to: collect_input  # Jump back to earlier step
```

**Jump targets:**
- `<step_id>`: Jump to a specific step by ID
- `__end__`: End the flow immediately

**Example with retry loop:**

```yaml
flows:
  retry_flow:
    process:
      - step: collect_input
        type: collect
        slot: user_input
      - step: validate
        type: action
        call: validate_input
      - step: check_validation
        type: branch
        input: validation_result
        cases:
          valid: process_input
          invalid: retry_collection
      - step: retry_collection
        type: action
        call: request_correction
        jump_to: collect_input  # Loop back
      - step: process_input
        type: action
        call: process_data
```

### Branches

Branches route conditionally based on input value:

```yaml
- step: check_status
  type: branch
  input: booking_status
  cases:
    confirmed: send_confirmation
    pending: request_payment
    cancelled: explain_cancellation
```

Each case can route to:
- `continue`: Next sequential step
- `jump_to_<step_id>`: Jump to specific step
- `<step_id>`: Jump to that step directly

**Example with complex branching:**

```yaml
flows:
  booking_flow:
    process:
      - step: collect_destination
        type: collect
        slot: destination
      - step: verify_route
        type: action
        call: check_route_availability
        map_outputs:
          status: route_status
      - step: decide_path
        type: branch
        input: route_status
        cases:
          available: collect_dates
          unavailable: suggest_alternatives
          error: jump_to_error_handler
      - step: collect_dates
        type: collect
        slot: departure_date
        jump_to: __end__
      - step: suggest_alternatives
        type: action
        call: find_alternatives
      - step: error_handler
        type: action
        call: handle_error
```

## Flow Triggers

### Trigger Configuration

Flows can define triggers that specify when they should be activated. The `trigger.intents` field contains natural language phrase examples that users might say to start the flow:

```yaml
flows:
  book_flight:
    description: "Book a flight from origin to destination"
    trigger:
      # Natural language phrase examples that trigger this flow
      # Used for NLU optimization - the LLM learns to map these phrases to the flow name
      intents:
        - "I want to book a flight"
        - "Book me a flight"
        - "I need to reserve a flight"
        - "Can I book a flight?"
    steps:
      - step: collect_origin
        type: collect
        slot: origin
```

**Key Points:**
- `trigger.intents` contains **natural language examples**, not intent names
- These examples are used for DSPy optimization training
- The NLU learns to map these phrases to the flow name (e.g., "book_flight")
- When `current_flow="none"`, available flows are passed to NLU to help it decide which flow to activate

**Creating Training Examples:**

You can use `trigger.intents` to create DSPy training examples for optimization:

```python
import dspy
from soni.core.config import SoniConfig

config = SoniConfig.from_yaml("soni.yaml")

# Create training examples from trigger.intents
examples = []
for flow_name, flow_config in config.flows.items():
    if flow_config.trigger and flow_config.trigger.intents:
        for intent_phrase in flow_config.trigger.intents:
            example = dspy.Example(
                user_message=intent_phrase,
                dialogue_history="",
                current_slots="{}",
                available_actions="[]",
                available_flows=f'["{flow_name}"]',
                current_flow="none",
                structured_command=flow_name,  # Flow name is the expected command
                extracted_slots="{}",
                confidence="0.95",
                reasoning=f"User wants to start {flow_name} flow",
            ).with_inputs(
                "user_message",
                "dialogue_history",
                "current_slots",
                "available_actions",
                "available_flows",
                "current_flow",
            )
            examples.append(example)
```

## Flow Structure

### Using `process` Section

For complex flows with branches and jumps, use the `process` section:

```yaml
flows:
  complex_flow:
    description: "Complex flow with branches and jumps"
    process:
      - step: collect_input
        type: collect
        slot: input
      - step: process
        type: action
        call: process_input
      - step: branch
        type: branch
        input: result
        cases:
          success: continue
          error: jump_to_retry
```

### Backward Compatibility

Simple linear flows can still use the `steps` array (backward compatible):

```yaml
flows:
  simple_flow:
    steps:
      - step: collect
        type: collect
        slot: input
      - step: process
        type: action
        call: process_input
```

## Slots and Validators

### Slot Definition

Slots define entities that need to be collected from users:

```yaml
slots:
  origin:
    type: string
    prompt: "Which city are you departing from?"
    required: true
    validator: city_name  # Semantic validator name
```

**Fields:**
- `type`: Data type (`string`, `integer`, `float`, `boolean`, `date`)
- `prompt`: Question to ask when slot is missing
- `required`: Whether slot must be collected (default: `false`)
- `validator`: (Optional) Semantic validator name (not regex pattern)

### Validators (Zero-Leakage Architecture)

Validators are registered using `@ValidatorRegistry.register()` decorator in Python code. YAML uses semantic names only:

```yaml
slots:
  origin:
    type: string
    prompt: "Which city?"
    validator: city_name  # Semantic name, not regex pattern
```

**Built-in Validators:**
- `city_name`: Validates city name format
- `future_date_only`: Validates date is in the future
- `iata_code`: Validates IATA airport code (3 uppercase letters)
- `booking_reference`: Validates booking reference format (6 alphanumeric)

**Custom Validators:**

Create custom validators by registering them in Python:

```python
from soni.validation.registry import ValidatorRegistry
import re

@ValidatorRegistry.register("my_custom_validator")
def validate_custom(value: str) -> bool:
    """Custom validation logic."""
    # Regex lives here, not in YAML
    return bool(re.match(r"^[A-Z]{2,3}\d{3,4}$", value))
```

**Important:**
- YAML uses semantic names only (e.g., `city_name`)
- Regex patterns live in Python code, not in YAML
- This implements zero-leakage architecture: YAML describes WHAT, Python implements HOW

## Compiler Validation

The compiler automatically validates:

### Cycle Detection

Detects infinite loops in the flow:

```yaml
# This will be detected as a cycle
- step: step1
  type: collect
  slot: input
  jump_to: step1  # Infinite loop!
```

### Unreachable Nodes

Identifies steps that can never be reached:

```yaml
# step2 is unreachable
- step: step1
  type: collect
  slot: input
  jump_to: step3
- step: step2  # Never reached
  type: action
  call: process
- step: step3
  type: action
  call: finish
```

### Valid Targets

Ensures jump targets and branch cases reference valid steps:

```yaml
# Error: step "invalid_step" doesn't exist
- step: step1
  type: collect
  slot: input
  jump_to: invalid_step  # Compilation error!
```

### Unique IDs

Ensures all step IDs are unique within a flow:

```yaml
# Error: duplicate step ID
- step: step1
  type: collect
  slot: input1
- step: step1  # Error: duplicate ID
  type: collect
  slot: input2
```

## Compilation Success Rate

Target: >95% compilation success rate for valid YAML configurations.

The compiler provides actionable error messages when compilation fails, indicating:
- What went wrong (specific error type)
- Where it occurred (step ID, field name)
- How to fix it (suggested correction)

## Error Messages

The compiler provides clear, actionable error messages:

```python
# Example error message
ValueError: Step 'decide_path' of type 'branch' must specify 'cases'
```

```python
# Example error message
ValueError: Step 'retry' has jump_to target 'invalid_step' that doesn't exist in flow
```

## Migration from v0.2.x

### Breaking Changes

- **Procedural DSL**: New `process` section with `steps` for complex flows
- **Branch syntax**: New `branch` step type for conditional logic
- **Jump syntax**: New `jump_to` field for explicit control flow

### Upgrade Guide

**v0.2.x (still supported for simple flows):**

```yaml
flows:
  simple_flow:
    steps:
      - step: collect
        type: collect
        slot: input
```

**v0.3.0 (new procedural DSL):**

```yaml
flows:
  complex_flow:
    process:
      - step: collect
        type: collect
        slot: input
      - step: branch
        type: branch
        input: value
        cases:
          ok: continue
          error: jump_to_retry
```

**v0.4.0 (Zero-Leakage Architecture):**

```yaml
# Actions: No handler paths, use ActionRegistry
actions:
  search_flights:
    description: "Search for flights"
    # No handler: field - registered via @ActionRegistry.register()
    inputs: [origin, destination]
    outputs: [api_flights, api_price]

# Slots: Semantic validator names, not regex
slots:
  origin:
    type: string
    prompt: "Which city?"
    validator: city_name  # Semantic name, not regex pattern

# Steps: Output mapping for zero-leakage
flows:
  book_flight:
    process:
      - step: search
        type: action
        call: search_flights
        map_outputs:
          flights: api_flights  # Map technical field to flat variable
          price: api_price
```

Simple linear flows continue to work with the `steps` array, but new procedural features require the `process` section.

## Examples

See `examples/advanced/` for complete working examples:
- `retry_flow.yaml` - Retry loop using jumps
- `branching_flow.yaml` - Complex branching logic

## Best Practices

1. **Use descriptive step IDs**: `collect_destination` is better than `step1`
2. **Document complex flows**: Add `description` field to flows
3. **Validate early**: Use compiler validation before deployment
4. **Test branches**: Ensure all branch cases are tested
5. **Avoid deep nesting**: Keep flows readable and maintainable

## Reference

- [Architecture Guide](architecture.md) - Framework architecture
- [Quickstart Guide](quickstart.md) - Getting started
- [ADR-001: Framework Architecture](../adr/ADR-001-Soni-Framework-Architecture.md) - Detailed architecture decisions
