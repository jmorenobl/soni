"""Integration test configuration.

Automatically patches NLU modules with mocks at import time.
"""

import soni.du
import soni.du.modules.extract_commands
import soni.du.modules.extract_slots
from tests.mocks import MockCommandGenerator, MockSlotExtractor

# Patch implementations
soni.du.modules.extract_commands.CommandGenerator = MockCommandGenerator  # type: ignore
soni.du.modules.extract_slots.SlotExtractor = MockSlotExtractor  # type: ignore

# Patch re-exports
soni.du.CommandGenerator = MockCommandGenerator  # type: ignore
soni.du.SlotExtractor = MockSlotExtractor  # type: ignore
