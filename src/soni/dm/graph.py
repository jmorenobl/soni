"""LangGraph graph builder and nodes for Soni Framework"""

import logging
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from soni.core.config import SoniConfig
from soni.core.errors import NLUError
from soni.core.state import DialogueState
from soni.du.modules import NLUResult, SoniDU

logger = logging.getLogger(__name__)


def _ensure_dialogue_state(
    state: DialogueState | dict[str, Any],
) -> DialogueState:
    """
    Ensure state is a DialogueState instance.

    Args:
        state: State as dict or DialogueState

    Returns:
        DialogueState instance
    """
    if isinstance(state, dict):
        return DialogueState.from_dict(state)
    return state


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
            [f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in state.messages[:-1]]
        )

        # Get available actions from config
        # For MVP, we use all actions. Scoping will be added in Hito 10
        if hasattr(state, "config"):
            available_actions = list(state.config.actions.keys())
        else:
            available_actions = []

        # Initialize SoniDU (for MVP, create new instance each time)
        # In future, this will be injected via builder
        du = SoniDU()

        # Call NLU
        nlu_result: NLUResult = await du.predict(
            user_message=user_message,
            dialogue_history=dialogue_history,
            current_slots=state.slots,
            available_actions=available_actions,
            current_flow=state.current_flow,
        )

        # Update state with NLU results
        updated_slots = state.slots.copy()
        updated_slots.update(nlu_result.slots)

        updates = {
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

        logger.info(
            f"NLU result: command={nlu_result.command}, "
            f"confidence={nlu_result.confidence:.2f}, "
            f"slots={nlu_result.slots}"
        )

        return updates

    except Exception as e:
        logger.error(f"Error in understand_node: {e}", exc_info=True)
        error_user_message: str | None = None
        if "user_messages" in locals() and user_messages:
            error_user_message = user_messages[-1]
        raise NLUError(
            f"Failed to understand user message: {e}",
            context={"user_message": error_user_message},
        ) from e


async def collect_slot_node(
    state: DialogueState | dict[str, Any], slot_name: str
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

    Returns:
        Dictionary with state updates
    """
    try:
        # Convert dict to DialogueState if needed
        state = _ensure_dialogue_state(state)

        # Get slot config
        if not hasattr(state, "config") or slot_name not in state.config.slots:
            raise ValueError(f"Slot '{slot_name}' not found in configuration")

        slot_config = state.config.slots[slot_name]  # type: ignore[attr-defined]

        # Check if slot is already filled
        if state.has_slot(slot_name) and state.get_slot(slot_name):
            logger.info(f"Slot '{slot_name}' already filled: {state.get_slot(slot_name)}")
            return {}

        # Get prompt for this slot
        prompt = slot_config.prompt

        # Check if user provided the value in the last message
        # For MVP, we assume the NLU already extracted it
        # In future, we might need to re-parse or ask explicitly
        slot_value = state.get_slot(slot_name)

        if slot_value:
            # Slot was extracted by NLU
            logger.info(f"Slot '{slot_name}' collected: {slot_value}")
            return {}

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

    except Exception as e:
        logger.error(f"Error in collect_slot_node: {e}", exc_info=True)
        # Get trace safely (state might not be converted if error occurred early)
        try:
            state_obj = _ensure_dialogue_state(state)
            trace = state_obj.trace
        except Exception:
            if isinstance(state, dict):
                trace = state.get("trace", [])
            else:
                trace = getattr(state, "trace", [])
        return {
            "last_response": f"I encountered an error collecting {slot_name}. Please try again.",
            "trace": trace
            + [
                {
                    "event": "error",
                    "data": {"error": str(e), "slot": slot_name},
                }
            ],
        }


async def action_node(state: DialogueState | dict[str, Any], action_name: str) -> dict[str, Any]:
    """
    Execute an external action.

    This node:
    1. Gets action config
    2. Collects required input slots
    3. Calls ActionHandler to execute action
    4. Updates state with action outputs

    Args:
        state: Current dialogue state (dict or DialogueState)
        action_name: Name of action to execute

    Returns:
        Dictionary with state updates
    """
    try:
        # Convert dict to DialogueState if needed
        state = _ensure_dialogue_state(state)

        # Get action config
        if not hasattr(state, "config") or action_name not in state.config.actions:
            raise ValueError(f"Action '{action_name}' not found in configuration")

        action_config = state.config.actions[action_name]  # type: ignore[attr-defined]

        # Collect input slots
        inputs = {}
        for input_slot in action_config.inputs:
            slot_value = state.get_slot(input_slot)
            if slot_value is None:
                raise ValueError(
                    f"Required input slot '{input_slot}' not filled for action '{action_name}'"
                )
            inputs[input_slot] = slot_value

        # Execute action using ActionHandler
        # ActionHandler will be implemented in Task 008
        # For now, we import it
        from soni.actions.base import ActionHandler

        handler = ActionHandler(state.config)  # type: ignore[attr-defined]
        result = await handler.execute(action_name, inputs)

        # Update state with outputs
        # For MVP, we assume outputs match the action_config.outputs
        updates = {
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
        # For MVP, we store outputs directly in slots
        # In future, map_outputs will be handled here
        output_slots: dict[str, Any] = {}
        for output_name in action_config.outputs:
            if output_name in result:
                output_slots[output_name] = result[output_name]
        if output_slots:
            updates["slots"] = output_slots  # type: ignore[assignment]

        logger.info(f"Action '{action_name}' executed successfully")

        return updates

    except Exception as e:
        logger.error(f"Error in action_node: {e}", exc_info=True)
        # Get trace safely (state might not be converted if error occurred early)
        try:
            state_obj = _ensure_dialogue_state(state)
            trace = state_obj.trace
        except Exception:
            if isinstance(state, dict):
                trace = state.get("trace", [])
            else:
                trace = getattr(state, "trace", [])
        return {
            "last_response": f"I encountered an error executing {action_name}. Please try again.",
            "trace": trace
            + [
                {
                    "event": "error",
                    "data": {"error": str(e), "action": action_name},
                }
            ],
        }


class SoniGraphBuilder:
    """
    Builds LangGraph StateGraph from Soni configuration.

    This builder creates graphs for linear flows (MVP only).
    Future versions will support branches and jumps.
    """

    def __init__(self, config: SoniConfig):
        """
        Initialize the graph builder.

        Args:
            config: Validated Soni configuration
        """
        self.config = config
        self._checkpointer_cm: Any = None  # Context manager for proper cleanup
        self.checkpointer = self._create_checkpointer()

    def cleanup(self) -> None:
        """
        Cleanup resources, especially the checkpointer context manager.

        Should be called when the builder is no longer needed to ensure
        proper resource cleanup (file descriptors, database connections, etc.).
        """
        if self._checkpointer_cm is not None:
            try:
                self._checkpointer_cm.__exit__(None, None, None)
                logger.info("Checkpointer context manager closed successfully")
            except Exception as e:
                logger.warning(f"Error closing checkpointer context manager: {e}")
            finally:
                self._checkpointer_cm = None
                self.checkpointer = None

    def __del__(self) -> None:
        """
        Destructor to ensure cleanup is called when object is garbage collected.

        Note: Relying on __del__ is not ideal, but provides a safety net.
        Explicit cleanup() calls are preferred.
        """
        self.cleanup()

    def _create_checkpointer(self) -> Any:
        """
        Create checkpointer for state persistence.

        Returns:
            SqliteSaver instance or None if persistence is disabled

        Note:
            SqliteSaver.from_conn_string() returns a context manager.
            We enter it and store the context manager for proper cleanup.
        """
        persistence = self.config.settings.persistence

        if persistence.backend == "sqlite":
            try:
                # from_conn_string returns a context manager
                self._checkpointer_cm = SqliteSaver.from_conn_string(persistence.path)
                # Enter the context manager and return the checkpointer
                return self._checkpointer_cm.__enter__()
            except Exception as e:
                logger.warning(
                    f"Failed to create SQLite checkpointer: {e}. Using in-memory state only."
                )
                self._checkpointer_cm = None
                return None
        elif persistence.backend == "none":
            return None
        else:
            logger.warning(
                f"Unsupported persistence backend: {persistence.backend}. "
                "Using in-memory state only."
            )
            return None

    def build_manual(self, flow_name: str) -> Any:
        """
        Build a linear graph manually from flow configuration.

        Args:
            flow_name: Name of the flow to build

        Returns:
            Compiled StateGraph ready for execution

        Raises:
            ValueError: If flow_name is not found in config
        """
        if flow_name not in self.config.flows:
            raise ValueError(f"Flow '{flow_name}' not found in configuration")

        flow = self.config.flows[flow_name]
        logger.info(f"Building graph for flow '{flow_name}' with {len(flow.steps)} steps")

        graph = StateGraph(DialogueState)

        # Validate that all referenced slots and actions exist
        self._validate_flow(flow)

        # Add nodes for each step
        # Note: Node implementations will be in Task 007
        # For now, we create placeholder nodes
        previous_node = START

        for step in flow.steps:
            node_name = step.step

            if step.type == "collect":
                if not step.slot:
                    raise ValueError(f"Step '{node_name}' of type 'collect' must specify a 'slot'")
                # Validate slot exists
                if step.slot not in self.config.slots:
                    raise ValueError(
                        f"Step '{node_name}' references slot '{step.slot}' "
                        "which is not defined in configuration"
                    )
                # Collect slot node
                graph.add_node(
                    node_name,
                    self._create_collect_node(step.slot),
                )
            elif step.type == "action":
                if not step.call:
                    raise ValueError(f"Step '{node_name}' of type 'action' must specify a 'call'")
                # Validate action exists
                if step.call not in self.config.actions:
                    raise ValueError(
                        f"Step '{node_name}' references action '{step.call}' "
                        "which is not defined in configuration"
                    )
                # Action node
                graph.add_node(
                    node_name,
                    self._create_action_node(step.call),
                )
            else:
                raise ValueError(f"Unsupported step type: {step.type}")

            # Connect previous node to current node
            if previous_node == START:
                graph.add_edge(START, node_name)
            else:
                graph.add_edge(previous_node, node_name)

            previous_node = node_name

        # Connect last node to END
        graph.add_edge(previous_node, END)

        logger.info(f"Graph built successfully with {len(flow.steps)} nodes")

        # Compile graph with checkpointer
        if self.checkpointer:
            return graph.compile(checkpointer=self.checkpointer)
        else:
            return graph.compile()

    def _validate_flow(self, flow: Any) -> None:
        """
        Validate that all referenced slots and actions exist in config.

        Args:
            flow: Flow configuration to validate

        Raises:
            ValueError: If validation fails
        """
        for step in flow.steps:
            if step.type == "collect" and step.slot:
                if step.slot not in self.config.slots:
                    raise ValueError(f"Flow references slot '{step.slot}' which is not defined")
            elif step.type == "action" and step.call:
                if step.call not in self.config.actions:
                    raise ValueError(f"Flow references action '{step.call}' which is not defined")

    def _create_collect_node(self, slot_name: str):
        """
        Create a collect slot node.

        Args:
            slot_name: Name of slot to collect

        Returns:
            Node function
        """

        async def collect_node(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
            # Convert dict to DialogueState if needed
            state = _ensure_dialogue_state(state)

            # Inject config into state for node access
            # Note: This is a workaround for MVP. Better approach in future
            if not hasattr(state, "config"):
                state.config = self.config  # type: ignore[attr-defined]
            return await collect_slot_node(state, slot_name)

        return collect_node

    def _create_action_node(self, action_name: str):
        """
        Create an action node.

        Args:
            action_name: Name of action to execute

        Returns:
            Node function
        """

        async def action_node_wrapper(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
            # Convert dict to DialogueState if needed
            if isinstance(state, dict):
                state = DialogueState.from_dict(state)

            # Inject config into state for node access
            if not hasattr(state, "config"):
                state.config = self.config  # type: ignore[attr-defined]
            return await action_node(state, action_name)

        return action_node_wrapper
