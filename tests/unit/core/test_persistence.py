from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from soni.core.types import _merge_flow_slots


class MockState(TypedDict):
    flow_slots: Annotated[dict[str, dict[str, Any]], _merge_flow_slots]
    _continue: Annotated[bool, lambda x, y: y]


def test_manual_persistence():
    # Test Reducer manually
    current = {"f1": {"a": 1}}
    new = {"f1": {"b": 2}}
    merged = _merge_flow_slots(current, new)
    assert merged == {"f1": {"a": 1, "b": 2}}

    current = {}
    new = {"f1": {"a": 1}}
    merged = _merge_flow_slots(current, new)
    assert merged == {"f1": {"a": 1}}


def node_step(state):
    print(f"Step state: {state}")
    if not state.get("flow_slots"):
        return {"flow_slots": {"f1": {"a": 1}}, "_continue": True}
    return {"_continue": False}


def test_graph_persistence():
    builder = StateGraph(MockState)
    builder.add_node("step", node_step)

    def router(state):
        if state.get("_continue"):
            return "step"
        return END

    builder.set_entry_point("step")
    builder.add_conditional_edges("step", router)

    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "1"}}

    # Run 1: Returns update and continues
    result = graph.invoke({"flow_slots": {}, "_continue": False}, config=config)

    # Check intermediate not visible? Wait. invoke runs until END.
    # Our graph loops until _continue is False.
    # node_step returns _continue=False on second run (when slots exist).

    assert result["flow_slots"] == {"f1": {"a": 1}}
