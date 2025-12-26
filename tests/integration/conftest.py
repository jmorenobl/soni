"""Integration test configuration.

Automatically patches NLU modules with mocks at import time.
"""

import pytest

import soni.du
import soni.du.modules.extract_commands
import soni.du.modules.extract_slots
from tests.mocks import MockCommandGenerator, MockSlotExtractor


@pytest.fixture
def use_mock_nlu(monkeypatch):
    """Patch NLU modules with mocks.
    Integration tests should use this fixture.
    """
    # Patch implementations
    monkeypatch.setattr("soni.du.modules.extract_commands.CommandGenerator", MockCommandGenerator)
    monkeypatch.setattr("soni.du.modules.extract_slots.SlotExtractor", MockSlotExtractor)

    # Patch re-exports
    monkeypatch.setattr("soni.du.CommandGenerator", MockCommandGenerator)
    monkeypatch.setattr("soni.du.SlotExtractor", MockSlotExtractor)

    # Patch in runtime (it imports at top level)
    monkeypatch.setattr("soni.runtime.loop.CommandGenerator", MockCommandGenerator)
