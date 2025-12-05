#!/usr/bin/env python3
"""
Script to fix test_scope.py tests to use new DialogueState schema.
"""

import re
from pathlib import Path


def main():
    test_file = Path("tests/unit/test_scope.py")
    content = test_file.read_text()

    # Add push_flow and set_slot to imports
    content = content.replace(
        "from soni.core.state import DialogueState, create_empty_state, create_initial_state, get_current_flow, get_all_slots",
        "from soni.core.state import DialogueState, create_empty_state, push_flow, set_slot, get_current_flow, get_all_slots",
    )

    # Replace all DialogueState(current_flow="...") with helper functions
    # Pattern 1: DialogueState(current_flow="...")
    pattern1 = r'DialogueState\(current_flow="([^"]+)"\)'

    def replace_current_flow_only(match):
        flow = match.group(1)
        return f'_create_test_state(flow="{flow}")'

    content = re.sub(pattern1, replace_current_flow_only, content)

    # Pattern 2: DialogueState(current_flow="...", slots={...})
    pattern2 = r'DialogueState\(\s*current_flow="([^"]+)",\s*slots=\{([^}]+)\}\s*\)'

    def replace_with_slots(match):
        flow = match.group(1)
        slots_content = match.group(2)
        return f'_create_test_state(flow="{flow}", slots_str="{{{slots_content}}}")'

    content = re.sub(pattern2, replace_with_slots, content)

    # Add helper function at the top after imports
    helper_func = '''

def _create_test_state(flow: str = "none", slots_str: str | None = None) -> DialogueState:
    """Helper to create test states with new schema."""
    state = create_empty_state()
    if flow != "none":
        push_flow(state, flow)
    if slots_str:
        # Parse slots string like '{"origin": "Madrid"}'
        import ast
        slots_dict = ast.literal_eval(slots_str)
        for slot_name, slot_value in slots_dict.items():
            set_slot(state, slot_name, slot_value)
    return state


'''

    # Insert helper after the last import
    import_end = content.rfind("from soni.")
    import_line_end = content.find("\n\n", import_end)
    content = content[:import_line_end] + helper_func + content[import_line_end + 2 :]

    # Write back
    test_file.write_text(content)
    print(f"✅ Fixed {test_file}")


if __name__ == "__main__":
    main()
