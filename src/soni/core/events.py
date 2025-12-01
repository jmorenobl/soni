"""
Event constants for Soni Framework.

These constants are used in the dialogue state trace to identify
significant events that occurred during flow execution.
"""

# Event triggered when a slot needs to be collected from the user
EVENT_SLOT_COLLECTION = "slot_collection"

# Event triggered when a slot value fails validation
EVENT_VALIDATION_ERROR = "validation_error"

# Event triggered when an action is successfully executed
EVENT_ACTION_EXECUTED = "action_executed"

# Event triggered when an error occurs
EVENT_ERROR = "error"
