# TDD Guidelines for Soni Framework

**Last Updated:** 2025-12-10
**Status:** MANDATORY for new features

---

## Overview

This document defines Test-Driven Development (TDD) process for the Soni Framework.

**TDD is MANDATORY for:**
- ✅ New features (greenfield code)
- ✅ New modules/classes
- ✅ New node types
- ✅ New utilities
- ✅ Refactoring with behavior changes

**Test-after is ACCEPTABLE for:**
- ⚠️ Critical P0 bug fixes (document why)
- ⚠️ Retrofitting tests to legacy code
- ⚠️ Exploratory prototypes (that will be rewritten)
- ⚠️ Time-sensitive security fixes (document why)

---

## The TDD Cycle

### 1. RED Phase: Write Failing Test

**Before writing any code:**

1. Understand the requirement
2. Write a test that describes desired behavior
3. Run test - **it MUST fail** (if it passes, test is wrong!)
4. Commit: `git commit -m "test: add failing test for [feature]"`

**Example:**

```python
# tests/unit/utils/test_metadata_manager.py

def test_clears_confirmation_flags():
    """Test that all confirmation flags are removed."""
    # Arrange
    metadata = {
        "_confirmation_attempts": 2,
        "_confirmation_processed": True,
    }

    # Act
    result = MetadataManager.clear_confirmation_flags(metadata)

    # Assert
    assert "_confirmation_attempts" not in result
    assert "_confirmation_processed" not in result
```

**Run test:**
```bash
uv run pytest tests/unit/utils/test_metadata_manager.py::test_clears_confirmation_flags -v
# Expected: FAILED (MetadataManager does not exist yet)
```

### 2. GREEN Phase: Make Test Pass

**Write MINIMAL code to make test pass:**

1. Implement simplest solution
2. Don't worry about perfect design yet
3. Run test - **it MUST pass**
4. Commit: `git commit -m "feat: implement [feature] to pass test"`

**Example:**

```python
# src/soni/utils/metadata_manager.py

class MetadataManager:
    @staticmethod
    def clear_confirmation_flags(metadata: dict) -> dict:
        updated = metadata.copy()
        updated.pop("_confirmation_attempts", None)
        updated.pop("_confirmation_processed", None)
        return updated
```

**Run test:**
```bash
uv run pytest tests/unit/utils/test_metadata_manager.py::test_clears_confirmation_flags -v
# Expected: PASSED ✅
```

### 3. REFACTOR Phase: Improve Design

**Now improve the implementation:**

1. Refactor for better design
2. Add docstrings, type hints
3. Optimize if needed
4. Tests MUST still pass
5. Commit: `git commit -m "refactor: improve [feature] implementation"`

**Example:**

```python
# src/soni/utils/metadata_manager.py

class MetadataManager:
    """Centralized metadata manipulation following DRY principle."""

    @staticmethod
    def clear_confirmation_flags(metadata: dict[str, Any]) -> dict[str, Any]:
        """Clear confirmation-related flags from metadata.

        Removes all flags related to confirmation flow:
        - _confirmation_attempts: retry counter
        - _confirmation_processed: processing status flag
        - _confirmation_unclear: unclear response flag

        Args:
            metadata: Current metadata dictionary

        Returns:
            New metadata dict with confirmation flags removed
        """
        updated = metadata.copy()
        updated.pop("_confirmation_attempts", None)
        updated.pop("_confirmation_processed", None)
        updated.pop("_confirmation_unclear", None)  # Added after review
        return updated
```

**Run all tests:**
```bash
uv run pytest tests/unit/utils/test_metadata_manager.py -v
# Expected: All tests PASSED ✅
```

### 4. REPEAT: Next Test

**Write next test and repeat cycle:**

```python
def test_returns_new_dict_immutable():
    """Test that original metadata is not modified."""
    # Arrange
    metadata = {"_confirmation_attempts": 2}

    # Act
    result = MetadataManager.clear_confirmation_flags(metadata)

    # Assert
    assert metadata["_confirmation_attempts"] == 2  # Original unchanged
    assert "_confirmation_attempts" not in result  # New dict cleared
```

---

## TDD Best Practices

### Writing Good Tests

**DO:**
- ✅ Test one thing per test
- ✅ Use descriptive test names (`test_clears_all_confirmation_flags`)
- ✅ Follow Arrange-Act-Assert pattern
- ✅ Test behavior, not implementation
- ✅ Test edge cases (empty, None, invalid input)

