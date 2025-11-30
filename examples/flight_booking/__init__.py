"""Flight booking example for Soni Framework"""

# Import handlers to auto-register actions with ActionRegistry
# This ensures actions are available when the runtime starts
# Using relative import to avoid mypy module resolution issues
from . import handlers  # noqa: F401, type: ignore[import]
