"""Flow integration tests configuration.

Automatically patches NLU modules with mocks for flow tests.
"""

import pytest

from tests.mocks import MockCommandGenerator, MockSlotExtractor


@pytest.fixture(autouse=True)
def use_mock_nlu(monkeypatch):
    """Patch NLU modules with mocks for flow integration tests.

    This fixture automatically applies to all tests in the flows/ directory.
    Tests that need real NLU (like optimizer tests) should be in other directories.
    """
    # Patch implementations
    monkeypatch.setattr("soni.du.modules.extract_commands.CommandGenerator", MockCommandGenerator)
    monkeypatch.setattr("soni.du.modules.extract_slots.SlotExtractor", MockSlotExtractor)

    # Patch re-exports
    monkeypatch.setattr("soni.du.CommandGenerator", MockCommandGenerator)
    monkeypatch.setattr("soni.du.SlotExtractor", MockSlotExtractor)

    # Patch in runtime (it imports at top level)
    monkeypatch.setattr("soni.runtime.loop.CommandGenerator", MockCommandGenerator)