**DON'T:**
- ❌ Test multiple things in one test
- ❌ Rely on test execution order
- ❌ Use production data in tests
- ❌ Skip RED phase (must see test fail first!)

### Test Coverage

**Minimum Requirements:**
- Unit tests: 90%+ coverage for new code
- Integration tests: All user flows
- Edge cases: Empty inputs, None, invalid types
- Error paths: Exception handling

**Check coverage:**
```bash
uv run pytest --cov=src/soni --cov-report=html
open htmlcov/index.html
```

---

## Exception Policy: When Test-After is OK

### Critical Bug Fixes

**Acceptable:**
- P0 production bug (system down)
- Security vulnerability
- Data corruption risk

**Required:**
- Document in task: "Test-after used because [reason]"
- Add to technical debt register if code quality suffers
- Write tests IMMEDIATELY after fix

**Example task note:**
```markdown
## Testing Approach

**Exception:** Using test-after for this task because of P0 production bug.

**Rationale:** Confirmation flow completely broken, users cannot complete bookings.
System hitting recursion limit causing timeouts.

**Debt:** Tests will be written immediately after fix is deployed (same PR).
This exception is documented in DEBT-002.
```

### Legacy Code

**Acceptable:**
- Retrofitting tests to existing untested code
- Characterization tests (document current behavior)

**Required:**
- Mark tests as "characterization tests" in docstring
- Plan to refactor to proper TDD in future

---

## Code Review Checklist

### For Reviewers

**TDD Compliance:**
- [ ] Was TDD used? (Check git history: test commits before feature commits)
- [ ] If test-after, is exception documented and justified?
- [ ] Do tests cover edge cases?
- [ ] Are tests independent (can run in any order)?
- [ ] Do tests follow Arrange-Act-Assert pattern?

**Quality Checks:**
- [ ] Coverage >= 90% for new code
- [ ] Tests have descriptive names
- [ ] No skipped tests without explanation
- [ ] Integration tests for new features

---

## Training Resources

### Recommended Reading

1. **Kent Beck: "Test-Driven Development: By Example"**
   - The TDD bible
   - Practical examples and patterns

2. **Martin Fowler: "Refactoring"**
   - How to refactor safely with tests
   - Common refactoring patterns

3. **Growing Object-Oriented Software, Guided by Tests**
   - Advanced TDD techniques
   - Test-first design principles

### Practice Exercises

**Kata 1: FizzBuzz with TDD**
1. Write test: `test_returns_fizz_for_multiples_of_3()`
2. Make it pass
3. Refactor
4. Repeat for Buzz, FizzBuzz, numbers

**Kata 2: Bowling Score Calculator**
- Complex logic, perfect for TDD
- Practice decomposing into small tests

---

## Tools and Automation

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/soni --cov-report=term-missing

# Run only unit tests
uv run pytest tests/unit/

# Run specific test file
uv run pytest tests/unit/utils/test_metadata_manager.py -v

# Run with watch (automatically re-run on file changes)
uv run pytest-watch
```

### Pre-commit Hook (Optional)

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: run-tests
      name: Run tests before commit
      entry: uv run pytest tests/unit/ -x
      language: system
      pass_filenames: false
      always_run: true
```

---

## Examples from Soni Codebase

### Example 1: MetadataManager (Good TDD)

**Commit History:**
1. `test: add failing test for clear_confirmation_flags`
2. `feat: implement clear_confirmation_flags`
3. `refactor: add docstrings and type hints`
4. `test: add test for immutability`
5. `feat: ensure metadata is not modified in-place`

### Example 2: Bug Fix (Acceptable Test-After)

**Commit History:**
1. `fix: prevent infinite loop in confirmation (P0)`
2. `test: add tests for confirmation retry logic`
3. `docs: document test-after exception in DEBT-002`

---

## FAQ

**Q: Do I always need to write tests first?**
A: Yes, for NEW features. For bug fixes, test-after is acceptable if justified.

**Q: Can I write multiple tests before implementing?**
A: Yes! You can write all tests first (all RED), then implement (all GREEN). This is "test-first", a variation of TDD.

**Q: What if I don't know how to test something?**
A: Ask for help! Pair programming is great for learning TDD. Also see "Training Resources" above.

**Q: How do I test async code?**
A: Use `@pytest.mark.asyncio` and `async def test_...()`. See existing tests for examples.

**Q: What about integration tests?**
A: Integration tests can be written after (since they test multiple components). But unit tests should follow TDD.

---

## Enforcement

**This is not optional** for new features. Code reviews will reject PRs that don't follow TDD without documented exception.

**Questions?** Ask team lead or see training resources above.
