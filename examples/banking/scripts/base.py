"""
Flow Testing Framework - Base Infrastructure.

Provides FlowTestRunner, state diffing, and rich logging for debugging
complex conversational flows.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from soni.core.config import SoniConfig
from soni.runtime.loop import RuntimeLoop

# =============================================================================
# Enums and Data Classes
# =============================================================================


class LogLevel(IntEnum):
    """Verbosity levels for test output."""

    BASIC = 1  # -v: Input → Output → Final summary
    DETAILED = 2  # -vv: + NLU, slot changes, routing
    DEBUG = 3  # -vvv: + Full state diffs, node traversal


@dataclass
class Turn:
    """A single conversation turn in a scenario."""

    user_message: str
    expected_patterns: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class Scenario:
    """A complete test scenario with multiple turns."""

    name: str
    description: str
    turns: list[Turn]
    expected_final: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class TurnResult:
    """Result of executing a single turn."""

    turn_number: int
    user_message: str
    response: str
    state_before: dict[str, Any]
    state_after: dict[str, Any]
    passed: bool = True
    failure_reason: str = ""


@dataclass
class ScenarioResult:
    """Result of executing a complete scenario."""

    scenario: Scenario
    turn_results: list[TurnResult]
    passed: bool = True
    duration_ms: float = 0.0


# =============================================================================
# State Differ
# =============================================================================


class StateDiffer:
    """Computes and formats differences between dialogue states."""

    TRACKED_KEYS = [
        "flow_stack",
        "flow_slots",
        "conversation_state",
        "flow_state",
        "commands",
        "waiting_for_slot",
        "current_step_index",
    ]

    @classmethod
    def compute_diff(
        cls,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> dict[str, tuple[Any, Any]]:
        """Compute differences between two states.

        Returns:
            Dict mapping key -> (before_value, after_value) for changed keys.
        """
        changes: dict[str, tuple[Any, Any]] = {}

        for key in cls.TRACKED_KEYS:
            val_before = before.get(key)
            val_after = after.get(key)

            if val_before != val_after:
                changes[key] = (val_before, val_after)

        return changes

    @classmethod
    def format_flow_stack_change(
        cls,
        before: list[dict[str, Any]] | None,
        after: list[dict[str, Any]] | None,
    ) -> str:
        """Format flow_stack changes as human-readable string."""
        before = before or []
        after = after or []

        before_names = [f.get("flow_name", "?") for f in before]
        after_names = [f.get("flow_name", "?") for f in after]

        if len(after) > len(before):
            added = after_names[-1]
            return f"+ PUSH: {added}"
        elif len(after) < len(before):
            removed = before_names[-1]
            return f"- POP: {removed}"
        else:
            return f"~ {before_names} → {after_names}"


# =============================================================================
# Rich Logger
# =============================================================================


class RichLogger:
    """Rich console output for test results."""

    def __init__(self, console: Console, level: LogLevel = LogLevel.BASIC) -> None:
        self.console = console
        self.level = level

    def scenario_header(self, scenario: Scenario) -> None:
        """Print scenario header."""
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]{scenario.name}[/bold]\n{scenario.description}",
                title="Scenario",
                border_style="blue",
            )
        )

    def turn_header(self, turn_number: int, total_turns: int) -> None:
        """Print turn separator."""
        self.console.print()
        self.console.rule(f"Turn {turn_number}/{total_turns}", style="dim")

    def user_message(self, message: str) -> None:
        """Print user message."""
        self.console.print(f"[bold green]User >[/] {message}")

    def bot_response(self, response: str) -> None:
        """Print bot response."""
        # Handle multi-line responses
        lines = response.split("\n")
        self.console.print(f"[bold blue]Soni >[/] {lines[0]}")
        for line in lines[1:]:
            self.console.print(f"        {line}")

    def nlu_result(self, state: dict[str, Any]) -> None:
        """Print NLU result (level >= DETAILED)."""
        if self.level < LogLevel.DETAILED:
            return

        commands = state.get("commands", [])
        conv_state = state.get("conversation_state", "?")

        table = Table(title="NLU Result", show_header=False, box=None)
        table.add_column("Key", style="dim")
        table.add_column("Value")

        table.add_row("conversation_state", str(conv_state))
        table.add_row("commands", str(commands))

        self.console.print(table)

    def state_diff(self, changes: dict[str, tuple[Any, Any]]) -> None:
        """Print state changes (level >= DETAILED)."""
        if self.level < LogLevel.DETAILED or not changes:
            return

        table = Table(title="State Changes", show_header=True, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Before", style="red")
        table.add_column("After", style="green")

        for key, (before, after) in changes.items():
            # Truncate long values
            before_str = self._truncate(str(before), 40)
            after_str = self._truncate(str(after), 40)
            table.add_row(key, before_str, after_str)

        self.console.print(table)

    def full_state(self, state: dict[str, Any], label: str = "State") -> None:
        """Print full state (level == DEBUG)."""
        if self.level < LogLevel.DEBUG:
            return

        tree = Tree(f"[bold]{label}[/]")

        for key in StateDiffer.TRACKED_KEYS:
            value = state.get(key)
            if value is not None:
                tree.add(f"[cyan]{key}[/]: {self._truncate(str(value), 60)}")

        self.console.print(tree)

    def flow_stack_tree(self, flow_stack: list[dict[str, Any]]) -> None:
        """Print flow stack as tree (level == DEBUG)."""
        if self.level < LogLevel.DEBUG or not flow_stack:
            return

        tree = Tree("[bold]Flow Stack[/]")
        for i, ctx in enumerate(flow_stack):
            name = ctx.get("flow_name", "?")
            flow_id = ctx.get("flow_id", "?")[:8]
            step = ctx.get("current_step_index", 0)
            tree.add(f"[{i}] {name} (id={flow_id}..., step={step})")

        self.console.print(tree)

    def assertion_result(self, pattern: str, found: bool) -> None:
        """Print pattern assertion result."""
        if found:
            self.console.print(f"  [green]✓[/] Pattern found: '{pattern}'")
        else:
            self.console.print(f"  [red]✗[/] Pattern NOT found: '{pattern}'")

    def scenario_summary(self, result: ScenarioResult) -> None:
        """Print scenario summary."""
        passed = sum(1 for tr in result.turn_results if tr.passed)
        total = len(result.turn_results)

        status = "[green]PASSED[/]" if result.passed else "[red]FAILED[/]"
        self.console.print()
        self.console.print(
            Panel(
                f"Status: {status}\n"
                f"Turns: {passed}/{total} passed\n"
                f"Duration: {result.duration_ms:.0f}ms",
                title=f"Summary: {result.scenario.name}",
                border_style="green" if result.passed else "red",
            )
        )

        # Show failures if any
        if not result.passed:
            for tr in result.turn_results:
                if not tr.passed:
                    self.console.print(f"  [red]Turn {tr.turn_number}:[/] {tr.failure_reason}")

    def final_slots(self, state: dict[str, Any]) -> None:
        """Print final slot values."""
        flow_slots = state.get("flow_slots", {})
        if not flow_slots:
            return

        table = Table(title="Final Slot Values", show_header=True)
        table.add_column("Flow", style="cyan")
        table.add_column("Slot", style="yellow")
        table.add_column("Value", style="green")

        for flow_id, slots in flow_slots.items():
            flow_name = flow_id.rsplit("_", 1)[0] if "_" in flow_id else flow_id
            for slot_name, value in slots.items():
                table.add_row(flow_name, slot_name, str(value))

        self.console.print(table)

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text with ellipsis if too long."""
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."


