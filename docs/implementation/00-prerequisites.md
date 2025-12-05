# Phase 0: Prerequisites

## Overview

Before starting implementation, ensure your environment is properly configured and you understand the scope.

## Environment Setup

### 1. Python Version

**Required**: Python 3.11+

```bash
python --version
# Should show: Python 3.11.x or 3.12.x
```

**Why**: We use modern type hints (`|` instead of `Union`, `list[T]` instead of `List[T]`).

### 2. Install Dependencies

```bash
# Sync all dependencies including dev tools
uv sync

# Verify installation
uv run python -c "import dspy; import langgraph; print('✅ Dependencies OK')"
```

### 3. Verify Tools

```bash
# Ruff (linting & formatting)
uv run ruff --version

# Mypy (type checking)
uv run mypy --version

# Pytest (testing)
uv run pytest --version
```

## Repository State

### Clean Slate Approach

**Decision**: We will **replace** existing broken code, not fix it.

**Rationale**:
- Current code doesn't align with v0.8 design
- Faster to rewrite cleanly than debug and refactor
- Zero legacy constraints

**Backup Strategy**:

```bash
# Create backup branch of current state
git checkout -b backup/pre-refactor-$(date +%Y%m%d)
git push -u origin backup/pre-refactor-$(date +%Y%m%d)

# Return to main
git checkout main
```

### Directory Structure

Verify this structure exists:

```
soni/
├── src/soni/           # Source code
│   ├── core/           # Core types & interfaces
│   ├── du/             # Dialogue Understanding (NLU)
│   ├── dm/             # Dialogue Management (LangGraph)
│   ├── flow/           # Flow management
│   ├── actions/        # Action registry
│   ├── validation/     # Validator registry
│   ├── config/         # Configuration
│   ├── server/         # FastAPI server
│   └── cli/            # CLI commands
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── docs/
│   ├── design/         # Design specifications (v0.8)
│   └── implementation/ # This directory
├── examples/           # Example configurations
└── pyproject.toml      # Dependencies
```

If directories are missing:

```bash
mkdir -p src/soni/{core,du,dm,flow,actions,validation,config,server,cli}
mkdir -p tests/{unit,integration}
```

## Knowledge Prerequisites

### Required Reading

Before starting, read these design documents in order:

1. **[docs/design/README.md](../design/README.md)** - Overview
2. **[docs/design/02-architecture.md](../design/02-architecture.md)** - Core principles
3. **[docs/design/03-components.md](../design/03-components.md)** - Component responsibilities
4. **[docs/design/04-state-machine.md](../design/04-state-machine.md)** - State schema

### Coding Standards

Review **[CLAUDE.md](../../CLAUDE.md)** for:
- Type hint conventions
- Docstring format
- Error handling patterns
- Testing standards (AAA pattern)

### Technology Deep Dives

Familiarize yourself with:

**DSPy**:
- Read: `ref/dspy/README.md` (reference code)
- Focus: Modules, Signatures, async patterns

**LangGraph**:
- Read: `ref/langgraph/README.md` (reference code)
- Focus: StateGraph, checkpointing, interrupt/resume

## Git Workflow

### Branching Strategy

We'll use feature branches for each phase:

```bash
# Phase 1
git checkout -b feature/phase-1-foundation

# When complete
git add .
git commit -m "feat: implement phase 1 foundation"
git push -u origin feature/phase-1-foundation

# Merge to main (after validation)
git checkout main
git merge feature/phase-1-foundation
```

### Commit Message Format

Follow Conventional Commits:

```
feat: add FlowManager with stack operations
fix: correct state transition validation logic
test: add unit tests for DialogueState
docs: update implementation progress
refactor: extract NLU cache to separate class
```

**Types**: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`

## Validation Tools

### Pre-Commit Checks (Manual)

After each significant change:

```bash
# 1. Format code
uv run ruff format .

# 2. Check linting
uv run ruff check .

# 3. Type checking
uv run mypy src/soni

# 4. Run tests
uv run pytest tests/

# If all pass → commit
git add .
git commit -m "..."
```

### Automated Checks (Optional)

Set up pre-commit hooks:

```bash
# Install pre-commit hooks
uv run pre-commit install

# Now checks run automatically on commit
```

## Progress Tracking

### Task States

Use these markers in task documents:

- `📋 Backlog`: Not started
- `🚧 In Progress`: Currently working
- `✅ Done`: Completed and tested
- `⏸️ Blocked`: Waiting on something

### Daily Log (Optional)

Keep a simple log in `docs/implementation/PROGRESS.md`:

```markdown
# Implementation Progress

## 2024-12-05

- ✅ Completed Phase 0 prerequisites
- ✅ Created backup branch
- 🚧 Started Phase 1: Task 1.1

**Blockers**: None
**Next**: Complete Task 1.2
```

## Verification Checklist

Before proceeding to Phase 1, verify:

- [ ] Python 3.11+ installed
- [ ] All dependencies installed (`uv sync`)
- [ ] Tools working (ruff, mypy, pytest)
- [ ] Backup branch created
- [ ] Directory structure in place
- [ ] Design docs reviewed
- [ ] CLAUDE.md conventions understood
- [ ] Git workflow clear

## Troubleshooting

### Issue: `uv sync` fails

**Solution**:
```bash
# Update uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clear cache and retry
uv cache clean
uv sync
```

### Issue: Import errors after sync

**Solution**:
```bash
# Verify virtual environment
uv run python -c "import sys; print(sys.prefix)"

# Should show: /path/to/soni/.venv
```

### Issue: Mypy shows too many errors

**Solution**: Start with `--no-strict` mode:
```bash
uv run mypy --no-strict-optional src/soni
```

We'll tighten strictness as we implement.

## Next Steps

Once all prerequisites are met:

1. Create feature branch: `git checkout -b feature/phase-1-foundation`
2. Proceed to **[01-phase-1-foundation.md](01-phase-1-foundation.md)**
3. Start with Task 1.1

---

**Checklist Complete?** ✅
**Ready to Code?** Let's go! 🚀
