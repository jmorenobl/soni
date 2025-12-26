from typing import Any

from soni.core.commands import (
    AffirmConfirmation,
    CancelFlow,
    ChitChat,
    Command,
    CorrectSlot,
    DenyConfirmation,
    SetSlot,
    StartFlow,
)


class MockNLUOutput:
    """Mock NLU output for deterministic tests."""

    def __init__(self, commands: list[Command]):
        self.commands = commands
        self.confidence = 1.0


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
        context: Any,
        history: list | None = None,
    ) -> MockNLUOutput:
        """Return deterministic commands."""
        self._call_count += 1
        msg = (message or "").lower()

        if msg in ("yes", "y", "confirm"):
            return MockNLUOutput(commands=[AffirmConfirmation()])
        if msg in ("no", "n", "deny"):
            return MockNLUOutput(commands=[DenyConfirmation()])

        if "actually" in msg and "50" in msg:
            return MockNLUOutput(commands=[CorrectSlot(slot="amount", new_value=50)])

        if "check balance" in msg:
            return MockNLUOutput(commands=[StartFlow(flow_name="check_balance")])

        if "es123" in msg:
            return MockNLUOutput(commands=[SetSlot(slot="iban", value="ES123")])

        if message.isdigit():
            if message == "100":
                return MockNLUOutput(
                    commands=[
                        SetSlot(slot="param", value=100),
                        SetSlot(slot="amount", value=100),
                    ]
                )
            if message == "200":
                return MockNLUOutput(commands=[SetSlot(slot="param", value=200)])

        if "transfer" in msg:
            return MockNLUOutput(commands=[StartFlow(flow_name="transfer")])

        # Handle DialogueContext
        if hasattr(context, "available_flows"):
            expected_slot = getattr(context, "expected_slot", None)
            if expected_slot and message:
                return MockNLUOutput(commands=[SetSlot(slot=expected_slot, value=message)])

            if context.available_flows:
                first_flow = context.available_flows[0]
                flow_name = getattr(first_flow, "name", None) or first_flow.get("name")
                return MockNLUOutput(commands=[StartFlow(flow_name=flow_name)])

        # Handle RuntimeContext
        if hasattr(context, "config") and context.config.flows:
            if message and not message.lower().startswith(("start", "i want", "transfer")):
                return MockNLUOutput(commands=[SetSlot(slot="name", value=message)])

            flow_name = list(context.config.flows.keys())[0]
            return MockNLUOutput(commands=[StartFlow(flow_name=flow_name)])

        return MockNLUOutput(commands=[ChitChat(message="I'm here to help!")])


class MockSlotExtractor:
    """Deterministic mock for SlotExtractor (Pass 2: Slot Extraction).

    Returns empty list - slot extraction happens via SetSlot commands in subsequent turns.
    """

    def __init__(self, *args, **kwargs):
        self._call_count = 0

    @classmethod
    def create_with_best_model(cls) -> "MockSlotExtractor":
        return cls()

    async def acall(self, user_message: str, slot_definitions: list) -> list:
        """Return empty list (no slots extracted from initial message)."""
        self._call_count += 1
        return []  # No slots extracted

    async def aforward(self, user_message: str, slot_definitions: list) -> list:
        """Mock aforward for consistency with real class."""
        return await self.acall(user_message, slot_definitions)
