"""Utterance templates for natural language variation.

This module provides template patterns for generating diverse user utterances
across all conversational patterns. Templates use {placeholder} syntax for
value substitution.
"""

# =============================================================================
# SLOT_VALUE Templates
# =============================================================================

SLOT_VALUE_TEMPLATES = {
    "direct": [
        "{value}",
        "{value}, please",
        "It's {value}",
    ],
    "informal": [
        "Hmm, {value}",
        "I'd say {value}",
        "Maybe {value}?",
        "Let's go with {value}",
    ],
    "verbose": [
        "I want {value}",
        "I'm thinking {value}",
        "How about {value}",
        "{value} sounds good",
    ],
}

# =============================================================================
# CORRECTION Templates
# =============================================================================

CORRECTION_TEMPLATES = [
    "No, I meant {new_value}",
    "Actually, {new_value}",
    "Sorry, I said it wrong - {new_value}",
    "Not {old_value}, {new_value}",
    "Wait, it's {new_value}",
    "I said {new_value}, not {old_value}",
    "Actually, I meant {new_value} not {old_value}",
]

# =============================================================================
# MODIFICATION Templates
# =============================================================================

MODIFICATION_TEMPLATES = [
    "Change the {slot} to {new_value}",
    "Can I modify the {slot}?",
    "I want to change the {slot}",
    "Update the {slot} to {new_value}",
    "No, change the {slot}",
    "Let me change the {slot}",
]

# =============================================================================
# CONFIRMATION Phrases
# =============================================================================

CONFIRMATION_POSITIVE = [
    "Yes",
    "Yeah",
    "Yep",
    "Sure",
    "Correct",
    "That's right",
    "Yes, that looks good",
    "Confirmed",
    "Perfect",
    "Go ahead",
    "Sounds good",
    "Absolutely",
    "Definitely",
    "Of course",
]

CONFIRMATION_NEGATIVE = [
    "No",
    "Nope",
    "That's wrong",
    "Incorrect",
    "Not quite",
    "No, that's not right",
    "Wrong",
    "Nah",
    "That's not correct",
]

CONFIRMATION_UNCLEAR = [
    "Maybe",
    "I think so",
    "Hmm",
    "I'm not sure",
    "Probably",
    "I guess",
    "Let me think",
    "Perhaps",
    "Kind of",
    "um...",
    "uh...",
    "well...",
    "I don't know",
    "Can you repeat that?",
    "What were the details again?",
    "If you say so",
    "hmm, I'm not sure",
]

# =============================================================================
# CANCELLATION Templates
# =============================================================================

CANCELLATION_TEMPLATES = [
    "Cancel",
    "Cancel this",
    "Never mind",
    "Forget it",
    "Stop",
    "I changed my mind",
    "Abort",
    "Don't do it",
    "Actually, cancel",
    "Nvm",
    "Drop it",
    "Leave it",
    "No wait, stop",
]

# =============================================================================
# DIGRESSION Templates
# =============================================================================

DIGRESSION_TEMPLATES = {
    "question": [
        "What {topic}?",
        "Can you tell me about {topic}?",
        "I have a question about {topic}",
    ],
    "inquiry": [
        "Do you have {feature}?",
        "Is there {feature}?",
        "What about {feature}?",
    ],
    "general": [
        "By the way, {topic}?",
        "Quick question: {topic}?",
    ],
}

# =============================================================================
# INTERRUPTION Prefixes
# =============================================================================

INTERRUPTION_PREFIXES = [
    "Actually, ",
    "Wait, ",
    "Hold on, ",
    "Before that, ",
    "First, ",
    "",  # No prefix
]

# =============================================================================
# CLARIFICATION Templates
# =============================================================================

CLARIFICATION_TEMPLATES = [
    "Why do you need that?",
    "What's this for?",
    "Why is that necessary?",
    "Why do you need my {slot}?",
    "What do you use my {slot} for?",
    "Is my {slot} required?",
]
