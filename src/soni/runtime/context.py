"""RuntimeContext for M4 (NLU integration)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from soni.config.models import SoniConfig
from soni.flow.manager import FlowManager

if TYPE_CHECKING:
    from soni.du.modules import SoniDU


@dataclass
class RuntimeContext:
    """Context passed to nodes via runtime.context.

    This is the typed context accessible in nodes via `runtime.context`.
    """

    subgraph: Any  # CompiledStateGraph
    config: SoniConfig
    flow_manager: FlowManager
    du: "SoniDU"  # NLU module (M4) - REQUIRED
