"""Shared constants for dataset generation."""

# Default datetime for training examples (ISO 8601 format)
DEFAULT_EXAMPLE_DATETIME = "2024-12-11T10:00:00"

# Shared confirmation phrases (can be overridden per domain)
SHARED_CONFIRMATION_POSITIVE = [
    "Yes",
    "Correct",
    "That's right",
    "Yes, that's correct",
    "Confirm",
    "Absolutely",
    "Sure",
    "Go ahead",
]

SHARED_CONFIRMATION_NEGATIVE = [
    "No",
    "That's wrong",
    "Incorrect",
    "No, that's wrong",
    "Cancel",
    "Nope",
]

SHARED_CONFIRMATION_UNCLEAR = [
    "Maybe",
    "I'm not sure",
    "Hmm",
    "Let me think",
    "I guess so",
    "Well...",
]
