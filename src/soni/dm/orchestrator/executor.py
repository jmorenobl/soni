"""Subgraph executor for orchestrator (SRP)."""

from collections.abc import AsyncIterator
from typing import Any

from soni.runtime.context import SubgraphRegistry


class SubgraphExecutor:
    """Executes subgraphs with streaming support (SRP)."""

    def __init__(self, registry: SubgraphRegistry) -> None:
        self._registry = registry

    async def execute(
        self,
        flow_name: str,
        state: dict[str, Any],
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        """Stream subgraph execution, yielding (node_name, output) tuples."""
        subgraph = self._registry.get(flow_name)

        # astream(stream_mode="updates") yields dicts like {node_name: {updates}}
        async for event in subgraph.astream(state, stream_mode="updates"):
            for node_name, output in event.items():
                yield node_name, output
