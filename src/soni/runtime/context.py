"""RuntimeContext for M5 (Actions + two-pass NLU)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from soni.config.models import SoniConfig
from soni.flow.manager import FlowManager

if TYPE_CHECKING:
    from soni.actions.registry import ActionRegistry
    from soni.du.modules import SoniDU
    from soni.du.slot_extractor import SlotExtractor


@dataclass
class RuntimeContext:
    """Context passed to nodes via runtime.context.

    This is the typed context accessible in nodes via `runtime.context`.
    """

    subgraph: Any  # CompiledStateGraph
    config: SoniConfig
    flow_manager: FlowManager
    du: "SoniDU"  # Pass 1: Intent detection (REQUIRED)
    slot_extractor: "SlotExtractor"  # Pass 2: Slot extraction (REQUIRED)
    action_registry: "ActionRegistry"  # M5: Action handlers (REQUIRED)


