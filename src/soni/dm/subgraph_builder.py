"""Flow Subgraph Builder for Soni v3.0.

Builds a StateGraph for a single flow from YAML definition.
Each step in the flow becomes a node in the subgraph.

This creates the actual subgraph that gets composed into
the OrchestratorGraph.
"""

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from soni.core.config import SoniConfig, StepConfig
from soni.core.constants import FlowState
from soni.core.state import get_all_slots, get_flow_config
from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


def build_flow_subgraph(
    flow_name: str,
    config: SoniConfig,
    context: RuntimeContext,
) -> StateGraph:
    """Build a StateGraph for a single flow.
    
    Creates nodes for each step in the flow:
    - collect steps: prompt for slot, wait for input
    - action steps: execute action handler
    - confirm steps: show confirmation, wait for response
    - say steps: show message, continue
    
    Args:
        flow_name: Name of flow to build
        config: Soni configuration
        context: Runtime context
        
    Returns:
        Uncompiled StateGraph for the flow
    """
    if flow_name not in config.flows:
        raise KeyError(f"Flow '{flow_name}' not found in configuration")
    
    flow_config = config.flows[flow_name]
    steps = flow_config.steps_or_process
    
    logger.info(f"Building subgraph for flow '{flow_name}' with {len(steps)} steps")
    
    builder = StateGraph(DialogueState)
    
    if not steps:
        # Empty flow - just pass through
        async def empty_flow(state: DialogueState) -> dict[str, Any]:
            return {"flow_state": FlowState.DONE}
        
        builder.add_node("empty", empty_flow)
        builder.add_edge(START, "empty")
        builder.add_edge("empty", END)
        return builder
    
    # Create node for each step
    step_names = []
    for i, step in enumerate(steps):
        step_name = step.step or f"step_{i}"
        step_names.append(step_name)
        
        # Create node function for this step
        node_fn = _create_step_node(step, context)
        builder.add_node(step_name, node_fn)
    
    # Add edges: linear by default
    # START → first step
    builder.add_edge(START, step_names[0])
    
    # Each step → next step (with conditional for waiting)
    for i, step_name in enumerate(step_names):
        step = steps[i]
        
        if i < len(step_names) - 1:
            next_step = step_names[i + 1]
        else:
            next_step = None  # Last step
        
        # Steps that need user input end the subgraph turn
        if step.type in ("collect", "confirm"):
            # Collect/confirm: route based on whether slot is filled
            def make_router(current_step: StepConfig, next_name: str | None):
                async def route(state: DialogueState) -> str:
                    if state.get("flow_state") == FlowState.WAITING_INPUT:
                        return END  # Pause for user input
                    if next_name:
                        return next_name
                    return END
                return route
            
            router = make_router(step, next_step)
            routing = {END: END}
            if next_step:
                routing[next_step] = next_step
            
            builder.add_conditional_edges(step_name, router, routing)
        else:
            # Non-blocking steps: always continue
            if next_step:
                builder.add_edge(step_name, next_step)
            else:
                builder.add_edge(step_name, END)
    
    return builder


def _create_step_node(
    step: StepConfig,
    context: RuntimeContext,
) -> Any:
    """Create a node function for a step.
    
    Returns an async function that processes this step.
    """
    step_type = step.type
    step_name = step.step
    
    if step_type == "collect":
        slot_name = step.slot
        # Use message field if available, otherwise generate default
        prompt = step.message or f"Please provide {slot_name}"
        
        async def collect_node(state: DialogueState) -> dict[str, Any]:
            slots = get_all_slots(state)
            
            if slot_name and slots.get(slot_name):
                # Slot filled, continue
                logger.debug(f"Slot {slot_name} already filled, continuing")
                return {"flow_state": FlowState.RUNNING}
            else:
                # Need user input
                return {
                    "flow_state": FlowState.WAITING_INPUT,
                    "waiting_for_slot": slot_name,
                    "response": prompt,
                }
        
        collect_node.__name__ = f"collect_{step_name}"
        return collect_node
    
    elif step_type == "action":
        action_name = step.call
        
        async def action_node(state: DialogueState) -> dict[str, Any]:
            action_handler = context["action_handler"]
            flow_manager = context["flow_manager"]
            slots = get_all_slots(state)
            
            try:
                result = await action_handler.execute(action_name, slots)
                logger.info(f"Action {action_name} completed")
                
                # Store outputs in slots
                for key, value in result.items():
                    flow_manager.set_slot(state, key, value)
                
                return {
                    "flow_slots": state["flow_slots"],
                    "action_result": result,
                    "flow_state": FlowState.RUNNING,
                }
            except Exception as e:
                logger.error(f"Action {action_name} failed: {e}")
                return {
                    "flow_state": FlowState.DONE,
                    "response": f"Error: {e}",
                }
        
        action_node.__name__ = f"action_{step_name}"
        return action_node
    
    elif step_type == "confirm":
        message = step.message or "Is this correct?"
        
        async def confirm_node(state: DialogueState) -> dict[str, Any]:
            slots = get_all_slots(state)
            
            # Interpolate message with slots
            try:
                formatted = message.format(**slots)
            except KeyError:
                formatted = message
            
            return {
                "flow_state": FlowState.WAITING_INPUT,
                "response": formatted,
            }
        
        confirm_node.__name__ = f"confirm_{step_name}"
        return confirm_node
    
    elif step_type in ("say", "respond"):
        message = step.message or ""
        
        async def say_node(state: DialogueState) -> dict[str, Any]:
            slots = get_all_slots(state)
            
            try:
                formatted = message.format(**slots)
            except KeyError:
                formatted = message
            
            return {
                "response": formatted,
                "flow_state": FlowState.RUNNING,
            }
        
        say_node.__name__ = f"say_{step_name}"
        return say_node
    
    else:
        # Unknown step type - pass through
        async def passthrough_node(state: DialogueState) -> dict[str, Any]:
            logger.warning(f"Unknown step type: {step_type}")
            return {"flow_state": FlowState.RUNNING}
        
        passthrough_node.__name__ = f"unknown_{step_name}"
        return passthrough_node
