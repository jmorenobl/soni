"""Pattern generators for conversational patterns.

Each pattern generator creates training examples for a specific MessageType.
"""

from soni.dataset.patterns.cancellation import CancellationGenerator
from soni.dataset.patterns.clarification import ClarificationGenerator
from soni.dataset.patterns.confirmation import ConfirmationGenerator
from soni.dataset.patterns.continuation import ContinuationGenerator
from soni.dataset.patterns.correction import CorrectionGenerator
from soni.dataset.patterns.digression import DigressionGenerator
from soni.dataset.patterns.interruption import InterruptionGenerator
from soni.dataset.patterns.modification import ModificationGenerator
from soni.dataset.patterns.slot_value import SlotValueGenerator

# Registry of all pattern generators
ALL_PATTERN_GENERATORS = {
    "slot_value": SlotValueGenerator(),
    "correction": CorrectionGenerator(),
    "modification": ModificationGenerator(),
    "interruption": InterruptionGenerator(),
    "cancellation": CancellationGenerator(),
    "continuation": ContinuationGenerator(),
    "digression": DigressionGenerator(),
    "clarification": ClarificationGenerator(),
    "confirmation": ConfirmationGenerator(),
}

__all__ = [
    "SlotValueGenerator",
    "CorrectionGenerator",
    "ModificationGenerator",
    "InterruptionGenerator",
    "CancellationGenerator",
    "ContinuationGenerator",
    "DigressionGenerator",
    "ClarificationGenerator",
    "ConfirmationGenerator",
    "ALL_PATTERN_GENERATORS",
]