# =============================================================================
# Mock NLU Provider
# =============================================================================


class MockNLUProvider:
    """Mock NLU provider for deterministic testing.

    Uses predefined responses based on message patterns.
    """

    def __init__(self) -> None:
        from soni.core.commands import (
            AffirmConfirmation,
            CancelFlow,
            DenyConfirmation,
            SetSlot,
            StartFlow,
        )
        from soni.du.models import NLUOutput

        self.NLUOutput = NLUOutput
        self.StartFlow = StartFlow
        self.SetSlot = SetSlot
        self.DenyConfirmation = DenyConfirmation
        self.AffirmConfirmation = AffirmConfirmation
        self.CancelFlow = CancelFlow

        # Pattern -> commands mapping
        self._patterns: dict[str, list[Any]] = {}
        self._setup_default_patterns()

    def _setup_default_patterns(self) -> None:
        """Setup default pattern responses."""
        # Intent patterns
        intent_patterns = {
            # Balance
            "balance": "check_balance",
            "how much": "check_balance",
            "what's in my": "check_balance",
            # Transactions
            "transaction": "check_transactions",
            "movements": "check_transactions",
            "spending": "check_transactions",
            # Transfers
            "transfer": "transfer_funds",
            "send money": "transfer_funds",
            "wire": "transfer_funds",
            # Cards
            "lost my card": "block_card",
            "block my card": "block_card",
            "stolen": "block_card",
            "new card": "request_card",
            "request a card": "request_card",
            "need a card": "request_card",
            "credit card": "request_card",
            "debit card": "request_card",
            # Bills
            "pay a bill": "pay_bill",
            "pay my": "pay_bill",
        }

        for pattern, flow in intent_patterns.items():
            self._patterns[pattern.lower()] = [self.StartFlow(flow_name=flow)]

        # Confirmation patterns
        self._patterns["yes"] = [self.AffirmConfirmation()]
        self._patterns["no"] = [self.DenyConfirmation()]

    def get_response(self, message: str, context: dict[str, Any]) -> Any:
        """Get mock NLU response for a message."""
        import re

        msg_lower = message.lower().strip()

        # Handle modification patterns first ("no, change the X" or "change the X")
        change_match = re.search(r"change (?:the )?(\w+)", msg_lower)
        if change_match:
            slot_hint = change_match.group(1)
            # Map common words to slot names
            slot_mapping = {
                "amount": "amount",
                "sum": "amount",
                "beneficiary": "beneficiary_name",
                "recipient": "beneficiary_name",
                "name": "beneficiary_name",
                "iban": "iban",
                "account": "source_account",
                "concept": "transfer_concept",
                "reference": "transfer_concept",
            }
            slot_name = slot_mapping.get(slot_hint, slot_hint)
            return self.NLUOutput(commands=[self.DenyConfirmation(slot_to_change=slot_name)])

        # Check for pattern match
        for pattern, commands in self._patterns.items():
            if pattern in msg_lower:
                return self.NLUOutput(commands=commands)

        # Default: treat as slot value
        waiting_for = context.get("waiting_for_slot")
        if waiting_for:
            return self.NLUOutput(commands=[self.SetSlot(slot=waiting_for, value=message)])

        # Fallback
        return self.NLUOutput(commands=[])


