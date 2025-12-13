## Task: 307 - Establish TDD Process for New Features

**ID de tarea:** 307
**Hito:** Technical Debt Repayment - Process Improvement
**Dependencias:** Ninguna
**Duración estimada:** N/A (Process change + training)
**Prioridad:** 🟡 MEDIUM - Impacts future development
**Related DEBT:** DEBT-001

### Objetivo

Establecer y documentar un proceso formal de Test-Driven Development (TDD) para nuevas features, actualizando templates de tareas, checklists de code review, y proveyendo training al equipo para mejorar la calidad del código y design.

### Contexto

**Problema Actual:**
En Tasks 201-205 (y otros) se implementó código primero y tests después ("test-after"), no verdadero TDD. Esto es aceptable para:
- Bug fixes urgentes en código existente
- Retrofitting tests a código legacy
- Situaciones de emergencia documentadas

Pero para **nuevas features**, debemos seguir TDD estrictamente:
1. ✅ RED: Write failing test first
2. ✅ GREEN: Write minimal code to pass
3. ✅ REFACTOR: Improve implementation

**Razones para TDD:**
- Tests guían el design (mejor arquitectura)
- Código más testeable por diseño
- Mejor coverage (tests escritos antes, no después)
- Menos bugs en edge cases
- Refactoring más seguro

**Referencias:**
- Technical Debt: `docs/technical-debt.md` (DEBT-001)
- TDD Guide: Kent Beck's "Test-Driven Development: By Example"

### Entregables

- [ ] Documento TDD Guidelines creado en `docs/development/tdd-guidelines.md`
- [ ] Task template actualizado con TDD steps
- [ ] Code review checklist actualizado
- [ ] Ejemplos de TDD cycle documentados
- [ ] Training session plan creado
- [ ] Exception policy documentada (cuándo test-after es aceptable)
- [ ] Pre-commit hook (opcional) para verificar tests

### Implementación Detallada

#### Paso 1: Crear TDD Guidelines Document

**Archivo a crear:** `docs/development/tdd-guidelines.md`

**Contenido completo:**

```markdown
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

\`\`\`python
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
\`\`\`

**Run test:**
\`\`\`bash
uv run pytest tests/unit/utils/test_metadata_manager.py::test_clears_confirmation_flags -v
# Expected: FAILED (MetadataManager does not exist yet)
\`\`\`

### 2. GREEN Phase: Make Test Pass

**Write MINIMAL code to make test pass:**

1. Implement simplest solution
2. Don't worry about perfect design yet
3. Run test - **it MUST pass**
4. Commit: `git commit -m "feat: implement [feature] to pass test"`

**Example:**

\`\`\`python
# src/soni/utils/metadata_manager.py

class MetadataManager:
    @staticmethod
    def clear_confirmation_flags(metadata: dict) -> dict:
        updated = metadata.copy()
        updated.pop("_confirmation_attempts", None)
        updated.pop("_confirmation_processed", None)
        return updated
\`\`\`

**Run test:**
\`\`\`bash
uv run pytest tests/unit/utils/test_metadata_manager.py::test_clears_confirmation_flags -v
# Expected: PASSED ✅
\`\`\`

### 3. REFACTOR Phase: Improve Design

**Now improve the implementation:**

1. Refactor for better design
2. Add docstrings, type hints
3. Optimize if needed
4. Tests MUST still pass
5. Commit: `git commit -m "refactor: improve [feature] implementation"`

**Example:**

\`\`\`python
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
\`\`\`

**Run all tests:**
\`\`\`bash
uv run pytest tests/unit/utils/test_metadata_manager.py -v
# Expected: All tests PASSED ✅
\`\`\`

### 4. REPEAT: Next Test

**Write next test and repeat cycle:**

\`\`\`python
def test_returns_new_dict_immutable():
    """Test that original metadata is not modified."""
    # Arrange
    metadata = {"_confirmation_attempts": 2}

    # Act
    result = MetadataManager.clear_confirmation_flags(metadata)

    # Assert
    assert metadata["_confirmation_attempts"] == 2  # Original unchanged
    assert "_confirmation_attempts" not in result  # New dict cleared
\`\`\`

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
\`\`\`bash
uv run pytest --cov=src/soni --cov-report=html
open htmlcov/index.html
\`\`\`

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
\`\`\`markdown
## Testing Approach

**Exception:** Using test-after for this task because of P0 production bug.

**Rationale:** Confirmation flow completely broken, users cannot complete bookings.
System hitting recursion limit causing timeouts.

**Debt:** Tests will be written immediately after fix is deployed (same PR).
This exception is documented in DEBT-002.
\`\`\`

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

\`\`\`bash
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
\`\`\`

### Pre-commit Hook (Optional)

Add to `.pre-commit-config.yaml`:

\`\`\`yaml
- repo: local
  hooks:
    - id: run-tests
      name: Run tests before commit
      entry: uv run pytest tests/unit/ -x
      language: system
      pass_filenames: false
      always_run: true
\`\`\`

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
\`\`\`

#### Paso 2: Actualizar Task Template

**Archivo a modificar:** `workflow/tasks/backlog/task-template.md`

**Agregar sección después de "Implementación Detallada":**

```markdown
### TDD Cycle (MANDATORY for new features)

