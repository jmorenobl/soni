"""Node factory registry."""

from soni.compiler.nodes.action import ActionNodeFactory
from soni.compiler.nodes.base import NodeFactory
from soni.compiler.nodes.branch import BranchNodeFactory
from soni.compiler.nodes.collect import CollectNodeFactory
from soni.compiler.nodes.confirm import ConfirmNodeFactory
from soni.compiler.nodes.say import SayNodeFactory
from soni.compiler.nodes.set import SetNodeFactory
from soni.compiler.nodes.while_loop import WhileNodeFactory
from soni.core.errors import GraphBuildError


class NodeFactoryRegistry:
    """Registry for node factories."""

    _factories: dict[str, NodeFactory] = {}

    @classmethod
    def register(cls, step_type: str, factory: NodeFactory) -> None:
        """Register a new node factory."""
        cls._factories[step_type] = factory

    @classmethod
    def get(cls, step_type: str) -> NodeFactory:
        """Get factory for step type."""
        factory = cls._factories.get(step_type)
        if not factory:
            raise GraphBuildError(
                f"Unknown step type: '{step_type}'. Available types: {list(cls._factories.keys())}"
            )
        return factory


# Initialize default factories
NodeFactoryRegistry.register("collect", CollectNodeFactory())
NodeFactoryRegistry.register("action", ActionNodeFactory())
NodeFactoryRegistry.register("say", SayNodeFactory())
NodeFactoryRegistry.register("set", SetNodeFactory())
NodeFactoryRegistry.register("branch", BranchNodeFactory())
NodeFactoryRegistry.register("confirm", ConfirmNodeFactory())
NodeFactoryRegistry.register("while", WhileNodeFactory())


def get_factory_for_step(step_type: str) -> NodeFactory:
    """Get the appropriate factory for a step type.

    Delegates to registry.
    """
    return NodeFactoryRegistry.get(step_type)
