"""Node factory functions for creating LangGraph node functions from DAG nodes."""

import logging
from typing import Any, cast

from soni.compiler.dag import DAGNode, NodeType
from soni.core.events import EVENT_SLOT_COLLECTION, EVENT_VALIDATION_ERROR
from soni.core.interfaces import INLUProvider, INormalizer, IScopeManager
from soni.core.state import (
    DialogueState,
    RuntimeContext,
    get_all_slots,
    get_slot,
    get_slot_config,
)
from soni.dm.node_factory_registry import NodeFactoryRegistry
from soni.validation.registry import ValidatorRegistry

logger = logging.getLogger(__name__)


def _ensure_dialogue_state(state: DialogueState | dict[str, Any]) -> DialogueState | dict[str, Any]:
    """
        Return state as-is (no conversion needed).

        This function used to convert dict to DialogueState, but since Dialog

    ueState
        is now a TypedDict (which is compatible with dict at runtime), and our helper
        functions work with both, no conversion is needed.

        Args:
            state: State as dict or DialogueState (both work with helper functions)

        Returns:
            State as-is (DialogueState TypedDict or dict)
    """
    # No conversion needed - helper functions handle both DialogueState and dict
    return state


def _get_trace_safely(state: DialogueState | dict[str, Any]) -> list[dict[str, Any]]:
    """
    Safely extract trace from state, handling all error cases.

    Args:
        state: Current dialogue state (dict or DialogueState)

    Returns:
        Trace list (empty list if extraction fails)
    """
    try:
        state_obj = _ensure_dialogue_state(state)
        return state_obj.get("trace", [])
    except Exception as e:
        logger.debug(
            f"Error accessing trace safely: {e}",
            exc_info=True,
            extra={"state_type": type(state).__name__},
        )
        if isinstance(state, dict):
            return cast(list[dict[str, Any]], state.get("trace", []))
        return []