**This section is MANDATORY for new features. Delete only if test-after exception applies.**

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/[module]/test_[feature].py`

**Failing tests to write FIRST:**

\`\`\`python
# Test 1: [Description]
def test_[feature]_[scenario]():
    """Test that [expected behavior]."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented

# Test 2: [Description]
def test_[feature]_[edge_case]():
    """Test that [edge case handled correctly]."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented
\`\`\`

**Verify tests fail:**
\`\`\`bash
uv run pytest tests/unit/[module]/test_[feature].py -v
# Expected: FAILED (feature not implemented yet)
\`\`\`

**Commit:**
\`\`\`bash
git add tests/
git commit -m "test: add failing tests for [feature]"
\`\`\`

#### Green Phase: Make Tests Pass

**Implement minimal code to pass tests.**

See "Implementación Detallada" section for implementation steps.

**Verify tests pass:**
\`\`\`bash
uv run pytest tests/unit/[module]/test_[feature].py -v
# Expected: PASSED ✅
\`\`\`

**Commit:**
\`\`\`bash
git add src/ tests/
git commit -m "feat: implement [feature]"
\`\`\`

#### Refactor Phase: Improve Design

**Refactor implementation while keeping tests green.**

- Add docstrings
- Improve type hints
- Optimize if needed
- Extract helper functions
- Tests must still pass!

**Commit:**
\`\`\`bash
git add src/
git commit -m "refactor: improve [feature] implementation"
\`\`\`

---

### Exception: Test-After

**Only fill this section if NOT using TDD. Requires justification.**

**Reason for test-after:**
- [ ] P0 critical bug fix
- [ ] Security vulnerability
- [ ] Legacy code retrofit
- [ ] Other: [explain]

**Justification:**
[Detailed explanation of why test-after is necessary]

**Debt Tracking:**
[Reference to technical debt document if code quality suffers]

---
```

#### Paso 3: Actualizar Code Review Checklist

**Archivo a crear:** `docs/development/code-review-checklist.md`

```markdown
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
```

#### Paso 4: Crear Training Session Plan

**Archivo a crear:** `docs/development/tdd-training-plan.md`

