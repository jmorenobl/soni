"""Node factories for dialogue graph nodes"""

import logging
from typing import Any, cast

from soni.compiler.dag import DAGNode, NodeType
from soni.core.interfaces import INLUProvider, INormalizer, IScopeManager
from soni.core.state import DialogueState, RuntimeContext
from soni.dm.node_factory_registry import NodeFactoryRegistry
from soni.du.modules import NLUResult
from soni.validation.registry import ValidatorRegistry

logger = logging.getLogger(__name__)


def _ensure_dialogue_state(
    state: DialogueState | dict[str, Any],
) -> DialogueState:
    """
    Ensure state is a DialogueState instance.

    Converts dict state to DialogueState if needed. This is necessary because
    LangGraph may pass state as a dict in some contexts, but our node functions
    expect DialogueState for type safety and convenience methods.

    Args:
        state: State as dict (from LangGraph) or DialogueState instance

    Returns:
        DialogueState instance (converted from dict if needed)

    Example:
        >>> state_dict = {"messages": [], "slots": {}, "current_flow": "booking"}
        >>> _ensure_dialogue_state(state_dict)
        DialogueState(messages=[], slots={}, current_flow='booking', ...)

        >>> state_obj = DialogueState(current_flow="booking")
        >>> _ensure_dialogue_state(state_obj) is state_obj
        True

    Note:
        This function is idempotent: if state is already a DialogueState,
        it is returned unchanged. No side effects.
    """
    if isinstance(state, dict):
        return DialogueState.from_dict(state)
    return state


def _get_trace_safely(state: DialogueState | dict[str, Any]) -> list[dict[str, Any]]:
    """
    Safely extract trace from state, handling all error cases.

    This function handles cases where:
    - State might not be converted yet
    - State might be missing trace attribute
    - Trace access might fail for various reasons

    Args:
        state: Current dialogue state (dict or DialogueState)

    Returns:
        Trace list (empty list if extraction fails)

    Example:
        >>> state = DialogueState(trace=[{"event": "test"}])
        >>> _get_trace_safely(state)
        [{"event": "test"}]

        >>> state_dict = {"trace": [{"event": "test"}]}
        >>> _get_trace_safely(state_dict)
        [{"event": "test"}]

        >>> invalid_state = {}
        >>> _get_trace_safely(invalid_state)
        []
    """
    try:
        state_obj = _ensure_dialogue_state(state)
        return state_obj.trace
    except Exception as e:
        # Log at debug level - this is expected in error scenarios
        logger.debug(
            f"Error accessing trace safely: {e}",
            exc_info=True,
            extra={"state_type": type(state).__name__},
        )
        # Fallback to direct attribute/dict access
        if isinstance(state, dict):
            return cast(list[dict[str, Any]], state.get("trace", []))
        return cast(list[dict[str, Any]], getattr(state, "trace", []))


