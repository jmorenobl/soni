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
