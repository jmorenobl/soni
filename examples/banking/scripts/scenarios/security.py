"""Security alert review scenarios."""

from examples.banking.scripts.base import Scenario, Turn

SCENARIOS = [
    Scenario(
        name="security_alerts_review",
        description="Review all pending security alerts using while loop",
        turns=[
            Turn("Review my security alerts"),
        ],
        expected_final=["All 3 security alerts", "reviewed"],
        tags=["security", "alerts", "while_loop"],
    ),
]