```markdown
# TDD Training Session Plan

**Duration:** 2-3 hours
**Format:** Workshop with hands-on practice
**Prerequisites:** None

## Session Outline

### Part 1: Theory (30 min)

1. **What is TDD?** (10 min)
   - Red-Green-Refactor cycle
   - Why tests first, not after
   - Benefits and costs

2. **When to use TDD vs test-after** (10 min)
   - TDD for new features (mandatory)
   - Test-after for bug fixes (acceptable)
   - Exception policy

3. **Common TDD mistakes** (10 min)
   - Skipping RED phase
   - Testing implementation, not behavior
   - Tests too large
   - Tests depend on each other

### Part 2: Live Coding Demo (45 min)

**Instructor demonstrates TDD cycle with FizzBuzz:**

1. Write failing test
2. Make it pass (minimal code)
3. Refactor
4. Repeat

**Show commit history and workflow.**

### Part 3: Hands-on Practice (60 min)

**Students implement Bowling Score Calculator using TDD:**

1. Pair programming (pairs of 2)
2. Instructor circulates to help
3. Focus on TDD cycle, not completing feature

### Part 4: Review and Q&A (30 min)

1. Review solutions
2. Discuss challenges
3. Answer questions
4. Show examples from Soni codebase

## Practice Exercises

### Exercise 1: String Calculator (Easy)

Create a string calculator with TDD:
- `add("")` returns 0
- `add("1")` returns 1
- `add("1,2")` returns 3
- `add("1,2,3")` returns 6

### Exercise 2: Metadata Manager (Real Soni Code)

Implement MetadataManager using TDD:
- `clear_confirmation_flags()` removes specific flags
- `clear_all_flow_flags()` removes all flags
- Original metadata not modified (immutable)

## Resources for Students

- **TDD Guidelines:** `docs/development/tdd-guidelines.md`
- **Task Template:** `workflow/tasks/backlog/task-template.md`
- **Code Review Checklist:** `docs/development/code-review-checklist.md`
- **Kent Beck Book:** "Test-Driven Development: By Example"

## Success Criteria

Students can:
- [ ] Explain RED-GREEN-REFACTOR cycle
- [ ] Write failing test before implementation
- [ ] Make test pass with minimal code
- [ ] Refactor while keeping tests green
- [ ] Understand when test-after is acceptable
```

### Tests Requeridos

**No hay tests de código para esta task** (es un cambio de proceso).

**Validación:**
- Documentos creados y revisados
- Training session completed
- First feature after training follows TDD
- Code reviews check TDD compliance

### Criterios de Éxito

- [ ] `docs/development/tdd-guidelines.md` creado y aprobado
- [ ] Task template actualizado con TDD section
- [ ] Code review checklist creado
- [ ] Training session plan creado
- [ ] Training session impartida a equipo
- [ ] Primeras 3 PRs después de training siguen TDD
- [ ] Code reviews verifican TDD compliance
- [ ] Exception policy entendida por equipo

### Validación Manual

**Verificar documentos creados:**
```bash
ls docs/development/tdd-guidelines.md
ls docs/development/code-review-checklist.md
ls docs/development/tdd-training-plan.md
```

**Verificar template actualizado:**
```bash
grep -A 20 "TDD Cycle" workflow/tasks/backlog/task-template.md
```

**Verificar primeras PRs post-training:**
- Review git history: tests committed before features
- Review PR descriptions: mention TDD cycle
- Check test coverage >= 90%

### Referencias

- **Technical Debt:** `docs/technical-debt.md` (DEBT-001)
- **TDD Book:** Kent Beck's "Test-Driven Development: By Example"
- **Testing Rules:** `.cursor/rules/003-testing.mdc`

### Notas Adicionales

**Resistance to TDD:**
Algunos desarrolladores pueden resistirse a TDD inicialmente:
- "Tests first is slower" - False once experienced
- "I know what to build, why test first?" - Tests guide better design
- "Too much overhead" - Prevents bugs, saves time long-term

**Solution:**
- Pair programming with experienced TDD practitioner
- Start with simple katas (FizzBuzz)
- Show concrete examples from codebase
- Enforce in code reviews (with kindness)

**Measurement:**
Track these metrics after training:
- % of PRs following TDD (target: 80%+)
- Test coverage (target: >= 90%)
- Bug rate in new features (should decrease)
- Refactoring incidents (should decrease)

**Continuous Improvement:**
- Retrospectives: What's working? What's not?
- Pair programming sessions
- Kata practice sessions
- Share TDD success stories
