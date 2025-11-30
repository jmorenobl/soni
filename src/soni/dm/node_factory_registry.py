"""Node factory registry for dialogue management nodes"""

import logging
from collections.abc import Callable
from threading import Lock
from typing import Any

from soni.compiler.dag import DAGNode, NodeType
from soni.core.state import RuntimeContext

logger = logging.getLogger(__name__)

# Type alias for node factory functions
# Factory takes (DAGNode, RuntimeContext) and returns a node function
NodeFactoryFunction = Callable[[DAGNode, RuntimeContext], Any]

# Global registry state
_node_factories: dict[NodeType, NodeFactoryFunction] = {}
_factories_lock = Lock()


class NodeFactoryRegistry:
    """
    Thread-safe registry for node factory functions.

    Node factories are functions that create LangGraph node functions from DAG nodes.
    Each node type (UNDERSTAND, COLLECT, ACTION) has a corresponding factory.

    Example:
        @NodeFactoryRegistry.register(NodeType.UNDERSTAND)
        def create_understand_factory(node: DAGNode, context: RuntimeContext) -> Any:
            return create_understand_node(
                scope_manager=context.scope_manager,
                normalizer=context.normalizer,
                nlu_provider=context.du,
                context=context,
            )
    """

    @classmethod
    def register(cls, node_type: NodeType) -> Callable:
        """
        Register a node factory function.

        Args:
            node_type: Node type to register factory for

        Returns:
            Decorator function

        Example:
            @NodeFactoryRegistry.register(NodeType.COLLECT)
            def create_collect_factory(node: DAGNode, context: RuntimeContext) -> Any:
                slot_name = node.config["slot_name"]
                return create_collect_node_factory(slot_name, context)
        """

        def decorator(func: NodeFactoryFunction) -> NodeFactoryFunction:
            with _factories_lock:
                if node_type in _node_factories:
                    logger.warning(
                        f"Node factory for type '{node_type}' already registered, overwriting"
                    )
                _node_factories[node_type] = func
                logger.debug(f"Registered node factory for type: {node_type}")
            return func

        return decorator

    @classmethod
    def get(cls, node_type: NodeType) -> NodeFactoryFunction:
        """
        Get node factory function for a given node type.

        Args:
            node_type: Node type to get factory for

        Returns:
            Node factory function

        Raises:
            ValueError: If node type is not registered
        """
        with _factories_lock:
            if node_type not in _node_factories:
                raise ValueError(
                    f"Node factory for type '{node_type}' not found. "
                    f"Available types: {list(_node_factories.keys())}"
                )
            return _node_factories[node_type]

    @classmethod
    def is_registered(cls, node_type: NodeType) -> bool:
        """
        Check if a node type has a registered factory.

        Args:
            node_type: Node type to check

        Returns:
            True if registered, False otherwise
        """
        with _factories_lock:
            return node_type in _node_factories

    @classmethod
    def get_all(cls) -> dict[NodeType, NodeFactoryFunction]:
        """
        Get all registered node factories.

        Returns:
            Dictionary mapping node types to factory functions
        """
        with _factories_lock:
            return _node_factories.copy()

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered node factories.

        This is primarily useful for testing.
        """
        with _factories_lock:
            _node_factories.clear()
            logger.debug("Cleared all node factories")
