#!/usr/bin/env python3
"""Validate NLU documentation consistency and completeness."""

import re
from pathlib import Path


def check_file_exists(filepath: str) -> bool:
    """Check if file exists."""
    path = Path(filepath)
    if not path.exists():
        print(f"❌ FAIL: File not found: {filepath}")
        return False
    print(f"✅ PASS: File exists: {filepath}")
    return True


def check_no_spanish_text(filepath: str) -> bool:
    """Check for Spanish text in file."""
    spanish_indicators = [
        r"\busuario\b",
        r"\bsistema\b",
        r"\bejemplo\b",
        r"\bpuede\b",
        r"\bdebe\b",
        r"\barchivo\b",
    ]

    path = Path(filepath)
    content = path.read_text()

    found_spanish = []
    for pattern in spanish_indicators:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            found_spanish.extend(matches)

    if found_spanish:
        print(f"❌ FAIL: Spanish text found in {filepath}: {found_spanish}")
        return False

    print(f"✅ PASS: No Spanish text in {filepath}")
    return True


def check_cross_references(filepath: str, references: list[str]) -> bool:
    """Check that file contains expected cross-references."""
    path = Path(filepath)
    content = path.read_text()

    missing_refs = []
    for ref in references:
        if ref not in content:
            missing_refs.append(ref)

    if missing_refs:
        print(f"❌ FAIL: Missing references in {filepath}: {missing_refs}")
        return False

    print(f"✅ PASS: All references found in {filepath}")
    return True


def check_examples_use_flight_booking(filepath: str) -> bool:
    """Check that examples use flight_booking scenario."""
    flight_booking_keywords = [
        "Madrid",
        "Barcelona",
        "book_flight",
        "destination",
        "departure_date",
    ]

    path = Path(filepath)
    content = path.read_text()

    # Check if file has examples section
    if "Example" not in content:
        print(f"⚠️  WARN: No examples found in {filepath}")
        return True  # Not a failure, just a warning

    # Check if examples use flight_booking keywords
    found_keywords = [kw for kw in flight_booking_keywords if kw in content]

    if len(found_keywords) < 2:
        print(f"❌ FAIL: Examples in {filepath} don't use flight_booking scenario")
        return False

    print(f"✅ PASS: Examples use flight_booking in {filepath}")
    return True


def check_docstring_length(filepath: str, class_name: str, max_lines: int) -> bool:
    """Check that class docstring is within expected length."""
    path = Path(filepath)
    content = path.read_text()

    # Find class docstring
    pattern = rf'class {class_name}.*?"""(.*?)"""'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        print(f"❌ FAIL: Could not find docstring for {class_name} in {filepath}")
        return False

    docstring = match.group(1)
    lines = docstring.strip().split("\n")
    line_count = len(lines)

    if line_count > max_lines:
        print(f"❌ FAIL: {class_name} docstring too long: {line_count} lines (max {max_lines})")
        return False

    print(f"✅ PASS: {class_name} docstring length OK: {line_count} lines")
    return True


def check_no_external_references_in_class_docstring(
    filepath: str, class_name: str, forbidden_refs: list[str]
) -> bool:
    """Check that class docstring does NOT reference external files (which LLM won't see)."""
    path = Path(filepath)
    content = path.read_text()

    # Find class docstring
    pattern = rf'class {class_name}.*?"""(.*?)"""'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        print(f"❌ FAIL: Could not find docstring for {class_name} in {filepath}")
        return False

    docstring = match.group(1)

    # Check for forbidden references
    found_refs = []
    for ref in forbidden_refs:
        if ref in docstring:
            found_refs.append(ref)

    if found_refs:
        print(f"❌ FAIL: {class_name} docstring contains external file references: {found_refs}")
        print("   Class docstrings are sent to LLM - must be self-contained!")
        return False

    print(f"✅ PASS: {class_name} docstring is self-contained (no external file refs)")
    return True


def main():
    """Run all validation checks."""
    print("=" * 60)
    print("NLU Documentation Validation")
    print("=" * 60)

    results = []

    # Task 334: DATA_STRUCTURES.md
    print("\n[Task 334] Validating DATA_STRUCTURES.md...")
    results.append(check_file_exists("src/soni/du/DATA_STRUCTURES.md"))
    results.append(check_no_spanish_text("src/soni/du/DATA_STRUCTURES.md"))
    results.append(check_examples_use_flight_booking("src/soni/du/DATA_STRUCTURES.md"))

    # Task 335: signatures.py
    print("\n[Task 335] Validating signatures.py...")
    results.append(check_no_spanish_text("src/soni/du/signatures.py"))
    results.append(
        check_cross_references(
            "src/soni/du/signatures.py",
            ["DATA_STRUCTURES.md"],  # Should be in module-level docstring
        )
    )
    results.append(
        check_no_external_references_in_class_docstring(
            "src/soni/du/signatures.py",
            "DialogueUnderstanding",
            forbidden_refs=["DATA_STRUCTURES.md", ".md"],  # Class docstring must be self-contained
        )
    )
    results.append(
        check_docstring_length(
            "src/soni/du/signatures.py",
            "DialogueUnderstanding",
            max_lines=20,  # Should be ~15 lines after refactor
        )
    )

    # Task 336: modules.py
    print("\n[Task 336] Validating modules.py...")
    results.append(check_no_spanish_text("src/soni/du/modules.py"))
    results.append(
        check_cross_references("src/soni/du/modules.py", ["DATA_STRUCTURES.md", "Example"])
    )
    results.append(check_examples_use_flight_booking("src/soni/du/modules.py"))

    # Task 337: models.py
    print("\n[Task 337] Validating models.py...")
    results.append(check_no_spanish_text("src/soni/du/models.py"))
    results.append(check_examples_use_flight_booking("src/soni/du/models.py"))
    results.append(
        check_cross_references(
            "src/soni/du/models.py",
            ["Examples:", "Example:"],  # Check for example sections
        )
    )

    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    pass_rate = (passed / total) * 100 if total > 0 else 0

    print(f"Results: {passed}/{total} checks passed ({pass_rate:.1f}%)")

    if passed == total:
        print("✅ All validation checks passed!")
        return 0
    else:
        print(f"❌ {total - passed} checks failed")
        return 1


if __name__ == "__main__":
    exit(main())
