"""Flight booking example for Soni Framework"""

# Import handlers to register actions via @ActionRegistry.register() decorators.
# This follows the convention: if using custom module names (handlers.py instead of actions.py),
# import them in __init__.py so they're registered when the package is imported.
# The RuntimeLoop auto-discovers actions.py, but for handlers.py we use explicit import in __init__.py.
from . import handlers  # noqa: F401, type: ignore[import]
