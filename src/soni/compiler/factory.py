"""Node factory registry (OCP: extensible without modification)."""

from soni.compiler.nodes.base import NodeFactory
from soni.compiler.nodes.say import SayNodeFactory
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
                f"Unknown step type: '{step_type}'. Available: {list(cls._factories.keys())}"
            )
        return factory


# Initialize default factories
NodeFactoryRegistry.register("say", SayNodeFactory())


def get_factory_for_step(step_type: str) -> NodeFactory:
    """Get the appropriate factory for a step type."""
    return NodeFactoryRegistry.get(step_type)
