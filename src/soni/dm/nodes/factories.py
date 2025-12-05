"""Node factory functions for creating LangGraph node functions from DAG nodes."""

import logging
from typing import Any, cast

from soni.compiler.dag import DAGNode, NodeType
from soni.core.events import EVENT_SLOT_COLLECTION, EVENT_VALIDATION_ERROR
from soni.core.interfaces import INLUProvider, INormalizer, IScopeManager
from soni.core.state import DialogueState, RuntimeContext
from soni.dm.node_factory_registry import NodeFactoryRegistry
from soni.du.models import MessageType, NLUOutput, SlotValue
from soni.validation.registry import ValidatorRegistry

logger = logging.getLogger(__name__)


def _ensure_dialogue_state(state: DialogueState | dict[str, Any]) -> DialogueState:
    """
    Ensure state is a DialogueState instance.

    Converts dict state to DialogueState if needed. This is necessary because
    LangGraph may pass state as a dict in some contexts, but our node functions
    expect DialogueState for type safety and convenience methods.

    Args:
        state: State as dict (from LangGraph) or DialogueState instance

    Returns:
        DialogueState instance (converted from dict if needed)
    """
    if isinstance(state, dict):
        return DialogueState.from_dict(state)
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
        return state_obj.trace
    except Exception as e:
        logger.debug(
            f"Error accessing trace safely: {e}",
            exc_info=True,
            extra={"state_type": type(state).__name__},
        )
        if isinstance(state, dict):
            return cast(list[dict[str, Any]], state.get("trace", []))
        return cast(list[dict[str, Any]], getattr(state, "trace", []))


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
    from soni.dm.routing import activate_flow_by_intent

    async def understand_node(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
        """Understand user message using NLU provider."""
        try:
            state = _ensure_dialogue_state(state)

            user_messages = state.get_user_messages()
            if not user_messages:
                logger.warning("No user messages in state")
                return {
                    "last_response": "I didn't receive any message. Please try again.",
                }

            user_message = user_messages[-1]

            dialogue_history = "\n".join(
                [
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    for msg in state.messages[:-1]
                ]
            )

            available_actions = scope_manager.get_available_actions(state)
            available_flows = scope_manager.get_available_flows(state)

            if state.current_flow and state.current_flow != "none":
                expected_slots = scope_manager.get_expected_slots(
                    flow_name=state.current_flow,
                    available_actions=available_actions,
                )
            else:
                expected_slots = []
                logger.debug(
                    f"No active flow, passing empty expected_slots. "
                    f"NLU will infer from available_flows: {available_flows}"
                )

            nlu_result_raw = await nlu_provider.predict(
                user_message=user_message,
                dialogue_history=dialogue_history,
                current_slots=state.slots,
                available_actions=available_actions,
                available_flows=available_flows,
                current_flow=state.current_flow,
                expected_slots=expected_slots,
            )

            # Convert to NLUOutput if needed
            if isinstance(nlu_result_raw, dict):
                slots_dict = nlu_result_raw.get("extracted_slots", {})
                if isinstance(slots_dict, dict):
                    slots_list = [
                        SlotValue(name=k, value=v, confidence=0.95) for k, v in slots_dict.items()
                    ]
                else:
                    slots_list = []
                nlu_result = NLUOutput(
                    message_type=MessageType.SLOT_VALUE,
                    command=nlu_result_raw.get("structured_command", ""),
                    slots=slots_list,
                    confidence=nlu_result_raw.get("confidence", 0.0),
                    reasoning=nlu_result_raw.get("reasoning", ""),
                )
            elif isinstance(nlu_result_raw, NLUOutput):
                nlu_result = nlu_result_raw
            else:
                nlu_result = NLUOutput(
                    message_type=MessageType.SLOT_VALUE,
                    command="",
                    slots=[],
                    confidence=0.0,
                    reasoning="",
                )

            # Normalize extracted slots
            normalized_slots = {slot.name: slot.value for slot in nlu_result.slots}
            failed_slots: list[dict[str, Any]] = []
            if normalized_slots:
                try:
                    normalized_dict: dict[str, Any] = {}
                    for slot_name, slot_value in normalized_slots.items():
                        try:
                            slot_config = context.get_slot_config(slot_name)
                            normalization_config = getattr(slot_config, "normalization", None)
                            entity_config = {
                                "name": slot_name,
                                "type": getattr(slot_config, "type", "string"),
                                "normalization": (
                                    normalization_config.model_dump()
                                    if normalization_config is not None
                                    else {}
                                ),
                            }
                            try:
                                normalized_value = await normalizer.normalize(
                                    slot_value, entity_config
                                )
                                normalized_dict[slot_name] = normalized_value
                            except (ValueError, TypeError, KeyError, AttributeError) as e:
                                logger.warning(
                                    f"Normalization failed for slot '{slot_name}': {e}",
                                    extra={
                                        "slot_name": slot_name,
                                        "slot_value": str(slot_value),
                                        "error": str(e),
                                    },
                                )
                                normalized_dict[slot_name] = slot_value
                                failed_slots.append(
                                    {
                                        "slot_name": slot_name,
                                        "value": str(slot_value),
                                        "error": str(e),
                                    }
                                )
                        except KeyError:
                            normalized_dict[slot_name] = slot_value
                    normalized_slots = normalized_dict
                    logger.info(f"Normalized slots: {normalized_slots}")
                except Exception as e:
                    logger.error(
                        f"Unexpected normalization error: {e}",
                        exc_info=True,
                        extra={
                            "slots": list(normalized_slots.keys()) if normalized_slots else [],
                        },
                    )
                    raise

            updated_slots = state.slots.copy()
            slots_before = updated_slots.copy()
            updated_slots.update(normalized_slots)
            slots_after = updated_slots.copy()

            if normalized_slots:
                logger.info(
                    f"Extracted slots from user message: {normalized_slots}",
                    extra={
                        "user_message": user_message,
                        "slots_before": slots_before,
                        "slots_after": slots_after,
                        "extracted_slots": normalized_slots,
                    },
                )

            new_current_flow = activate_flow_by_intent(
                command=nlu_result.command,
                current_flow=state.current_flow,
                config=context.config,
            )

            updates: dict[str, Any] = {
                "slots": updated_slots,
                "pending_action": nlu_result.command if nlu_result.command else None,
                "current_flow": new_current_flow,
                "trace": state.trace
                + [
                    {
                        "event": "nlu_result",
                        "data": {
                            "command": nlu_result.command,
                            "slots": nlu_result.slots,
                            "confidence": nlu_result.confidence,
                            "reasoning": nlu_result.reasoning,
                        },
                    }
                ],
            }

            if failed_slots:
                updates["trace"][-1]["data"]["normalization_failed"] = True
                updates["trace"][-1]["data"]["failed_slots"] = failed_slots
                logger.warning(
                    f"Normalization failed for {len(failed_slots)} slot(s)",
                    extra={
                        "failed_count": len(failed_slots),
                        "failed_slots": [s["slot_name"] for s in failed_slots],
                    },
                )

            logger.info(
                f"NLU result: command={nlu_result.command}, "
                f"confidence={nlu_result.confidence:.2f}, "
                f"slots={normalized_slots}"
            )

            return updates

        except (ImportError, AttributeError, RuntimeError, TypeError) as e:
            from soni.core.errors import NLUError

            error_user_message: str | None = None
            if "user_messages" in locals() and user_messages:
                error_user_message = user_messages[-1]
            logger.error(
                f"NLU processing failed: {e}",
                exc_info=True,
                extra={
                    "user_message": error_user_message,
                    "error_type": type(e).__name__,
                },
            )
            raise NLUError(
                f"NLU processing failed: {e}",
                context={"user_message": error_user_message},
            ) from e
        except Exception as e:
            from soni.core.errors import NLUError

            if "user_messages" in locals() and user_messages:
                error_user_msg = user_messages[-1]
            else:
                error_user_msg = None
            logger.error(
                f"Unexpected NLU error: {e}",
                exc_info=True,
                extra={
                    "user_message": error_user_msg,
                    "error_type": type(e).__name__,
                },
            )
            raise NLUError(
                f"Unexpected NLU error: {e}",
                context={"user_message": error_user_msg},
            ) from e

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
        slot_config = context.get_slot_config(slot_name)
        slot_value = state.get_slot(slot_name)

        is_filled = (
            slot_value is not None
            and slot_value != ""
            and (not isinstance(slot_value, str) or slot_value.strip() != "")
        )

        logger.debug(
            f"Checking slot '{slot_name}': value={slot_value}, is_filled={is_filled}",
            extra={
                "slot_name": slot_name,
                "slot_value": slot_value,
                "is_filled": is_filled,
                "current_flow": state.current_flow,
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
                        return {
                            "slots": {slot_name: None},
                            "last_response": (
                                f"Invalid format for {slot_name}. Please provide a valid value."
                            ),
                            "trace": state.trace
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
        updates = {
            "last_response": prompt,
            "messages": state.messages + [{"role": "assistant", "content": prompt}],
            "trace": state.trace
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
                "current_flow": state.current_flow,
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

        action_handler = context.action_handler
        action_config = context.get_action_config(action_name)

        action_inputs: dict[str, Any] = {}
        for input_name in action_config.inputs:
            # Try to get from slots first, then from state directly
            slot_value = state.get_slot(input_name)
            if slot_value is not None:
                action_inputs[input_name] = slot_value
            elif hasattr(state, input_name):
                action_inputs[input_name] = getattr(state, input_name)
            elif isinstance(state, dict) and input_name in state:
                action_inputs[input_name] = state[input_name]

        try:
            action_result = await action_handler.execute(
                action_name=action_name,
                inputs=action_inputs,
            )

            updates: dict[str, Any] = {
                "trace": state.trace
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

            if map_outputs:
                mapped_slots: dict[str, Any] = {}
                for state_var, action_output in map_outputs.items():
                    if action_output in action_result:
                        mapped_slots[state_var] = action_result[action_output]
                if mapped_slots:
                    current_slots = state.slots.copy()
                    current_slots.update(mapped_slots)
                    updates["slots"] = current_slots
            else:
                if action_result:
                    current_slots = state.slots.copy()
                    current_slots.update(action_result)
                    updates["slots"] = current_slots

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
        scope_manager=context.scope_manager,
        normalizer=context.normalizer,
        nlu_provider=context.du,
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