def create_understand_node(
    scope_manager: IScopeManager,
    normalizer: INormalizer,
    nlu_provider: INLUProvider,
    context: RuntimeContext,
) -> Any:  # Returns: Callable[[DialogueState | dict[str, Any]], Awaitable[dict[str, Any]]]
    """
    Create understand node factory function.

    This factory creates an async node function that processes NLU,
    normalizes slots, and updates dialogue state.

    Args:
        scope_manager: Scope manager for action filtering
        normalizer: Normalizer for slot normalization
        nlu_provider: NLU provider for understanding user messages
        context: Runtime context with configuration and dependencies.
                 Always required - provides access to config for normalization
                 and other runtime dependencies.

    Returns:
        Async node function.
        Type: Callable[[DialogueState | dict[str, Any]], Awaitable[dict[str, Any]]]
        (annotated as Any due to LangGraph internals)

    Note:
        Return type is `Any` because LangGraph's node function type is
        a complex internal type. The actual return type is an async function
        that takes DialogueState | dict[str, Any] and returns dict[str, Any]
        (state updates).

        RuntimeContext is required because:
        - Nodes need access to config for normalization settings
        - Provides consistent way to pass all runtime dependencies
        - Simplifies node creation (no need to handle None case)
    """

    async def understand_node(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
        """
        Understand user message using SoniDU.

        This node:
        1. Extracts the last user message from state
        2. Calls SoniDU to get NLU result
        3. Updates state with extracted slots and command

        Args:
            state: Current dialogue state (dict or DialogueState)

        Returns:
            Dictionary with state updates
        """
        try:
            # Convert dict to DialogueState if needed
            state = _ensure_dialogue_state(state)

            # Get last user message
            user_messages = state.get_user_messages()
            if not user_messages:
                logger.warning("No user messages in state")
                return {
                    "last_response": "I didn't receive any message. Please try again.",
                }

            user_message = user_messages[-1]

            # Build dialogue history
            dialogue_history = "\n".join(
                [
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    for msg in state.messages[:-1]
                ]
            )

            # Get scoped actions using injected scope_manager
            available_actions = scope_manager.get_available_actions(state)

            # Call NLU using injected provider
            nlu_result_raw = await nlu_provider.predict(
                user_message=user_message,
                dialogue_history=dialogue_history,
                current_slots=state.slots,
                available_actions=available_actions,
                current_flow=state.current_flow,
            )

            # Convert to NLUResult if needed
            if isinstance(nlu_result_raw, dict):
                nlu_result = NLUResult(
                    command=nlu_result_raw.get("structured_command", ""),
                    slots=nlu_result_raw.get("extracted_slots", {}),
                    confidence=nlu_result_raw.get("confidence", 0.0),
                    reasoning=nlu_result_raw.get("reasoning", ""),
                )
            elif isinstance(nlu_result_raw, NLUResult):
                nlu_result = nlu_result_raw
            else:
                # Fallback: create empty NLUResult
                nlu_result = NLUResult(
                    command="",
                    slots={},
                    confidence=0.0,
                    reasoning="",
                )

            # Normalize extracted slots before updating state using injected normalizer
            normalized_slots = nlu_result.slots
            failed_slots: list[dict[str, Any]] = []
            if normalized_slots:
                try:
                    normalized_dict: dict[str, Any] = {}
                    for slot_name, slot_value in normalized_slots.items():
                        try:
                            # Use type-safe config accessor
                            slot_config = context.get_slot_config(slot_name)
                            # Get normalization config safely (may not exist in SlotConfig)
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
                                # Normalización falló para este slot específico
                                logger.warning(
                                    f"Normalization failed for slot '{slot_name}': {e}",
                                    extra={
                                        "slot_name": slot_name,
                                        "slot_value": str(slot_value),
                                        "error": str(e),
                                    },
                                )
                                # Usar valor original
                                normalized_dict[slot_name] = slot_value
                                failed_slots.append(
                                    {
                                        "slot_name": slot_name,
                                        "value": str(slot_value),
                                        "error": str(e),
                                    }
                                )
                        except KeyError:
                            # Slot not configured - use raw value
                            normalized_dict[slot_name] = slot_value
                    normalized_slots = normalized_dict
                    logger.info(f"Normalized slots: {normalized_slots}")

                    # Marcar en metadata si alguna normalización falló
                    # Metadata will be included in updates dict below
                except Exception as e:
                    # Errores inesperados en todo el proceso de normalización
                    logger.error(
                        f"Unexpected normalization error: {e}",
                        exc_info=True,
                        extra={
                            "slots": list(normalized_slots.keys()) if normalized_slots else [],
                        },
                    )
                    # Re-raise para debugging (no ocultar errores inesperados)
                    raise

            # Update state with NLU results (using normalized slots)
            updated_slots = state.slots.copy()
            updated_slots.update(normalized_slots)

            # Prepare updates dict
            updates: dict[str, Any] = {
                "slots": updated_slots,
                "pending_action": nlu_result.command if nlu_result.command else None,
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

            # Add normalization metadata if any slots failed
            if failed_slots:
                # Store metadata in trace for persistence
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
            # Errores esperados de NLU
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
            # Errores inesperados
            from soni.core.errors import NLUError

            # Reuse error_user_message from outer scope if available
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

    This node:
    1. Checks if slot is already filled
    2. If not, prompts user for the slot
    3. Updates state with slot value (if provided in message)

    Args:
        state: Current dialogue state (dict or DialogueState)
        slot_name: Name of slot to collect
        context: Runtime context with configuration and dependencies.
                 Always required - provides access to config for slot validation
                 and other runtime dependencies.

    Returns:
        Dictionary with state updates
    """
    try:
        # Convert dict to DialogueState if needed
        state = _ensure_dialogue_state(state)

        # Get slot config from context

        slot_config = context.get_slot_config(slot_name)

        # Check if slot is already filled
        slot_value = state.get_slot(slot_name)
        if slot_value:
            # Slot was extracted by NLU - validate if validator configured
            if slot_config.validator:
                try:
                    is_valid = ValidatorRegistry.validate(
                        name=slot_config.validator,
                        value=slot_value,
                    )
                    if not is_valid:
                        logger.warning(
                            f"Slot '{slot_name}' value '{slot_value}' "
                            f"failed validation with '{slot_config.validator}'"
                        )
                        # Return validation error
                        return {
                            "last_response": (
                                f"Invalid value for {slot_name}. Please provide a valid value."
                            ),
                            "trace": state.trace
                            + [
                                {
                                    "event": "validation_error",
                                    "data": {
                                        "slot": slot_name,
                                        "value": slot_value,
                                        "validator": slot_config.validator,
                                    },
                                }
                            ],
                        }
                except ValueError as e:
                    logger.warning(f"Validator '{slot_config.validator}' not found: {e}")
            # Slot is valid or no validator configured
            logger.info(f"Slot '{slot_name}' already filled: {slot_value}")
            return {}

        # Get prompt for this slot
        prompt = slot_config.prompt

        # Slot not filled, need to prompt user
        response = prompt

        updates = {
            "last_response": response,
            "trace": state.trace
            + [
                {
                    "event": "slot_collection",
                    "data": {"slot": slot_name, "prompt": prompt},
                }
            ],
        }

        logger.info(f"Prompting for slot '{slot_name}': {prompt}")

        return updates

    except KeyError as e:
        # Slot not found in configuration
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
        # Expected errors in collect_slot_node - re-raise for upstream handling
        logger.error(
            f"Error in collect_slot_node: {e}",
            exc_info=True,
            extra={"slot_name": slot_name, "error_type": type(e).__name__},
        )
        raise
    except Exception as e:
        # Unexpected errors - re-raise for upstream handling
        logger.error(
            f"Unexpected error in collect_slot_node: {e}",
            exc_info=True,
            extra={"slot_name": slot_name, "error_type": type(e).__name__},
        )
        raise


def create_collect_node_factory(
    slot_name: str, context: RuntimeContext
) -> Any:  # Returns: Callable[[DialogueState | dict[str, Any]], Awaitable[dict[str, Any]]]
    """
    Create collect node factory function.

    Args:
        slot_name: Name of the slot to collect
        context: Runtime context with configuration and dependencies.
                 Always required - provides access to config for slot validation
                 and other runtime dependencies.

    Returns:
        Async node function that collects a slot value.
        Type: Callable[[DialogueState | dict[str, Any]], Awaitable[dict[str, Any]]]
        (annotated as Any due to LangGraph internals)

    Note:
        Return type is `Any` because LangGraph's node function type is
        a complex internal type. The actual return type is an async function
        that takes DialogueState | dict[str, Any] and returns dict[str, Any]
        (state updates).
    """

    async def collect_node(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
        # Convert dict to DialogueState if needed
        state = _ensure_dialogue_state(state)

        # Use context for slot collection
        return await collect_slot_node(state, slot_name, context=context)

    return collect_node


def create_action_node_factory(
    action_name: str, context: RuntimeContext
) -> Any:  # Returns: Callable[[DialogueState | dict[str, Any]], Awaitable[dict[str, Any]]]
    """
    Create action node factory function.

    Args:
        action_name: Name of the action to execute
        context: Runtime context with configuration and dependencies.
                 Always required - provides access to action handler and config.

    Returns:
        Async node function that executes an action.
        Type: Callable[[DialogueState | dict[str, Any]], Awaitable[dict[str, Any]]]
        (annotated as Any due to LangGraph internals)

    Note:
        Return type is `Any` because LangGraph's node function type is
        a complex internal type. The actual return type is an async function
        that takes DialogueState | dict[str, Any] and returns dict[str, Any]
        (state updates).
    """
    # Capture dependencies in closure
    action_handler = context.action_handler

    async def action_node_wrapper(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
        # Convert dict to DialogueState if needed
        if isinstance(state, dict):
            state = DialogueState.from_dict(state)

        # Get action config from context
        try:
            action_config = context.get_action_config(action_name)
        except KeyError as err:
            raise ValueError(f"Action '{action_name}' not found in configuration") from err

        # Collect input slots
        inputs = {}
        for input_slot in action_config.inputs:
            slot_value = state.get_slot(input_slot)
            if slot_value is None:
                raise ValueError(
                    f"Required input slot '{input_slot}' not filled for action '{action_name}'"
                )
            inputs[input_slot] = slot_value

        # Execute action using injected handler
        result = await action_handler.execute(action_name, inputs)

        # Update state with outputs
        updates: dict[str, Any] = {
            "trace": state.trace
            + [
                {
                    "event": "action_executed",
                    "data": {
                        "action": action_name,
                        "inputs": inputs,
                        "outputs": result,
                    },
                }
            ],
        }

        # Map outputs to state slots/variables
        output_slots: dict[str, Any] = {}
        for output_name in action_config.outputs:
            if output_name in result:
                output_slots[output_name] = result[output_name]

        if output_slots:
            updates["slots"] = {**state.slots, **output_slots}

        # Generate response (for MVP, simple confirmation)
        updates["last_response"] = f"Action '{action_name}' executed successfully."

        logger.info(f"Action '{action_name}' executed. Outputs: {list(result.keys())}")

        return updates

    return action_node_wrapper


# Register default node factories
@NodeFactoryRegistry.register(NodeType.UNDERSTAND)
def create_understand_factory(node: DAGNode, context: RuntimeContext) -> Any:
    """
    Factory for UNDERSTAND nodes.

    Args:
        node: DAG node (config not used for understand nodes)
        context: Runtime context with dependencies

    Returns:
        Understand node function
    """
    return create_understand_node(
        scope_manager=context.scope_manager,
        normalizer=context.normalizer,
        nlu_provider=context.du,
        context=context,
    )


@NodeFactoryRegistry.register(NodeType.COLLECT)
def create_collect_factory(node: DAGNode, context: RuntimeContext) -> Any:
    """
    Factory for COLLECT nodes.

    Args:
        node: DAG node with slot_name in config
        context: Runtime context with dependencies

    Returns:
        Collect node function
    """
    slot_name = node.config["slot_name"]
    return create_collect_node_factory(slot_name, context)


@NodeFactoryRegistry.register(NodeType.ACTION)
def create_action_factory(node: DAGNode, context: RuntimeContext) -> Any:
    """
    Factory for ACTION nodes.

    Args:
        node: DAG node with action_name in config
        context: Runtime context with dependencies

    Returns:
        Action node function
    """
    action_name = node.config["action_name"]
    return create_action_node_factory(action_name, context)
