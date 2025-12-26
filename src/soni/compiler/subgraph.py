"""Subgraph builder for M3 with branch and while support."""

from langgraph.graph import END, StateGraph

from soni.compiler.factory import get_factory_for_step
from soni.config.models import BranchStepConfig, FlowConfig, StepConfig, WhileStepConfig
from soni.core.types import DialogueState
from soni.runtime.context import RuntimeContext


def _flatten_inline_steps(steps: list[StepConfig]) -> list[StepConfig]:
    """Extract inline step definitions from while loops and flatten into step list.

    This allows while loops to define steps inline:

        - while:
            step: loop
            condition: "counter < 3"
            do:
              - set:
                  step: increment
                  slots: {counter: ...}

    The inline steps are extracted and added to the main step list.
    """
    result: list[StepConfig] = []

    for step in steps:
        result.append(step)

        # Extract inline steps from while loops
        if isinstance(step, WhileStepConfig):
            for inline_step in step.get_inline_steps():
                result.append(inline_step)

    return result


def build_flow_subgraph(flow: FlowConfig):
    """Build a compiled subgraph for a flow.

    Supports:
    - Linear flows
    - Conditional branching via _branch_target
    - While loops with automatic loop-back from last do step
    - Inline step definitions in while loops

    Branch targets reference step names (e.g., "low_value") which are
    translated to node names (e.g., "say_low_value") for routing.
    """
    builder = StateGraph(DialogueState, context_schema=RuntimeContext)

    # Flatten inline steps from while loops
    all_steps = _flatten_inline_steps(list(flow.steps))

    # First pass: collect node names and build step-to-node mapping
    node_names: list[str] = []
    step_to_node: dict[str, str] = {}  # step name -> node name

    for i, step in enumerate(all_steps):
        factory = get_factory_for_step(step.type)
        node_func = factory.create(step, flow.steps, i)
        node_name = node_func.__name__
        node_names.append(node_name)
        step_to_node[step.step] = node_name
        builder.add_node(node_name, node_func)

    valid_node_names = set(node_names)
    valid_node_names.add(END)

    # Collect branch targets - they route to END after executing
    branch_targets: set[str] = set()
    for step in flow.steps:
        if isinstance(step, BranchStepConfig):
            for case_target in step.cases.values():
                if case_target != "default":
                    node_name = step_to_node.get(case_target, case_target)
                    branch_targets.add(node_name)

    # Collect while loop metadata: last step in do block -> loop back to guard
    loop_back_targets: dict[str, str] = {}  # last do step -> while guard
    while_guards: set[str] = set()
    for step in all_steps:
        if isinstance(step, WhileStepConfig):
            guard_name = step_to_node[step.step]
            while_guards.add(guard_name)
            # Get step names (handles both string refs and inline definitions)
            do_step_names = step.get_do_step_names()
            # Last step in do block should loop back to guard
            last_do_step = do_step_names[-1]
            if last_do_step in step_to_node:
                loop_back_targets[step_to_node[last_do_step]] = guard_name
            # All steps in do block are branch targets (for the while)
            for do_step in do_step_names:
                if do_step in step_to_node:
                    branch_targets.add(step_to_node[do_step])

    def _create_router(
        default_target: str,
        step_mapping: dict[str, str],
        valid_targets: set[str],
    ):
        """Create router that supports branch targets."""

        def router(state: DialogueState) -> str:
            pending_task = state.get("_pending_task")

            if pending_task:
                # ADR-002: Only exit if task requires interruption (blocking)
                # Inform tasks with wait_for_ack=False are non-blocking
                is_blocking = True
                if pending_task.get("type") == "inform" and not pending_task.get("wait_for_ack"):
                    is_blocking = False

                if is_blocking:
                    return str(END)

            target = state.get("_branch_target")
            if target:
                # Special: __end__ for link/call to exit subgraph early
                if target == "__end__":
                    return str(END)
                node_name = step_mapping.get(target, target)
                if node_name in valid_targets:
                    return node_name

            return default_target

        return router

    # Second pass: add edges
    for i, node_name in enumerate(node_names):
        if i == 0:
            builder.set_entry_point(node_name)

        # Determine default next step
        # Determine default next step
        if node_name in loop_back_targets:
            # Last step in while loop - loops back to guard
            default_next = loop_back_targets[node_name]
        elif node_name in branch_targets:
            # Case targets should be terminal within the flow diversion
            default_next = END
        elif i < len(node_names) - 1:
            default_next = node_names[i + 1]
        else:
            default_next = END

        builder.add_conditional_edges(
            node_name,
            _create_router(default_next, step_to_node, valid_node_names),
        )

    return builder.compile()
