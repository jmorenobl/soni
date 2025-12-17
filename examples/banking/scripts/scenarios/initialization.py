"""
Initialization flow scenarios: session setup and quick transfer with set node.

Note: quick_transfer scenarios require --real-nlu flag because the mock NLU
doesn't properly track waiting_for_slot state between collect nodes.
"""

from examples.banking.scripts.base import Scenario, Turn

SCENARIOS = [
    # This scenario works with mock NLU
    Scenario(
        name="initialize_session_happy",
        description="Initialize user session with set node (premium user)",
        turns=[
            Turn(
                "Start session",
                expected_patterns=["Welcome back", "Alice Johnson", "premium"],
                description="Triggers initialize_session flow with set node",
            ),
        ],
        expected_final=["Welcome back", "premium"],
        tags=["initialization", "set_node", "basic"],
    ),
    # These scenarios require real NLU (--real-nlu flag)
    Scenario(
        name="quick_transfer_happy",
        description="Quick transfer with defaults (requires --real-nlu)",
        turns=[
            Turn(
                "Quick transfer",
                expected_patterns=["How much"],
                description="Starts quick_transfer flow with set defaults",
            ),
            Turn(
                "500",
                expected_patterns=["recipient"],
                description="Sets amount, asks for recipient",
            ),
            Turn(
                "John Doe",
                expected_patterns=["IBAN"],
                description="Sets beneficiary, asks for IBAN",
            ),
            Turn(
                "ES9121000418450200051332",
                expected_patterns=["checking", "500", "EUR"],
                description="Shows summary with default values from set node",
            ),
            Turn(
                "yes",
                expected_patterns=["completed"],
                description="Confirms and executes transfer",
            ),
        ],
        expected_final=["completed"],
        tags=["initialization", "set_node", "transfer", "real-nlu"],
    ),
    # NOTE: This scenario is currently disabled because on_deny routing
    # is not implemented in ConfirmNodeFactory. The confirm node asks
    # "What would you like to change?" instead of jumping to cancel_transfer.
    # TODO: Implement on_deny support in ConfirmNodeFactory
    # Scenario(
    #     name="quick_transfer_cancel",
    #     description="Quick transfer cancelled (requires --real-nlu)",
    #     turns=[
    #         Turn("Quick transfer", expected_patterns=["How much"]),
    #         Turn("100", expected_patterns=["recipient"]),
    #         Turn("Jane Smith", expected_patterns=["IBAN"]),
    #         Turn("DE89370400440532013000", expected_patterns=["summary"]),
    #         Turn(
    #             "no",
    #             expected_patterns=["cancelled"],
    #             description="Denies confirmation, transfer cancelled",
    #         ),
    #     ],
    #     expected_final=["cancelled"],
    #     tags=["initialization", "set_node", "transfer", "cancel", "real-nlu"],
    # ),
]
