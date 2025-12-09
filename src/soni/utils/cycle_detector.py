"""Cycle detector for preventing infinite state transition loops."""

import logging
from collections import deque

logger = logging.getLogger(__name__)


class StateTransitionCycleDetector:
    """Detects cycles in state transitions to prevent infinite loops.

    Tracks recent state transitions and detects when the same cycle repeats.
    Example: understand → handle_confirmation → understand → handle_confirmation → ...
    """

    def __init__(self, max_history: int = 10, cycle_threshold: int = 3):
        """Initialize cycle detector.

        Args:
            max_history: Maximum number of transitions to track
            cycle_threshold: Number of times a cycle must repeat to trigger detection
        """
        self.max_history = max_history
        self.cycle_threshold = cycle_threshold
        self.transition_history: deque[tuple[str, str]] = deque(maxlen=max_history)

    def add_transition(self, from_node: str, to_node: str) -> bool:
        """Add a state transition and check for cycles.

        Args:
            from_node: Source node name
            to_node: Target node name

        Returns:
            True if a cycle is detected, False otherwise
        """
        transition = (from_node, to_node)
        self.transition_history.append(transition)

        # Check for cycles
        if len(self.transition_history) < 4:  # Need at least 2 transitions repeated
            return False

        # Look for repeating pattern
        # Example: [(A,B), (B,A), (A,B), (B,A)] is a cycle
        cycle_detected = self._detect_cycle()

        if cycle_detected:
            logger.error(f"State transition cycle detected: {list(self.transition_history)[-6:]}")

        return cycle_detected

    def _detect_cycle(self) -> bool:
        """Detect if recent transitions form a cycle."""
        history = list(self.transition_history)

        # Check for simple 2-step cycle: A→B→A→B→A→B
        if len(history) >= 6:
            # Get last 6 transitions
            last_6 = history[-6:]
            # Check if they form pattern: [A,B] * 3
            if (
                last_6[0] == last_6[2] == last_6[4]
                and last_6[1] == last_6[3] == last_6[5]
                and last_6[0] != last_6[1]
            ):
                return True

        # Check for 3-step cycle: A→B→C→A→B→C
        if len(history) >= 9:
            last_9 = history[-9:]
            if (
                last_9[0] == last_9[3] == last_9[6]
                and last_9[1] == last_9[4] == last_9[7]
                and last_9[2] == last_9[5] == last_9[8]
            ):
                return True

        return False

    def reset(self) -> None:
        """Reset the transition history."""
        self.transition_history.clear()