def create_understand_node(
    scope_manager: IScopeManager,
    normalizer: INormalizer,
    nlu_provider: INLUProvider,
    context: RuntimeContext,
) -> Any:
    """Create understand node factory function.

    This factory creates an async node function that processes NLU,
    normalizes slots, and updates dialogue state.

    Args:
        scope_manager: Scope manager for action filtering
        normalizer: Normalizer for slot normalization
        nlu_provider: NLU provider for understanding user messages
        context: Runtime context with configuration and dependencies

    Returns:
        Async node function that takes DialogueState | dict[str, Any]
        and returns dict[str, Any] (state updates)
    """
    # Import here to avoid circular imports

    async def understand_node(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
        """Understand user message using NLU provider (v2.0 Command-Based).

        1. Read user_message
        2. Call NLU (returns Commands)
        3. Store commands in state for Executor
        """
        try:
            state = _ensure_dialogue_state(state)
            user_message = state.get("user_message", "")

            # Simple context creation (DRY)
            from soni.du.models import DialogueContext

            context_obj = DialogueContext(
                current_slots=get_all_slots(state),
                current_flow=state.get("flow_stack", [{}])[-1].get("flow_name", "none"),
            )

            # dspy.History
            import dspy

            messages = state.get("messages", [])
            history = dspy.History(messages=messages[:-1])  # simplistic

            # Call NLU
            nlu_result = await nlu_provider.predict(
                user_message=user_message,
                history=history,
                context=context_obj,
            )

            # Store commands for the Executor node
            return {
                "command_log": nlu_result.commands,
                "nlu_result": nlu_result,  # Keep raw result if needed
                "trace": state.get("trace", [])
                + [
                    {
                        "event": "nlu_result",
                        "data": {"commands": [str(c) for c in nlu_result.commands]},
                    }
                ],
            }

        except Exception as e:
            logger.error(f"NLU failed: {e}", exc_info=True)
            return {"command_log": []}

    return understand_node


async def collect_slot_node(
    state: DialogueState | dict[str, Any],
    slot_name: str,
    context: RuntimeContext,
) -> dict[str, Any]:
    """
    Collect a slot value from user.

    Trust NLU extractions. Only prompt if slot is missing.
    Validators check format/syntax only, not semantics.
    """
    try:
        state = _ensure_dialogue_state(state)
        slot_config = get_slot_config(context, slot_name)
        slot_value = get_slot(state, slot_name)

        is_filled = (
            slot_value is not None
            and slot_value != ""
            and (not isinstance(slot_value, str) or slot_value.strip() != "")
        )

        # Get current flow for logging
        from soni.core.state import get_current_flow

        current_flow = get_current_flow(state)

        logger.debug(
            f"Checking slot '{slot_name}': value={slot_value}, is_filled={is_filled}",
            extra={
                "slot_name": slot_name,
                "slot_value": slot_value,
                "is_filled": is_filled,
                "current_flow": current_flow,
            },
        )

        if is_filled:
            if slot_config.validator:
                try:
                    is_valid = ValidatorRegistry.validate(
                        name=slot_config.validator,
                        value=slot_value,
                    )
                    if not is_valid:
                        logger.warning(
                            f"Slot '{slot_name}' value '{slot_value}' "
                            f"failed format validation with '{slot_config.validator}' - "
                            f"re-collecting from user"
                        )
                        # Clear the invalid slot
                        from soni.core.state import set_slot

                        set_slot(state, slot_name, None)
                        trace = state.get("trace", [])
                        return {
                            "flow_slots": state.get("flow_slots", {}),
                            "last_response": (
                                f"Invalid format for {slot_name}. Please provide a valid value."
                            ),
                            "trace": trace
                            + [
                                {
                                    "event": EVENT_VALIDATION_ERROR,
                                    "data": {
                                        "slot": slot_name,
                                        "value": slot_value,
                                        "validator": slot_config.validator,
                                    },
                                }
                            ],
                        }
                except ValueError:
                    logger.debug(
                        f"Validator '{slot_config.validator}' not found for slot '{slot_name}' - "
                        f"trusting value"
                    )

            logger.debug(f"Slot '{slot_name}' is filled: {slot_value} - continuing")
            return {}

        prompt = slot_config.prompt
        messages = state.get("messages", [])
        trace = state.get("trace", [])
        updates = {
            "last_response": prompt,
            "current_prompted_slot": slot_name,  # Track which slot we're asking for
            "messages": messages + [{"role": "assistant", "content": prompt}],
            "trace": trace
            + [
                {
                    "event": EVENT_SLOT_COLLECTION,
                    "data": {"slot": slot_name, "prompt": prompt},
                }
            ],
        }

        logger.info(
            f"Prompting for slot '{slot_name}': {prompt}",
            extra={
                "slot_name": slot_name,
                "current_flow": current_flow,
            },
        )

        return updates

    except KeyError as e:
        logger.warning(
            f"Slot '{slot_name}' not found in configuration: {e}",
            extra={"slot_name": slot_name},
        )
        trace = _get_trace_safely(state)
        return {
            "last_response": f"Error: Slot '{slot_name}' not found in configuration.",
            "trace": trace
            + [
                {
                    "event": "error",
                    "data": {"slot": slot_name, "error": str(e)},
                }
            ],
        }
    except (ValueError, AttributeError, TypeError) as e:
        logger.error(
            f"Error in collect_slot_node: {e}",
            exc_info=True,
            extra={"slot_name": slot_name, "error_type": type(e).__name__},
        )
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in collect_slot_node: {e}",
            exc_info=True,
            extra={"slot_name": slot_name, "error_type": type(e).__name__},
        )
        raise


