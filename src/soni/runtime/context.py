from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from soni.config.models import SoniConfig
from soni.flow.manager import FlowManager

if TYPE_CHECKING:
    from soni.actions.registry import ActionRegistry
    from soni.core.message_sink import MessageSink
    from soni.dm.orchestrator.commands import CommandHandler
    from soni.du.modules import SoniDU
    from soni.du.rephraser import ResponseRephraser
    from soni.du.slot_extractor import SlotExtractor


class SubgraphRegistry(Protocol):
    """Registry for compiled flow subgraphs (DIP)."""

    def get(self, flow_name: str) -> Any:
        """Get compiled subgraph by flow name."""
        ...


@dataclass(frozen=True)
class RuntimeContext:
    """Context passed to nodes via runtime.context.

    ADR-002: Contains subgraphs and sinks for orchestration.
    DIP: Depends on abstractions (Protocols/ABCs).
    """

    config: SoniConfig
    flow_manager: FlowManager
    subgraph_registry: SubgraphRegistry
    message_sink: "MessageSink"
    nlu_provider: "SoniDU"  # Pass 1: Intent detection
    slot_extractor: "SlotExtractor"  # Pass 2: Slot extraction
    action_registry: "ActionRegistry"
    command_handlers: tuple["CommandHandler", ...] | None = None
    rephraser: "ResponseRephraser | None" = None
