#!/usr/bin/env python3
"""Validate flow graphs for potential infinite loops and issues.

Usage:
    uv run python scripts/validate_flows.py examples/banking/domain
"""

import sys
from collections import defaultdict
from pathlib import Path

from soni.core.config import SoniConfig


def validate_flow(flow_name: str, flow_config) -> list[str]:
    """Validate a single flow for common issues."""
    issues = []
    steps = flow_config.steps_or_process

    if not steps:
        return issues

    step_names = {step.step for step in steps}

    for i, step in enumerate(steps):
        # Check 1: jump_to targets exist
        if step.jump_to and step.jump_to not in step_names:
            issues.append(
                f"Flow '{flow_name}', step '{step.step}': "
                f"jump_to target '{step.jump_to}' does not exist"
            )

        # Check 2: branch cases target existing steps
        if step.type == "branch" and step.cases:
            for case_value, target in step.cases.items():
                if target not in step_names:
                    issues.append(
                        f"Flow '{flow_name}', step '{step.step}': "
                        f"branch case '{case_value}' targets non-existent step '{target}'"
                    )

        # Check 3: while loop has exit_to or proper structure
        if step.type == "while":
            if not step.exit_to:
                # Check if there are steps after the do: block
                do_steps = set(step.do) if step.do else set()
                has_exit = False
                for j in range(i + 1, len(steps)):
                    if steps[j].step not in do_steps:
                        has_exit = True
                        break

                if not has_exit:
                    issues.append(
                        f"Flow '{flow_name}', step '{step.step}': "
                        f"while loop has no exit (no exit_to and no steps after do: block)"
                    )

            # Check that do: steps exist
            if step.do:
                for do_step in step.do:
                    if do_step not in step_names:
                        issues.append(
                            f"Flow '{flow_name}', step '{step.step}': "
                            f"do: references non-existent step '{do_step}'"
                        )

            # Warning: check for potential infinite loops
            # If a step in do: has jump_to back to while, need logic to exit
            if step.do:
                for j in range(i + 1, len(steps)):
                    candidate = steps[j]
                    if candidate.step in step.do and candidate.jump_to == step.step:
                        # Found a step that jumps back - check if there's branching logic before it
                        has_branching = False
                        for k in range(i + 1, j):
                            if steps[k].type == "branch":
                                has_branching = True
                                break

                        if not has_branching:
                            issues.append(
                                f"Flow '{flow_name}', step '{step.step}': "
                                f"potential infinite loop - step '{candidate.step}' jumps back "
                                f"without conditional branching in between"
                            )

    return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/validate_flows.py <config_path>")
        sys.exit(1)

    config_path = Path(sys.argv[1])

    print(f"Loading configuration from: {config_path}")
    config = SoniConfig.from_yaml(config_path)

    print(f"Found {len(config.flows)} flows\n")

    all_issues = []
    for flow_name, flow_config in config.flows.items():
        issues = validate_flow(flow_name, flow_config)
        if issues:
            all_issues.extend(issues)
            print(f"⚠️  Flow '{flow_name}':")
            for issue in issues:
                print(f"   - {issue}")
            print()

    if not all_issues:
        print("✅ All flows validated successfully - no issues found!")
        return 0
    else:
        print(f"\n❌ Found {len(all_issues)} issue(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
