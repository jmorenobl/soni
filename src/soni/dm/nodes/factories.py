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
from soni.du.models import MessageType, NLUOutput, SlotValue
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
    from soni.dm.routing import activate_flow_by_intent

    async def understand_node(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
        """Understand user message using NLU provider.

        Reads user message from state["user_message"] as per design (05-message-flow.md).
        The messages[] list is used only for building conversation history.
        """
        try:
            state = _ensure_dialogue_state(state)

            # Read from user_message field (per design: 05-message-flow.md)
            user_message = state.get("user_message", "")
            if not user_message or not user_message.strip():
                logger.warning("No user_message in state")
                return {
                    "last_response": "I didn't receive any message. Please try again.",
                }

            # Build dspy.History from messages
            import dspy

            from soni.du.models import DialogueContext

            # dspy.History accepts a list of message dicts directly
            messages = state.get("messages", [])
            history_messages = messages[:-1]  # All messages except the last one
            history = dspy.History(messages=history_messages)

            available_actions = scope_manager.get_available_actions(state)
            available_flows = scope_manager.get_available_flows(state)

            # Get current flow name
            from soni.core.state import get_current_flow

            current_flow = get_current_flow(state)
            if current_flow and current_flow != "none":
                expected_slots = scope_manager.get_expected_slots(
                    flow_name=current_flow,
                    available_actions=available_actions,
                )
            else:
                expected_slots = []
                logger.debug(
                    f"No active flow, passing empty expected_slots. "
                    f"NLU will infer from available_flows: {list(available_flows.keys())}"
                )

            # Get all current slots
            current_slots = get_all_slots(state)

            # Get currently prompted slot (if any)
            current_prompted_slot = state.get("current_prompted_slot")

            # Create DialogueContext
            dialogue_context = DialogueContext(
                current_slots=current_slots,
                available_actions=available_actions,
                available_flows=available_flows,
                current_flow=current_flow,
                expected_slots=expected_slots,
                current_prompted_slot=current_prompted_slot,
            )

            nlu_result_raw = await nlu_provider.predict(
                user_message=user_message,
                history=history,
                context=dialogue_context,
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
                    command=nlu_result_raw.get("structured_command") or None,
                    slots=slots_list,
                    confidence=nlu_result_raw.get("confidence", 0.0),
                )
            elif isinstance(nlu_result_raw, NLUOutput):
                nlu_result = nlu_result_raw
            else:
                nlu_result = NLUOutput(
                    message_type=MessageType.SLOT_VALUE,
                    command=None,
                    slots=[],
                    confidence=0.0,
                )

            # Determine target flow BEFORE slot validation
            # This ensures we use the correct expected_slots for the flow being activated
            from soni.core.state import get_current_flow

            current_flow_name = get_current_flow(state)
            config = context["config"]
            target_flow = activate_flow_by_intent(
                command=nlu_result.command,
                current_flow=current_flow_name,
                config=config,
            )

            # Get expected_slots for TARGET flow (may differ from current flow)
            if target_flow and target_flow != current_flow_name and target_flow != "none":
                # New flow being activated - use its expected_slots
                target_expected_slots = scope_manager.get_expected_slots(
                    flow_name=target_flow,
                    available_actions=available_actions,
                )
                logger.debug(
                    f"Flow activation detected: {current_flow_name} -> {target_flow}, "
                    f"using target flow expected_slots: {target_expected_slots}"
                )
            else:
                # Staying in current flow - use current expected_slots
                target_expected_slots = expected_slots

            # Normalize extracted slots
            # When we have a current_prompted_slot and the NLU extracts a slot_value,
            # use the prompted slot name to ensure correct assignment
            current_prompted_slot = state.get("current_prompted_slot")
            normalized_slots: dict[str, Any] = {}

            if nlu_result.slots:
                expected_set = set(target_expected_slots)

                if (
                    current_prompted_slot
                    and nlu_result.message_type.value == "slot_value"
                    and len(nlu_result.slots) == 1
                ):
                    # User responded to a direct prompt
                    extracted_slot = nlu_result.slots[0]

                    # Check if NLU's slot name matches the prompted slot or is unknown
                    if (
                        extracted_slot.name == current_prompted_slot
                        or extracted_slot.name not in expected_set
                    ):
                        # Assign to prompted slot
                        normalized_slots[current_prompted_slot] = extracted_slot.value
                        logger.debug(
                            f"Assigned value '{extracted_slot.value}' to prompted slot "
                            f"'{current_prompted_slot}' (NLU named it '{extracted_slot.name}')"
                        )
                    else:
                        # NLU recognized a DIFFERENT known slot - respect NLU's semantic analysis
                        # This happens when user provides unexpected info (e.g., date when asked for city)
                        normalized_slots[extracted_slot.name] = extracted_slot.value
                        logger.info(
                            f"NLU extracted '{extracted_slot.name}' but prompted for "
                            f"'{current_prompted_slot}' - respecting NLU's semantic analysis"
                        )
                else:
                    # Multiple slots or no prompt context - validate against target flow's slots
                    for slot in nlu_result.slots:
                        if slot.name in expected_set:
                            normalized_slots[slot.name] = slot.value
                        else:
                            # Log warning for unknown slot names
                            logger.warning(
                                f"NLU extracted unknown slot '{slot.name}' "
                                f"(expected: {target_expected_slots}). Discarding value: {slot.value}"
                            )

            failed_slots: list[dict[str, Any]] = []
            if normalized_slots:
                try:
                    normalized_dict: dict[str, Any] = {}
                    for slot_name, slot_value in normalized_slots.items():
                        try:
                            slot_config = get_slot_config(context, slot_name)
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

            # Update slots - need to merge with existing slots
            from soni.core.state import push_flow, set_all_slots

            current_slots = get_all_slots(state)
            slots_before = current_slots.copy()
            current_slots.update(normalized_slots)
            slots_after = current_slots.copy()

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

            # Use target_flow determined earlier (before slot validation)
            new_current_flow = target_flow

            # Build updates dict
            trace = state.get("trace", [])
            updates: dict[str, Any] = {
                "trace": trace
                + [
                    {
                        "event": "nlu_result",
                        "data": {
                            "command": nlu_result.command,
                            "slots": nlu_result.slots,
                            "confidence": nlu_result.confidence,
                        },
                    }
                ],
            }

            # If flow changed, update flow_stack and flow_slots
            if new_current_flow != current_flow_name:
                if new_current_flow and new_current_flow != "none":
                    # Push new flow onto stack (also initializes flow_slots for new flow)
                    push_flow(state, new_current_flow)
                    updates["flow_stack"] = state.get("flow_stack", [])
                    # CRITICAL: Include flow_slots in updates to persist slot storage initialization
                    updates["flow_slots"] = state.get("flow_slots", {})

            # Update slots in state (merge with any previously initialized slots)
            if normalized_slots:
                set_all_slots(state, current_slots)
                updates["flow_slots"] = state.get("flow_slots", {})

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

            # Clear prompted slot after processing to avoid carrying it to next turn
            if current_prompted_slot and normalized_slots:
                updates["current_prompted_slot"] = None

            return updates

        except (ImportError, AttributeError, RuntimeError, TypeError) as e:
            from soni.core.errors import NLUError

            error_user_message: str | None = (
                state.get("user_message") if "user_message" in state else None
            )
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

            error_user_msg = state.get("user_message") if "user_message" in state else None
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
