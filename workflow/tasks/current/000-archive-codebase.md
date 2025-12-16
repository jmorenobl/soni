## Task: 000 - Archive Current Codebase

**ID de tarea:** 000
**Hito:** 0 - Setup
**Dependencias:** Ninguna
**Duración estimada:** 1 hora

### Objetivo

Archive the current `src/` and `tests/` directories to `archive/` to preserve the reference implementation while starting fresh.

### Contexto

The v3.0 rewrite requires a clean slate. The current codebase has validated the subgraph architecture but contains technical debt. We archive rather than delete to preserve reference code and edge case handling.

### Entregables

- [ ] Create `archive/` directory structure
- [ ] Move `src/soni/` to `archive/src/soni/`
- [ ] Move `tests/` to `archive/tests/`
- [ ] Create empty `src/soni/` directory structure
- [ ] Create empty `tests/` directory structure
- [ ] Update `.gitignore` if needed
- [ ] Commit archive

### Implementación Detallada

#### Paso 1: Create archive directory and move code

```bash
# Create archive directory
mkdir -p archive

# Move current code to archive
mv src/soni archive/src/
mv tests archive/tests/

# Create new empty structure
mkdir -p src/soni/{core,flow,compiler/nodes,dm/nodes,du,runtime,actions,server}
mkdir -p tests/{unit/{core,flow,compiler,dm,du,runtime,actions},integration,e2e}

# Create __init__.py files
touch src/soni/__init__.py
touch src/soni/{core,flow,compiler,dm,du,runtime,actions,server}/__init__.py
touch src/soni/compiler/nodes/__init__.py
touch src/soni/dm/nodes/__init__.py
```

#### Paso 2: Create test conftest.py and factories.py

**Archivo:** `tests/conftest.py`

```python
"""Shared fixtures for Soni tests."""
import pytest


@pytest.fixture
def empty_dialogue_state():
    """Create an empty dialogue state for testing."""
    from soni.core.types import DialogueState
    return create_empty_dialogue_state()
```

**Archivo:** `tests/factories.py`

```python
"""Test factories for creating test objects."""
from typing import Any


def make_dialogue_state(**overrides: Any) -> dict:
    """Create a DialogueState with defaults, allowing overrides."""
    defaults = {
        "flow_stack": [],
        "flow_slots": {},
        "user_message": "",
        "last_response": "",
        "messages": [],
        "flow_state": "idle",
        "waiting_for_slot": None,
        "commands": [],
        "response": None,
        "action_result": None,
        "turn_count": 0,
        "metadata": {},
    }
    return {**defaults, **overrides}


def make_flow_context(**overrides: Any) -> dict:
    """Create a FlowContext with defaults, allowing overrides."""
    import uuid
    defaults = {
        "flow_id": str(uuid.uuid4()),
        "flow_name": "test_flow",
        "flow_state": "active",
        "current_step": None,
        "outputs": {},
        "started_at": 0.0,
    }
    return {**defaults, **overrides}
```

### TDD Cycle (MANDATORY for new features)

N/A - This is a setup task, not a feature implementation.

### Exception: Test-After

**Reason for test-after:**
- [x] Other: Setup/infrastructure task - no code to test

### Criterios de Éxito

- [ ] `archive/src/soni/` contains old code
- [ ] `archive/tests/` contains old tests
- [ ] `src/soni/` has empty directory structure
- [ ] `tests/` has empty directory structure
- [ ] Git commit with archive complete

### Validación Manual

```bash
# Verify archive exists
ls archive/src/soni/
ls archive/tests/

# Verify new structure is empty
ls src/soni/

# Verify git status
git status
```

### Referencias

- `REWRITE_PLAN.md` - Full rewrite plan

### Notas Adicionales

Keep archive for at least 3 months after rewrite is complete. Reference for edge cases and implementation details.
