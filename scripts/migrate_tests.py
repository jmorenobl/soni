#!/usr/bin/env python3
"""
Script to migrate tests from old DialogueState dataclass to new TypedDict schema.

This script updates test files to use the new helper functions instead of
dataclass constructors and attribute access.
"""

import re
import sys
from pathlib import Path


def migrate_test_file(file_path: Path) -> tuple[str, int]:
    """Migrate a single test file to use new schema.

    Returns:
        tuple of (new_content, num_changes)
    """
    content = file_path.read_text()
    original_content = content
    changes = 0

    # 1. Update imports to include helper functions
    if (
        "from soni.core.state import DialogueState" in content
        and "create_empty_state" not in content
    ):
        content = content.replace(
            "from soni.core.state import DialogueState",
            "from soni.core.state import DialogueState, create_empty_state, create_initial_state, get_current_flow, get_all_slots",
        )
        changes += 1

    # 2. Replace DialogueState() constructor with create_empty_state()
    # Match: DialogueState()
    pattern1 = r"\bDialogueState\(\s*\)"
    if re.search(pattern1, content):
        content = re.sub(pattern1, "create_empty_state()", content)
        changes += len(re.findall(pattern1, original_content))

    # 3. Replace DialogueState(...) with dict constructor for complex states
    # This is trickier - we need to convert to new schema format
    # For now, just flag these for manual review
    pattern2 = r"\bDialogueState\([^)]+\)"
    matches = re.findall(pattern2, content)
    if matches:
        print(f"  ⚠️  Found {len(matches)} complex DialogueState constructors - needs manual review")
        for match in matches[:3]:  # Show first 3
            print(f"      {match[:80]}...")

    # 4. Remove isinstance checks for DialogueState (TypedDict doesn't support isinstance)
    isinstance_pattern = r"assert isinstance\((\w+), DialogueState\)"
    if re.search(isinstance_pattern, content):
        # Replace with isinstance(..., dict) since TypedDict is a dict at runtime
        content = re.sub(isinstance_pattern, r"assert isinstance(\1, dict)", content)
        changes += len(re.findall(isinstance_pattern, original_content))

    # 5. Replace state.field access with state["field"]
    # Common fields that need updating
    field_patterns = [
        (r"state\.current_flow\b", "get_current_flow(state)"),
        (r"state\.slots\b", "get_all_slots(state)"),
        (r"state\.turn_count\b", 'state["turn_count"]'),
        (r"state\.messages\b", 'state["messages"]'),
        (r"state\.last_response\b", 'state["last_response"]'),
        (r"state\.pending_action\b", 'state.get("pending_action")'),
        (r"state\.trace\b", 'state["trace"]'),
        (r"state\.summary\b", 'state.get("summary")'),
    ]

    for pattern, replacement in field_patterns:
        if re.search(pattern, content):
            before = content
            content = re.sub(pattern, replacement, content)
            if content != before:
                changes += len(re.findall(pattern, before))

    return content, changes


def main():
    """Main migration script."""
    # Find all test files
    test_dir = Path("tests")
    if not test_dir.exists():
        print("Error: tests/ directory not found")
        sys.exit(1)

    test_files = list(test_dir.rglob("test_*.py"))
    print(f"Found {len(test_files)} test files to migrate\n")

    total_changes = 0
    migrated_files = []

    for test_file in sorted(test_files):
        print(f"Processing {test_file}...")
        try:
            new_content, changes = migrate_test_file(test_file)
            if changes > 0:
                # Backup original
                backup_path = test_file.with_suffix(".py.bak")
                test_file.rename(backup_path)

                # Write migrated content
                test_file.write_text(new_content)

                print(f"  ✅ Migrated with {changes} changes (backup: {backup_path.name})")
                total_changes += changes
                migrated_files.append(test_file)
            else:
                print("  ⏭️  No changes needed")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    print(f"\n{'=' * 60}")
    print("Migration Summary:")
    print(f"  Files migrated: {len(migrated_files)}")
    print(f"  Total changes: {total_changes}")
    print("\nNext steps:")
    print("  1. Review migrated files (backups saved as *.py.bak)")
    print("  2. Manually fix complex DialogueState(...) constructors")
    print("  3. Run tests: uv run pytest tests/")
    print("  4. If tests pass, delete backups: rm tests/**/*.py.bak")


if __name__ == "__main__":
    main()
