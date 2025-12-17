"""Integration tests for auto-resume functionality."""

import pytest
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from soni.actions.handler import ActionHandler
from soni.actions.registry import ActionRegistry
from soni.core.config import SoniConfig
from soni.core.state import create_empty_dialogue_state
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.builder import build_orchestrator
from soni.du.modules import SoniDU
from soni.flow.manager import FlowManager


@pytest.fixture
def mock_du():
    from unittest.mock import AsyncMock

    mock = AsyncMock(spec=SoniDU)
    # Default response structure
    mock.acall.return_value = type("NLUOutput", (), {"commands": []})
    return mock


@pytest.mark.asyncio
async def test_auto_resume_flow(mock_du):
    """Test that interrupting a flow correctly resumes the parent flow."""
    # 1. Setup
    config = SoniConfig.from_yaml("examples/banking/domain")

    # Setup context
    fm = FlowManager()
    registry = ActionRegistry()
    registry.clear()  # Ensure clean state

    # Register mock actions needed
    @registry.register("get_balance")
    def get_balance(account_type: str):
        return {"balance": "12000.00", "currency": "USD"}

    @registry.register("format_balance_message")
    def format_balance_message(balance: str, currency: str):
        return {"message": f"Balance is {balance} {currency}"}

    handler = ActionHandler(registry)

    # Setup mock NLU to drive the conversation
    # Trace:
    # 1. "transfer money" -> StartFlow(transfer)
    # 2. "my mom" -> SetSlot(beneficiary_name=my mom)
    # 3. "check balance" -> StartFlow(check_balance)
    # 4. "savings" -> SetSlot(account_type=savings)
    # ... Auto-resume ...
    # 5. "ES123..." -> SetSlot(iban=...) (For the RESUMED flow)

    # We mock aforward responses sequentially
    from soni.core.commands import SetSlot, StartFlow

    # Response 1: Start Transfer
    mock_du.acall.side_effect = [
        # Turn 1: transfer money
        type("NLUOutput", (), {"commands": [StartFlow(flow_name="transfer_funds")]}),
        # Turn 2: my mom
        type("NLUOutput", (), {"commands": [SetSlot(slot="beneficiary_name", value="my mom")]}),
        # Turn 3: check balance (Interruption)
        type("NLUOutput", (), {"commands": [StartFlow(flow_name="check_balance")]}),
        # Turn 4: savings
        type("NLUOutput", (), {"commands": [SetSlot(slot="account_type", value="savings")]}),
        # Turn 5: IBAN (Resumed transfer)
        type(
            "NLUOutput", (), {"commands": [SetSlot(slot="iban", value="ES9121000418450200051332")]}
        ),
    ]

    # Build graph
    graph = build_orchestrator(config)

    # 2. Execution

    # Turn 1
    state = create_empty_dialogue_state()
    state["user_message"] = "transfer money"
    state["messages"] = [HumanMessage(content="transfer money")]

    # Context injection
    ctx = RuntimeContext(config=config, flow_manager=fm, action_handler=handler, du=mock_du)
    run_config = {"configurable": {"runtime_context": ctx}}

    result = await graph.ainvoke(state, config=run_config)
    assert result["flow_stack"][0]["flow_name"] == "transfer_funds"
    assert result["waiting_for_slot"] == "beneficiary_name"  # Asking beneficiary

    # Turn 2: my mom
    state = result
    state["user_message"] = "my mom"
    result = await graph.ainvoke(state, config=run_config)
    # Should be asking IBAN (next slot in transfer_funds flow)
    assert result["flow_stack"][0]["flow_name"] == "transfer_funds"
    assert result["waiting_for_slot"] == "iban"

    # Turn 3: check balance (Interrupt)
    state = result
    state["user_message"] = "check balance"
    result = await graph.ainvoke(state, config=run_config)
    # New flow on top
    assert len(result["flow_stack"]) == 2
    assert result["flow_stack"][1]["flow_name"] == "check_balance"
    assert result["waiting_for_slot"] == "account_type"

    # Turn 4: savings -> Should complete balance AND resume transfer
    state = result
    state["user_message"] = "savings"
    result = await graph.ainvoke(state, config=run_config)

    # Check Auto-Resume
    # 1. Stack should be 1 (check_balance popped)
    assert len(result["flow_stack"]) == 1
    assert result["flow_stack"][0]["flow_name"] == "transfer_funds"

    # 2. Should be asking for 'iban' (resumed state - next slot after beneficiary_name)
    assert result["waiting_for_slot"] == "iban"

    # 3. Should have generated balance message
    # messages list should contain AIMessage with balance
    last_msgs = result["messages"][-3:]  # check last few
    assert any("balance" in str(m.content).lower() for m in last_msgs)

    # Success!
