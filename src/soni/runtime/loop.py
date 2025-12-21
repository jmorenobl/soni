"""RuntimeLoop for M1."""

from typing import Any

from langgraph.graph.state import CompiledStateGraph

from soni.compiler.subgraph import build_flow_subgraph
from soni.config.models import SoniConfig
from soni.core.state import create_empty_state
from soni.dm.builder import build_orchestrator
from soni.runtime.context import RuntimeContext


class RuntimeLoop:
    """Simple runtime loop for M1."""
    
    def __init__(self, config: SoniConfig) -> None:
        self.config = config
        self._graph: CompiledStateGraph | None = None
        self._context: RuntimeContext | None = None
    
    async def __aenter__(self) -> "RuntimeLoop":
        """Initialize graphs."""
        # Build subgraph for first flow
        flow_name = next(iter(self.config.flows.keys()))
        flow = self.config.flows[flow_name]
        subgraph = build_flow_subgraph(flow)
        
        # Create context
        self._context = RuntimeContext(subgraph=subgraph, config=self.config)
        
        # Build orchestrator
        self._graph = build_orchestrator()
        return self
    
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Cleanup."""
        pass
    
    async def process_message(self, message: str) -> str:
        """Process a message and return response."""
        if self._graph is None or self._context is None:
            raise RuntimeError("RuntimeLoop not initialized. Use 'async with' context.")
        
        state = create_empty_state()
        state["user_message"] = message
        
        # Pass context as kwarg (per LangGraph Runtime pattern)
        # config = {"configurable": {"context": self._context}}
        # result = await self._graph.ainvoke(state, config)
        
        # Try passing context directly as kwarg
        result = await self._graph.ainvoke(state, context=self._context)
        return result.get("response", "")
