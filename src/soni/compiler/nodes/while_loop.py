"""WhileNodeFactory - generates loop guard nodes with proper loop semantics.

## How While Loops Work in Soni

A while loop in Soni creates a guard node that evaluates a condition and routes
the execution flow accordingly:

1. **Condition Evaluation**: At the START of each iteration, the while node evaluates
   the condition using slot values.
2. **Loop Entry**: If TRUE → jumps to first step in `do:` block
3. **Loop Body**: Executes all steps in the `do:` block sequentially
4. **Loop Back**: After last step in `do:`, automatically returns to while guard
5. **Loop Exit**: If FALSE → jumps to exit_to target or next step after while

## YAML Structure

```yaml
- step: my_loop
  type: while
  condition: "counter < 10"  # Evaluated using slot values
  do:
    - step_one
    - step_two
    - step_three
  exit_to: optional_explicit_exit  # Optional, auto-calculated if not provided
```

## ✅ Good Use Cases (No User Input Inside Loop)

While loops work best for **automatic iterations** without pausing for user input:

- **Batch Processing**: Process a list of items automatically
  ```yaml
  condition: "item_index < total_items"
  do: [fetch_item, process_item, increment_index]
  ```

- **Retry Logic**: Retry an operation until success or max attempts
  ```yaml
  condition: "attempts < 3 AND status != 'success'"
  do: [try_operation, check_status, increment_attempts]
  ```

- **Auto-review**: Show multiple notifications/alerts sequentially
  ```yaml
  condition: "alert_index < total_alerts"
  do: [get_alert, display_alert, mark_reviewed, next_alert]
  ```

## ❌ Problematic Use Cases (User Input Inside Loop)

**AVOID** using `collect` or any step that pauses for user input inside the `do:` block:

```yaml
# ❌ BAD - collect inside loop causes resumption issues
condition: "has_more_pages == 'yes'"
do:
  - fetch_page
  - show_page
  - ask_user_continue  # collect - PROBLEMATIC!
  - handle_response
```

**Why it fails**: When `collect` pauses execution (`waiting_input`), the loop state
is not properly preserved across turns, causing the flow to restart incorrectly.

**Solution**: Use `branch + jump_to` for interactive loops:

```yaml
# ✅ GOOD - branch + jump_to for user interaction
- step: show_page
  ...
- step: ask_continue
  type: collect
  slot: continue
- step: decide
  type: branch
  slot: continue
  cases:
    "yes": show_page  # Creates loop via jump_to
    "no": end_flow
```

## Exit Mechanisms

1. **Natural Exit**: Condition becomes FALSE
2. **Explicit Exit**: Use `jump_to: __exit_loop__` from a branch inside the loop
   (Only works if NO collect is involved before the branch)

## Implementation Details

- **Auto-calculated exit_to**: If not specified, the compiler finds the first step
  after the while that is NOT in the `do:` block
- **Loop back edge**: Automatically created from last step in `do:` to while guard
- **Special target**: `__exit_loop__` can be used as branch target to exit early
"""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.expression import evaluate_condition
from soni.core.types import DialogueState, get_runtime_context

# Special constant for exiting a while loop from within
EXIT_LOOP_TARGET = "__exit_loop__"


class WhileNodeFactory:
    """Factory for while loop guard nodes.

    Creates a conditional routing node that implements while loop semantics.
    The guard node evaluates a condition and routes to either the loop body
    or the exit target.
    """

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a while loop guard node.

        The guard node:
        1. Evaluates the condition using slot values
        2. If TRUE: jumps to first step in do: block
        3. If FALSE: jumps to exit target

        The SubgraphBuilder automatically creates:
        - Edge from last step in do: back to this guard (loop back)
        - Edges for sequential flow within do: block
        """
        if not step.condition:
            raise ValueError(f"Step {step.step} of type 'while' missing required field 'condition'")
        if not step.do:
            raise ValueError(f"Step {step.step} of type 'while' missing required field 'do'")

        condition = step.condition
        loop_body_start = step.do[0]  # First step in do: block
        loop_body_end = step.do[-1]  # Last step in do: block
        while_node_name = step.step  # Name of this while node

        # Calculate default exit target: first step AFTER all steps in do: block
        exit_target = step.exit_to
        if not exit_target and all_steps and step_index is not None:
            do_step_names = set(step.do)

            for i in range(step_index + 1, len(all_steps)):
                candidate = all_steps[i]
                if candidate.step not in do_step_names:
                    exit_target = candidate.step
                    break
            # If no step found after while, will fall through to __end_flow__

        # Store loop metadata for SubgraphBuilder to use
        step.loop_body_start = loop_body_start
        step.loop_body_end = loop_body_end
        step.calculated_exit_target = exit_target or "__end_flow__"

        async def while_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> Command[Any] | dict[str, Any]:
            """Evaluate condition and route to loop body or exit."""
            context = get_runtime_context(config)
            flow_manager = context.flow_manager

            # Get all slots for condition evaluation
            slots = flow_manager.get_all_slots(state)

            # Evaluate condition
            is_true = evaluate_condition(condition, slots)

            if is_true:
                return Command(goto=loop_body_start)

            # Exit loop
            if exit_target:
                return Command(goto=exit_target)

            # Fallback: end flow
            return {}

        while_node.__name__ = f"while_{while_node_name}"
        return while_node
