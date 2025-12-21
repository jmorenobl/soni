"""SetNodeFactory - generates declarative slot assignment nodes.

## How Set Node Works

The set node enables **declarative slot initialization** directly in YAML flows,
eliminating the need for Python action handlers for simple value assignments.
This is particularly useful for session initialization, default values, and
computed derived values.

## Primary Use Case: Session Initialization

When deploying Soni as a service, you often need to initialize user context
from authentication data or external systems. The set node makes this trivial:

```yaml
flows:
  initialize_session:
    steps:
      - step: set_user_context
        type: set
        slots:
          user_id: "{{auth.user_id}}"
          user_name: "{{auth.name}}"
          account_type: "{{auth.account_type}}"
          session_active: true
          login_count: 0
```

## YAML Structure

```yaml
- step: my_set_step
  type: set
  slots:                      # Required: dict of slot_name: value
    literal_string: "hello"   # String literal
    literal_number: 42        # Number literal
    literal_bool: true        # Boolean literal
    from_slot: "{{other_slot}}"  # Template substitution

  condition: "user_id"        # Optional: only execute if condition true
```

## Value Types Supported

### 1. Literal Values
Values are taken directly from YAML with type preservation:

```yaml
slots:
  name: "Alice"              # str
  age: 30                    # int
  balance: 1234.56           # float
  active: true               # bool
```

### 2. Template Substitution
Use `{{slot_name}}` syntax to reference existing slot values:

```yaml
slots:
  # Copy from another slot
  destination_account: "{{source_account}}"

  # Embed in string
  greeting: "Hello, {{user_name}}!"

  # From nested context (if available)
  email: "{{auth.email}}"
```

**Template Resolution**:
- Templates are resolved using current slot values
- Format: `{{slot_name}}` → converted to Python `.format(slot_name=value)`
- Missing slots: Falls back to literal value with warning

## Conditional Execution

Execute the set step only if a condition is met:

```yaml
- step: set_premium_features
  type: set
  condition: "account_type == 'premium'"
  slots:
    max_transfers: 100
    fee_waived: true
```

Uses the same condition syntax as `branch` and `while` nodes.

## Common Use Cases

### 1. Session Initialization from Auth

```yaml
- step: init_user_session
  type: set
  slots:
    user_id: "{{system.user_id}}"
    email: "{{system.email}}"
    authenticated: true
    session_start: "{{system.timestamp}}"
```

### 2. Default Values Before Collection

```yaml
- step: set_defaults
  type: set
  slots:
    currency: "EUR"
    fee: 0
    express_delivery: false

- step: ask_amount
  type: collect
  slot: amount
```

### 3. Internal Flags for Flow Control

```yaml
- step: mark_retry
  type: set
  slots:
    __retry_count: "{{retry_count + 1}}"
    __last_attempt: "{{system.now}}"
```

### 4. Derived Values

```yaml
- step: calculate_totals
  type: set
  slots:
    # Note: Currently only supports template substitution
    # Full expression evaluation is a future enhancement
    display_total: "{{amount}}"
```

## Integration Points

- **FlowManager**: Uses `set_slot()` to update active flow context
- **Expression System**: Uses existing template substitution
- **Conditional Execution**: Uses `evaluate_condition()` from `core.expression`

## Limitations

**Current**: Only template substitution (`{{slot}}`)
**Future**: Arithmetic expressions (`{{amount * 1.1}}`, `{{count + 1}}`)

## Implementation Details

- **Async**: Follows async pattern for consistency with other nodes
- **Type Preservation**: YAML types (str, int, bool, float) are maintained
- **Multiple Slots**: Can set many slots in a single step
- **Order**: Slots are set sequentially in definition order
- **Atomicity**: If template fails, falls back to literal value (no partial state)
"""

import logging
from typing import Any

from langgraph.runtime import Runtime
from soni.compiler.nodes.base import NodeFunction
from soni.compiler.nodes.utils import require_field, validate_non_empty
from soni.core.expression import evaluate_condition
from soni.core.types import DialogueState, RuntimeContext
from soni.flow.manager import merge_delta

from soni.config.steps import SetStepConfig, StepConfig

logger = logging.getLogger(__name__)


class SetNodeFactory:
    """Factory for set step nodes.

    Creates nodes that declaratively assign values to multiple slots.
    """

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node that sets multiple slot values.

        Args:
            step: Step configuration with 'slots' dict
            all_steps: Not used for set nodes
            step_index: Not used for set nodes

        Returns:
            Async node function that sets slots

        Raises:
            ValidationError: If slots field is missing
        """
        if not isinstance(step, SetStepConfig):
            raise ValueError(f"SetNodeFactory received wrong step type: {type(step).__name__}")

        require_field(step, "slots")
        validate_non_empty(step, "slots", step.slots)

        # Pydantic validates slots is a dict
        slots_to_set = step.slots
        condition = step.condition

        async def set_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Execute the set step.

            Sets each slot in the slots dict, with optional template substitution
            and conditional execution.
            """
            context = runtime.context
            fm = context.flow_manager

            # IDEMPOTENCY CHECK
            step_id = f"step_{step_index}" if step_index is not None else step.step
            flow_id = fm.get_active_flow_id(state)

            if flow_id:
                executed = state.get("_executed_steps", {}).get(flow_id, set())
                if step_id in executed:
                    return {}

            # Check condition if specified
            if condition:
                current_slots = fm.get_all_slots(state)
                should_execute = evaluate_condition(condition, current_slots)
                if not should_execute:
                    logger.debug(f"Set step {step.step}: condition '{condition}' false, skipping")

                    # Mark as executed even if condition failed?
                    # Yes, because we evaluated it.
                    updates = {"flow_slots": state["flow_slots"]}
                    if flow_id:
                        updates["_executed_steps"] = {flow_id: {step_id}}
                    return updates

            # Get current slots for template substitution
            current_slots = fm.get_all_slots(state)

            # Build updates dict
            updates: dict[str, Any] = {}

            # Set each slot
            for slot_name, slot_value in slots_to_set.items():
                # Handle template substitution for strings
                final_value = slot_value

                if isinstance(slot_value, str) and "{{" in slot_value:
                    try:
                        # Convert {{slot}} to {slot} for Python format()
                        template = slot_value.replace("{{", "{").replace("}}", "}")
                        final_value = template.format(**current_slots)
                    except (KeyError, ValueError) as e:
                        logger.warning(
                            f"Template substitution failed for slot '{slot_name}' "
                            f"with template '{slot_value}': {e}. Using literal value."
                        )
                        # Use original value as fallback
                        final_value = slot_value

                # Set the slot and get delta
                delta = fm.set_slot(state, slot_name, final_value)
                merge_delta(updates, delta)
                # Apply to state for subsequent iterations
                if delta and delta.flow_slots is not None:
                    state["flow_slots"] = delta.flow_slots
                logger.debug(f"Set slot '{slot_name}' = {final_value}")

            # Ensure flow_slots in updates
            if "flow_slots" not in updates:
                updates["flow_slots"] = state.get("flow_slots")

            # MARK AS EXECUTED
            if flow_id:
                updates["_executed_steps"] = {flow_id: {step_id}}

            return updates

        set_node.__name__ = f"set_{step.step}"
        return set_node
