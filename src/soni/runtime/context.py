"""RuntimeContext for M7 (ADR-002 compliant interrupt architecture)."""

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

    ADR-002: Contains subgraphs dict for flow execution orchestration.
    """

    config: SoniConfig
    flow_manager: FlowManager
    du: "SoniDU"  # Pass 1: Intent detection (NLU service)
    slot_extractor: "SlotExtractor"  # Pass 2: Slot extraction
    action_registry: "ActionRegistry"  # M5: Action handlers
    subgraphs: dict[str, Any] | None = None  # ADR-002: Compiled flow subgraphs
