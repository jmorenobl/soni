"""Shared fixtures for Soni tests.

Uses MockCommandGenerator and MockSlotExtractor for deterministic, fast tests without LLM API calls.
Two-pass architecture mocked for testing.
"""

import pytest


class MockNLUOutput:
    """Mock NLU output for deterministic tests."""

    def __init__(self, commands: list):
        self.commands = commands
        self.confidence = 1.0


class MockCommand:
    """Mock command for tests."""

    def __init__(self, cmd_dict: dict):
        self._data = cmd_dict
        self.type = cmd_dict.get("type")
        self.flow_name = cmd_dict.get("flow_name")
        self.slot = cmd_dict.get("slot")
        self.value = cmd_dict.get("value")
        self.message = cmd_dict.get("message")

    def model_dump(self) -> dict:
        return self._data


class MockCommandGenerator:
    """Deterministic mock for CommandGenerator (Pass 1: Intent Detection).

    Returns StartFlow for first flow in config if message not empty.
    """

    def __init__(self, default_flow: str | None = None):
        self.default_flow = default_flow
        self._call_count = 0

    @classmethod
    def create_with_best_model(cls) -> "MockCommandGenerator":
        return cls()

    async def acall(
        self,
        message: str,
        context,
        history: list | None = None,  # Two-pass: history parameter
    ) -> MockNLUOutput:
        """Return deterministic StartFlow command."""
        self._call_count += 1

        # 0. Debug input
        import sys

        sys.stderr.write(
            f"DEBUG_STDERR: MockCommandGenerator msg='{message}' type={type(message)}\n"
        )

        # 1. Check message content specific patterns first
        if msg := (message or "").lower():
            if msg in ("yes", "y", "confirm"):
                return MockNLUOutput(commands=[MockCommand({"type": "affirm"})])
            if msg in ("no", "n", "deny"):
                return MockNLUOutput(commands=[MockCommand({"type": "deny"})])

            if "actually" in msg and "50" in msg:
                return MockNLUOutput(
                    commands=[
                        MockCommand({"type": "correct_slot", "slot": "amount", "new_value": 50})
                    ]
                )

            if "check balance" in msg:
                return MockNLUOutput(
                    commands=[MockCommand({"type": "start_flow", "flow_name": "check_balance"})]
                )

            if "es123" in msg:
                return MockNLUOutput(
                    commands=[MockCommand({"type": "set_slot", "slot": "iban", "value": "ES123"})]
                )

            if message.isdigit():
                sys.stderr.write(f"DEBUG_STDERR: isdigit=True for {repr(message)}\n")
                # Primitive logic to guess slot based on context would be better,
                # but for these tests we might need to assume 'param' or 'amount' based on test.
                # Let's try to infer or just return a generic SetSlot that works if context known?
                # For `test_confirm_affirm_continues`, slot is `param`.
                # For `test_confirm_correction_updates_slot`, slot is `amount`.
                # We can return SetSlot for both if we guess, or key off value.
                if message == "100":
                    sys.stderr.write("DEBUG_STDERR: MATCH 100\n")
                    return MockNLUOutput(
                        commands=[
                            MockCommand({"type": "set_slot", "slot": "param", "value": 100}),
                            MockCommand({"type": "set_slot", "slot": "amount", "value": 100}),
                        ]
                    )
                if message == "200":
                    return MockNLUOutput(
                        commands=[MockCommand({"type": "set_slot", "slot": "param", "value": 200})]
                    )

            if "transfer" in msg:
                return MockNLUOutput(
                    commands=[MockCommand({"type": "start_flow", "flow_name": "transfer"})]
                )

            if "start" in msg:
                # Default start flow logic
                pass

        # 2. Fallback: Start Flow if context allows (for initial "start" messages not caught above)
        import sys

        sys.stderr.write(f"DEBUG_STDERR: MockCommandGenerator context type: {type(context)}\n")

        # Handle DialogueContext (from understand_node or execute_flow_node)
        if hasattr(context, "available_flows"):
            # Check if we're filling a slot (expected_slot is set)
            expected_slot = getattr(context, "expected_slot", None)
            if expected_slot and message:
                # Return SetSlot for the expected slot
                return MockNLUOutput(
                    commands=[
                        MockCommand({"type": "set_slot", "slot": expected_slot, "value": message})
                    ]
                )

            # Otherwise start first available flow
            if context.available_flows:
                first_flow = context.available_flows[0]
                flow_name = getattr(first_flow, "name", None) or first_flow.get("name")
                return MockNLUOutput(
                    commands=[MockCommand({"type": "start_flow", "flow_name": flow_name})]
                )

        # Handle RuntimeContext (from execute_node resume)
        # If we're here with a RuntimeContext, we're resuming from an interrupt.
        # The user message is likely a slot value, not a new intent.
        if hasattr(context, "config") and context.config.flows:
            # Check if there's an active flow in state (indicates slot-filling context)
            # For test purposes, treat plain text as slot value for 'name' slot
            if message and not message.lower().startswith(("start", "i want", "transfer")):
                # Assume it's a slot value - use 'name' as default slot
                return MockNLUOutput(
                    commands=[MockCommand({"type": "set_slot", "slot": "name", "value": message})]
                )

            # Otherwise start flow
            flow_name = list(context.config.flows.keys())[0]
            return MockNLUOutput(
                commands=[MockCommand({"type": "start_flow", "flow_name": flow_name})]
            )

        # 3. Last resort: Chitchat
        return MockNLUOutput(
            commands=[MockCommand({"type": "chitchat", "message": "I'm here to help!"})]
        )


class MockSlotExtractor:
    """Deterministic mock for SlotExtractor (Pass 2: Slot Extraction).

    Returns empty list - slot extraction happens via SetSlot commands in subsequent turns.
    """

    def __init__(self):
        self._call_count = 0

    @classmethod
    def create_with_best_model(cls) -> "MockSlotExtractor":
        return cls()

    async def acall(self, user_message: str, slot_definitions: list) -> list:
        """Return empty list (no slots extracted from initial message)."""
        self._call_count += 1
        return []  # No slots extracted


# Patch modules to use mocks
import soni.du  # noqa: E402
import soni.du.modules.extract_commands  # noqa: E402
import soni.du.modules.extract_slots  # noqa: E402

# Patch implementations
soni.du.modules.extract_commands.CommandGenerator = MockCommandGenerator  # type: ignore
soni.du.modules.extract_slots.SlotExtractor = MockSlotExtractor  # type: ignore

# Patch re-exports in package root
soni.du.CommandGenerator = MockCommandGenerator  # type: ignore
soni.du.SlotExtractor = MockSlotExtractor  # type: ignore


@pytest.fixture
def empty_dialogue_state():
    """Create an empty dialogue state for testing."""
    from soni.core.state import create_empty_state

    return create_empty_state()


@pytest.fixture
def mock_runtime():
    """Create a mock Runtime[RuntimeContext] for testing nodes."""
    from unittest.mock import AsyncMock, MagicMock

    from langgraph.runtime import Runtime

    from soni.config import SoniConfig
    from soni.runtime.context import RuntimeContext

    mock_context = MagicMock(spec=RuntimeContext)
    mock_context.flow_manager = MagicMock()
    mock_context.du = MockCommandGenerator()
    mock_context.slot_extractor = MockSlotExtractor()
    mock_context.action_handler = AsyncMock()
    mock_context.config = SoniConfig(flows={})

    runtime = Runtime(
        context=mock_context,
        store=None,
        stream_writer=lambda x: None,
        previous=None,
    )
    return runtime
