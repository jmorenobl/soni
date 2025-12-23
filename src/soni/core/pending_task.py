"""PendingTask types for Human Input Gate architecture.

This module defines the core data structures that subgraphs return when they
need user input. Uses union types (ISP) instead of one generic TypedDict.
"""

from typing import Any, Literal, NotRequired, TypedDict

# ─────────────────────────────────────────────────────────────────
# Specific Task Types (ISP: each type has only the fields it needs)
# ─────────────────────────────────────────────────────────────────


class CollectTask(TypedDict):
    """Task that collects a slot value from the user."""

    type: Literal["collect"]
    prompt: str
    slot: str  # REQUIRED for collect
    options: NotRequired[list[str]]
    metadata: NotRequired[dict[str, Any]]


class ConfirmTask(TypedDict):
    """Task that asks user for confirmation (yes/no/cancel)."""

    type: Literal["confirm"]
    prompt: str
    options: list[str]  # REQUIRED
    metadata: NotRequired[dict[str, Any]]


class InformTask(TypedDict):
    """Task that displays information to the user."""

    type: Literal["inform"]
    prompt: str
    wait_for_ack: NotRequired[bool]
    options: NotRequired[list[str]]
    metadata: NotRequired[dict[str, Any]]


# Union type (discriminated union on "type" field)
PendingTask = CollectTask | ConfirmTask | InformTask


# ─────────────────────────────────────────────────────────────────
# Factory Functions
# ─────────────────────────────────────────────────────────────────


def collect(
    prompt: str,
    slot: str,
    *,
    options: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> CollectTask:
    """Create a CollectTask to gather a slot value from the user."""
    task: CollectTask = {"type": "collect", "prompt": prompt, "slot": slot}
    if options:
        task["options"] = options
    if metadata:
        task["metadata"] = metadata
    return task


def confirm(
    prompt: str,
    options: list[str] | None = None,
    *,
    metadata: dict[str, Any] | None = None,
) -> ConfirmTask:
    """Create a ConfirmTask to ask for user confirmation."""
    task: ConfirmTask = {
        "type": "confirm",
        "prompt": prompt,
        "options": options or ["yes", "no"],
    }
    if metadata:
        task["metadata"] = metadata
    return task


def inform(
    prompt: str,
    *,
    wait_for_ack: bool = False,
    options: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> InformTask:
    """Create an InformTask to display information to the user."""
    task: InformTask = {"type": "inform", "prompt": prompt}
    if wait_for_ack:
        task["wait_for_ack"] = True
    if options:
        task["options"] = options
    if metadata:
        task["metadata"] = metadata
    return task


# ─────────────────────────────────────────────────────────────────
# Type Guards
# ─────────────────────────────────────────────────────────────────


def is_collect(task: PendingTask) -> bool:
    """Check if task is a CollectTask."""
    return task["type"] == "collect"


def is_confirm(task: PendingTask) -> bool:
    """Check if task is a ConfirmTask."""
    return task["type"] == "confirm"


def is_inform(task: PendingTask) -> bool:
    """Check if task is an InformTask."""
    return task["type"] == "inform"


def requires_input(task: PendingTask) -> bool:
    """Check if this task requires user input (pauses flow)."""
    if task["type"] in ("collect", "confirm"):
        return True
    if task["type"] == "inform":
        return task.get("wait_for_ack", False)
    return False
