from soni.core.constants import FlowContextState, FlowState


def test_flow_state_is_strenum():
    """Test that FlowState is a StrEnum, not Literal."""
    from enum import StrEnum

    assert issubclass(FlowState, StrEnum)
    assert FlowState.IDLE == "idle"
    assert FlowState.ACTIVE == "active"


def test_flow_context_state_is_strenum():
    """Test that FlowContextState is a StrEnum."""
    from enum import StrEnum

    assert issubclass(FlowContextState, StrEnum)


def test_no_duplicate_flow_state_in_types():
    """Test that types.py doesn't define its own FlowState Literal."""
    # Check if 'FlowState' in types works as expected
    # The crucial check is that it's NOT a distinct Literal definition
    # If types.py defines 'FlowState = Literal[...]', it's NOT the same object
    # as constants.FlowState class.
    import soni.core.types as types_module
    from soni.core.constants import FlowState as ConstFlowState

    # If types.py imports from constants, this will be True
    # If types.py defines its own Literal, this will be False
    assert types_module.FlowState is ConstFlowState, (
        "FlowState in types.py should be imported from constants.py, not redefined as Literal"
    )


def test_no_duplicate_flow_context_state_in_types():
    """Test that FlowContextState is consistent."""
    import soni.core.types as types_module
    from soni.core.constants import FlowContextState as ConstFlowContextState

    assert types_module.FlowContextState is ConstFlowContextState, (
        "FlowContextState in types.py should be imported from constants.py"
    )
