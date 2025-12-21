"""RuntimeContext for M1."""

from dataclasses import dataclass
from typing import Any

from soni.config.models import SoniConfig
from soni.flow.manager import FlowManager


@dataclass
class RuntimeContext:
    """Context passed to nodes via runtime.context.

    This is the typed context accessible in nodes via `runtime.context`.
    """

    subgraph: Any  # CompiledStateGraph
    config: SoniConfig
    flow_manager: FlowManager
