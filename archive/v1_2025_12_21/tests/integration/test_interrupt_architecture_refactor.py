from unittest.mock import AsyncMock, MagicMock

import pytest
from soni.core.commands import SetSlot, StartFlow
from soni.du.models import NLUOutput

from soni.config import CollectStepConfig, FlowConfig, SayStepConfig, SoniConfig
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_interrupt_architecture_flow():
    """Verify that the new execute_node logic correctly handles interrupts and subgraphs."""

    # 1. Setup Config with a simple flow
    flow_config = FlowConfig(
        description="A simple test flow",
        steps=[
            CollectStepConfig(step="ask_name", slot="user_name", message="What is your name?"),
            SayStepConfig(step="greet", message="Hello, {user_name}!"),
        ],
    )

    config = SoniConfig(flows={"test_flow": flow_config})

    # 2. Mock NLU Service
    # We need to mock the DU protocol or injected NLU service
    # Since RuntimeLoop creates NLUService internally in process_message using self.du and self.slot_extractor,
    # we should mock self.du

    mock_du = MagicMock()
    mock_du.acall = AsyncMock()

    # First call: Intent detection (StartFlow)
    # Second call: Slot extraction (SetSlot)
    # Actually, process_message calls NLU.
    # We will simulate the interaction sequence.

    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()

    # Mock slot_extractor to prevent it from calling DSPy
    mock_slot_extractor = MagicMock()
    mock_slot_extractor.acall = AsyncMock(return_value=[])  # Return empty list (no slot commands)

    async with RuntimeLoop(
        config, checkpointer=checkpointer, du=mock_du, slot_extractor=mock_slot_extractor
    ) as runtime:
        # --- TURN 1: User says "start test" ---
        # Mock NLU to return StartFlow
        mock_du.acall.return_value = NLUOutput(commands=[StartFlow(flow_name="test_flow")])

        # We expect the system to run:
        # 1. understand_node -> StartFlow
        # 2. execute_node -> StartFlow consumed -> push flow -> invoke subgraph
        # 3. Subgraph -> collect_node -> _need_input=True -> Command(goto=END)
        # 4. execute_node -> sees need_input -> interrupt() -> returns prompt

        response = await runtime.process_message("start test", user_id="test_user_1")

        assert "What is your name?" in response

        # Verify state
        state = await runtime.get_state("test_user_1")
        assert state["_need_input"] is True
        assert state["_pending_prompt"]["slot"] == "user_name"
        assert len(state["flow_stack"]) == 1
        assert state["flow_stack"][0]["flow_name"] == "test_flow"

        # --- TURN 2: User says "Alice" ---
        # Mock NLU to return SetSlot
        # Note: RuntimeLoop creates NLUService which uses DU.
        # We mock DU to return basic NLUOutput, NLUService handles slot extraction if needed.
        # But simpler: just mock DU to return the command directly for this test.
        mock_du.acall.return_value = NLUOutput(commands=[SetSlot(slot="user_name", value="Alice")])

        response = await runtime.process_message("Alice", user_id="test_user_1")

        # We expect:
        # 1. RuntimeLoop -> Resume with input "Alice"
        # 2. NLU (NLUService) -> returns SetSlot("user_name", "Alice")
        # 3. Graph resumes execute_node with Command(resume={commands: [SetSlot...]})
        # 4. execute_node loop -> injects commands -> invokes subgraph
        # 5. Subgraph -> collect_node -> checks command -> fills slot -> continues
        # 6. Subgraph -> say_node -> "Hello, Alice!" -> finish
        # 7. Subgraph finishes -> execute_node sees completion -> routes to Respond

        assert "Hello, Alice!" in response

        # Verify state
        state = await runtime.get_state("test_user_1")
        assert state["_need_input"] is False
        # Slot should be filled in MAIN state (propagated from subgraph)
        # Accessing flow slots via flow_manager or raw state
        # state["flow_slots"] is dict[flow_id, dict]
        flow_id = state["flow_stack"][0]["flow_id"]
        slots = state["flow_slots"].get(flow_id, {})
        assert slots.get("user_name") == "Alice"
