"""Pending task handler for orchestrator (SRP)."""

from dataclasses import dataclass
from enum import Enum

from soni.core.message_sink import MessageSink
from soni.core.pending_task import PendingTask, is_inform, requires_input


class TaskAction(Enum):
    """What to do after handling a pending task."""

    CONTINUE = "continue"
    INTERRUPT = "interrupt"
    COMPLETE = "complete"


@dataclass
class TaskResult:
    """Result of handling a pending task."""

    action: TaskAction
    task: PendingTask | None = None


class PendingTaskHandler:
    """Handles pending tasks from subgraph outputs (SRP)."""

    def __init__(self, message_sink: MessageSink) -> None:
        self._sink = message_sink

    async def handle(self, task: PendingTask) -> TaskResult:
        """Process a pending task and determine next action."""
        if is_inform(task):
            await self._sink.send(task["prompt"])

            if requires_input(task):
                return TaskResult(action=TaskAction.INTERRUPT, task=task)
            return TaskResult(action=TaskAction.CONTINUE)

        # COLLECT or CONFIRM: always interrupt
        return TaskResult(action=TaskAction.INTERRUPT, task=task)