# =============================================================================
# Flow Test Runner
# =============================================================================


class FlowTestRunner:
    """Orchestrates scenario execution with logging and state tracking."""

    def __init__(
        self,
        config_path: Path | str,
        level: LogLevel = LogLevel.BASIC,
        use_real_nlu: bool = False,
    ) -> None:
        self.config_path = Path(config_path)
        self.level = level
        self.use_real_nlu = use_real_nlu
        self.console = Console()
        self.logger = RichLogger(self.console, level)

        self._runtime: RuntimeLoop | None = None
        self._mock_nlu: MockNLUProvider | None = None

    async def initialize(self) -> None:
        """Initialize the runtime."""
        # Load banking handlers to register actions
        # This is done by importing the module which triggers @ActionRegistry.register decorators
        import examples.banking.handlers  # noqa: F401

        # Note: validators not imported since soni.validation module doesn't exist yet

        if self.use_real_nlu:
            import dspy

            # Configure default LM for real NLU
            lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
            dspy.configure(lm=lm)
            self.console.print(f"[dim]Configured DSPy with {lm.model}[/]")

        config = SoniConfig.from_yaml(self.config_path)
        checkpointer = MemorySaver()

        self._runtime = RuntimeLoop(config, checkpointer=checkpointer)
        await self._runtime.initialize()

        if not self.use_real_nlu:
            self._mock_nlu = MockNLUProvider()

    async def run_scenario(self, scenario: Scenario, user_id: str) -> ScenarioResult:
        """Execute a complete scenario."""
        import time

        if not self._runtime:
            await self.initialize()

        assert self._runtime is not None

        self.logger.scenario_header(scenario)

        start_time = time.time()
        turn_results: list[TurnResult] = []
        all_passed = True

        for i, turn in enumerate(scenario.turns, 1):
            self.logger.turn_header(i, len(scenario.turns))
            self.logger.user_message(turn.user_message)

            # Get state before
            state_before = await self._runtime.get_state(user_id) or {}

            # Execute turn
            if self._mock_nlu and not self.use_real_nlu:
                # Inject mock NLU response
                response = await self._execute_with_mock_nlu(
                    turn.user_message, user_id, state_before
                )
            else:
                response = await self._runtime.process_message(turn.user_message, user_id)

            # Get state after
            state_after = await self._runtime.get_state(user_id) or {}

            # Log response
            self.logger.bot_response(response)
            self.logger.nlu_result(state_after)

            # Compute and show diff
            changes = StateDiffer.compute_diff(state_before, state_after)
            self.logger.state_diff(changes)
            self.logger.flow_stack_tree(state_after.get("flow_stack", []))

            # Check assertions
            turn_passed = True
            failure_reason = ""

            for pattern in turn.expected_patterns:
                found = pattern.lower() in response.lower()
                self.logger.assertion_result(pattern, found)
                if not found:
                    turn_passed = False
                    failure_reason = f"Pattern not found: '{pattern}'"

            if not turn_passed:
                all_passed = False

            turn_results.append(
                TurnResult(
                    turn_number=i,
                    user_message=turn.user_message,
                    response=response,
                    state_before=copy.deepcopy(state_before),
                    state_after=copy.deepcopy(state_after),
                    passed=turn_passed,
                    failure_reason=failure_reason,
                )
            )

        # Check final assertions
        final_state = await self._runtime.get_state(user_id) or {}
        last_response = turn_results[-1].response if turn_results else ""

        for pattern in scenario.expected_final:
            found = pattern.lower() in last_response.lower()
            self.logger.assertion_result(pattern, found)
            if not found:
                all_passed = False

        # Show final slots
        self.logger.final_slots(final_state)

        duration_ms = (time.time() - start_time) * 1000
        result = ScenarioResult(
            scenario=scenario,
            turn_results=turn_results,
            passed=all_passed,
            duration_ms=duration_ms,
        )

        self.logger.scenario_summary(result)
        return result

    async def _execute_with_mock_nlu(
        self,
        message: str,
        user_id: str,
        current_state: dict[str, Any],
    ) -> str:
        """Execute turn with mocked NLU."""
        assert self._runtime is not None
        assert self._mock_nlu is not None

        # Get mock NLU response
        nlu_response = self._mock_nlu.get_response(message, current_state)

        # Inject into runtime
        from unittest.mock import AsyncMock, Mock

        mock_du = Mock()
        mock_du.aforward = AsyncMock(return_value=nlu_response)

        # Temporarily replace DU
        original_du = self._runtime.du
        self._runtime.du = mock_du

        try:
            response = await self._runtime.process_message(message, user_id)
        finally:
            self._runtime.du = original_du

        return str(response)

    async def run_all(
        self,
        scenarios: list[Scenario],
        user_id_prefix: str = "test",
    ) -> list[ScenarioResult]:
        """Run all scenarios and return results."""
        results: list[ScenarioResult] = []

        for i, scenario in enumerate(scenarios):
            user_id = f"{user_id_prefix}_{scenario.name}_{i}"
            result = await self.run_scenario(scenario, user_id)
            results.append(result)

        # Print final summary
        self._print_final_summary(results)
        return results

    def _print_final_summary(self, results: list[ScenarioResult]) -> None:
        """Print summary of all scenario results."""
        passed = sum(1 for r in results if r.passed)
        total = len(results)

        self.console.print()
        self.console.rule("Final Summary")

        table = Table(show_header=True)
        table.add_column("Scenario", style="cyan")
        table.add_column("Status")
        table.add_column("Duration", justify="right")

        for result in results:
            status = Text("PASSED", style="green") if result.passed else Text("FAILED", style="red")
            table.add_row(
                result.scenario.name,
                status,
                f"{result.duration_ms:.0f}ms",
            )

        self.console.print(table)
        self.console.print()

        if passed == total:
            self.console.print(f"[bold green]All {total} scenarios passed![/]")
        else:
            self.console.print(f"[bold red]{total - passed}/{total} scenarios failed[/]")
