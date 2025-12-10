# Code Review Checklist

## TDD Compliance

- [ ] **TDD used for new features?**
  - Check git history: test commits before feature commits
  - If test-after, check exception is documented

- [ ] **Tests cover edge cases?**
  - Empty inputs
  - None values
  - Invalid types
  - Boundary conditions

- [ ] **Tests are independent?**
  - Can run in any order
  - No shared state between tests
  - Each test sets up its own data

- [ ] **Test quality:**
  - Descriptive names
  - Arrange-Act-Assert pattern
  - One assertion focus per test
  - Docstrings explain what is tested

## Code Quality

- [ ] **Coverage >= 90%** for new code
- [ ] **Type hints** on all functions
- [ ] **Docstrings** on public API
- [ ] **No obvious bugs** or code smells
- [ ] **Follows SOLID principles**

## Documentation

- [ ] **README updated** if public API changed
- [ ] **CHANGELOG updated** with changes
- [ ] **Technical debt documented** if shortcuts taken

## Testing

- [ ] **All tests pass** locally
- [ ] **No skipped tests** without explanation
- [ ] **Integration tests** for new features
- [ ] **Manual testing** completed

---

**If any item fails, request changes with explanation.**
