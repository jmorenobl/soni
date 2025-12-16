"""Node factory registry."""
from soni.compiler.nodes.action import ActionNodeFactory
from soni.compiler.nodes.base import NodeFactory
from soni.compiler.nodes.branch import BranchNodeFactory
from soni.compiler.nodes.collect import CollectNodeFactory
from soni.compiler.nodes.confirm import ConfirmNodeFactory
from soni.compiler.nodes.say import SayNodeFactory
from soni.compiler.nodes.while_loop import WhileNodeFactory


def get_factory_for_step(step_type: str) -> NodeFactory:
    """Get the appropriate factory for a step type."""
    factories = {
        "collect": CollectNodeFactory(),
        "action": ActionNodeFactory(),
        "say": SayNodeFactory(),
        "branch": BranchNodeFactory(),
        "confirm": ConfirmNodeFactory(),
        "while": WhileNodeFactory(),
    }

    factory = factories.get(step_type)
    if not factory:
        raise ValueError(f"Unknown step type: {step_type}")

    return factory