def create_collect_node_factory(slot_name: str, context: RuntimeContext) -> Any:
    """Create collect node factory function.

    Args:
        slot_name: Name of the slot to collect
        context: Runtime context with configuration and dependencies

    Returns:
        Async node function that collects a slot value
    """

    async def collect_node(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
        state = _ensure_dialogue_state(state)
        return await collect_slot_node(state, slot_name, context)

    return collect_node


def create_action_node_factory(
    action_name: str,
    context: RuntimeContext,
    map_outputs: dict[str, str] | None = None,
) -> Any:
    """Create action node factory function.

    Args:
        action_name: Name of the action to execute
        context: Runtime context with configuration and dependencies
        map_outputs: Optional mapping from action outputs to state variables

    Returns:
        Async node function that executes an action
    """

    async def action_node_wrapper(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
        state = _ensure_dialogue_state(state)

        from soni.core.state import get_action_config

        action_handler = context["action_handler"]
        action_config = get_action_config(context, action_name)

        action_inputs: dict[str, Any] = {}
        for input_name in action_config.inputs:
            # Try to get from slots first, then from state directly
            slot_value = get_slot(state, input_name)
            if slot_value is not None:
                action_inputs[input_name] = slot_value
            else:
                # Try getting from state dict directly (for special top-level fields)
                # These are unlikely to be action inputs but handle them just in case
                # Only check for common top-level state fields
                if isinstance(state, dict) and input_name in (
                    "user_message",
                    "last_response",
                    "conversation_state",
                    "turn_count",
                ):
                    try:
                        action_inputs[input_name] = state.get(input_name)
                    except (KeyError, TypeError):
                        pass

        try:
            action_result = await action_handler.execute(
                action_name=action_name,
                slots=action_inputs,
            )

            trace = state.get("trace", [])
            updates: dict[str, Any] = {
                "trace": trace
                + [
                    {
                        "event": "action_executed",
                        "data": {
                            "action": action_name,
                            "inputs": action_inputs,
                            "outputs": action_result,
                        },
                    }
                ],
            }

            # Map outputs to slots if mapping specified
            if map_outputs:
                from soni.core.state import set_all_slots

                mapped_slots: dict[str, Any] = {}
                for state_var, action_output in map_outputs.items():
                    if action_output in action_result:
                        mapped_slots[state_var] = action_result[action_output]
                if mapped_slots:
                    current_slots = get_all_slots(state)
                    current_slots.update(mapped_slots)
                    set_all_slots(state, current_slots)
                    updates["flow_slots"] = state.get("flow_slots", {})
            else:
                # No mapping - store all action results as slots
                if action_result:
                    from soni.core.state import set_all_slots

                    current_slots = get_all_slots(state)
                    current_slots.update(action_result)
                    set_all_slots(state, current_slots)
                    updates["flow_slots"] = state.get("flow_slots", {})

            logger.info(
                f"Action '{action_name}' executed successfully",
                extra={
                    "action": action_name,
                    "inputs": action_inputs,
                    "outputs": action_result,
                },
            )

            return updates

        except Exception as e:
            logger.error(
                f"Action '{action_name}' execution failed: {e}",
                exc_info=True,
                extra={"action": action_name, "inputs": action_inputs},
            )
            raise

    return action_node_wrapper


# Register default node factories
@NodeFactoryRegistry.register(NodeType.UNDERSTAND)
def create_understand_factory(node: DAGNode, context: RuntimeContext) -> Any:
    """Factory for UNDERSTAND nodes."""
    return create_understand_node(
        scope_manager=context["scope_manager"],
        normalizer=context["normalizer"],
        nlu_provider=context["du"],
        context=context,
    )


@NodeFactoryRegistry.register(NodeType.COLLECT)
def create_collect_factory(node: DAGNode, context: RuntimeContext) -> Any:
    """Factory for COLLECT nodes."""
    slot_name = node.config["slot_name"]
    return create_collect_node_factory(slot_name, context)


@NodeFactoryRegistry.register(NodeType.ACTION)
def create_action_factory(node: DAGNode, context: RuntimeContext) -> Any:
    """Factory for ACTION nodes with output mapping support."""
    action_name = node.config["action_name"]
    map_outputs = node.config.get("map_outputs")
    return create_action_node_factory(action_name, context, map_outputs=map_outputs)


def create_confirm_node_factory(context: RuntimeContext) -> Any:
    """Create confirm node factory function.

    Args:
        context: Runtime context with configuration and dependencies

    Returns:
        Async node function that requests user confirmation
    """
    from soni.dm.builder import RuntimeWrapper
    from soni.dm.nodes.confirm_action import confirm_action_node

    runtime = RuntimeWrapper(context)

    async def confirm_node(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
        """Request user confirmation before executing an action."""
        state_typed = _ensure_dialogue_state(state)
        # Type assertion: _ensure_dialogue_state returns DialogueState-compatible type
        result = await confirm_action_node(
            state_typed,  # type: ignore[arg-type]
            runtime,
        )
        return dict(result) if result else {}

    return confirm_node


@NodeFactoryRegistry.register(NodeType.CONFIRM)
def create_confirm_factory(node: DAGNode, context: RuntimeContext) -> Any:
    """Factory for CONFIRM nodes."""
    return create_confirm_node_factory(context)
