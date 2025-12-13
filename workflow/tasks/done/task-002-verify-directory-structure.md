## Task: 002 - Verify and Create Directory Structure

**ID de tarea:** 002
**Hito:** Phase 0 - Prerequisites
**Dependencias:** Task 000 (Environment verification)
**Duración estimada:** 15 minutos

### Objetivo

Verify that all required directory structure exists according to the prerequisites document, and create any missing directories with proper `__init__.py` files.

### Contexto

The Soni framework requires a specific directory structure for organizing code into modules (core, du, dm, flow, actions, validation, config, server, cli). While some directories may already exist, we need to verify completeness and ensure all required directories are present with proper Python package structure.

**Reference:** [docs/implementation/00-prerequisites.md](../../docs/implementation/00-prerequisites.md) - Directory Structure section

### Entregables

- [ ] All required source directories verified or created
- [ ] All required test directories verified or created
- [ ] All directories have proper `__init__.py` files
- [ ] Directory structure documented in PROGRESS.md

### Implementación Detallada

#### Paso 1: Verify Source Directory Structure

**Archivo(s) a crear/modificar:** Directory structure and `__init__.py` files

**Estructura requerida:**

```
src/soni/
├── core/           # Core types & interfaces
├── du/             # Dialogue Understanding (NLU)
├── dm/             # Dialogue Management (LangGraph)
├── flow/           # Flow management
├── actions/        # Action registry
├── validation/     # Validator registry
├── config/         # Configuration
├── server/         # FastAPI server
└── cli/            # CLI commands
```

**Comandos a ejecutar:**

```bash
# Create missing directories if needed
mkdir -p src/soni/{core,du,dm,flow,actions,validation,config,server,cli}

# Verify all directories exist
ls -la src/soni/
```

**Explicación:**
- Create all required source directories
- Use brace expansion for efficiency
- Verify all directories were created

#### Paso 2: Verify Test Directory Structure

**Archivo(s) a crear/modificar:** Directory structure

**Estructura requerida:**

```
tests/
├── unit/           # Unit tests
└── integration/    # Integration tests
```

**Comandos a ejecutar:**

```bash
# Create missing test directories if needed
mkdir -p tests/{unit,integration}

# Verify all directories exist
ls -la tests/
```

**Explicación:**
- Create test directories if missing
- Verify structure matches requirements

#### Paso 3: Ensure __init__.py Files Exist

**Archivo(s) a crear/modificar:** `__init__.py` files in each directory

**Script de verificación:**

```python
# scripts/verify_structure.py (temporary script)
import os
from pathlib import Path

required_dirs = [
    "src/soni/core",
    "src/soni/du",
    "src/soni/dm",
    "src/soni/flow",
    "src/soni/actions",
    "src/soni/validation",
    "src/soni/config",
    "src/soni/server",
    "src/soni/cli",
    "tests/unit",
    "tests/integration",
]

for dir_path in required_dirs:
    path = Path(dir_path)
    if not path.exists():
        print(f"❌ Missing: {dir_path}")
        continue

    init_file = path / "__init__.py"
    if not init_file.exists():
        init_file.touch()
        print(f"✅ Created: {init_file}")
    else:
        print(f"✅ Exists: {init_file}")
```

**Comandos a ejecutar:**

```bash
# Run verification script
uv run python scripts/verify_structure.py

# Or manually create missing __init__.py files
touch src/soni/flow/__init__.py  # Example if flow directory is new
```

**Explicación:**
- Ensure each directory has an `__init__.py` file
- Create missing files automatically
- Verify all files exist

#### Paso 4: Document Directory Structure

**Archivo(s) a crear/modificar:** `docs/implementation/PROGRESS.md`

**Contenido esperado:**

```markdown
## Directory Structure Verification - [DATE]

### Source Directories
- ✅ src/soni/core
- ✅ src/soni/du
- ✅ src/soni/dm
- ✅ src/soni/flow
- ✅ src/soni/actions
- ✅ src/soni/validation
- ✅ src/soni/config
- ✅ src/soni/server
- ✅ src/soni/cli

### Test Directories
- ✅ tests/unit
- ✅ tests/integration

### Status
- All directories verified
- All __init__.py files present
```

**Explicación:**
- Document the verification results
- List all directories and their status
- Mark as completed

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_structure.py` (optional verification test)

**Tests específicos a implementar:**

```python
"""Test directory structure exists."""
import os
from pathlib import Path

def test_source_directories_exist():
    """Test that all required source directories exist."""
    # Arrange
    base_path = Path("src/soni")
    required_dirs = ["core", "du", "dm", "flow", "actions", "validation", "config", "server", "cli"]

    # Act & Assert
    for dir_name in required_dirs:
        dir_path = base_path / dir_name
        assert dir_path.exists(), f"Directory {dir_path} does not exist"
        assert dir_path.is_dir(), f"{dir_path} is not a directory"

def test_test_directories_exist():
    """Test that all required test directories exist."""
    # Arrange
    base_path = Path("tests")
    required_dirs = ["unit", "integration"]

    # Act & Assert
    for dir_name in required_dirs:
        dir_path = base_path / dir_name
        assert dir_path.exists(), f"Directory {dir_path} does not exist"
        assert dir_path.is_dir(), f"{dir_path} is not a directory"

def test_init_files_exist():
    """Test that all directories have __init__.py files."""
    # Arrange
    source_dirs = [
        "src/soni/core",
        "src/soni/du",
        "src/soni/dm",
        "src/soni/flow",
        "src/soni/actions",
        "src/soni/validation",
        "src/soni/config",
        "src/soni/server",
        "src/soni/cli",
    ]

    # Act & Assert
    for dir_path in source_dirs:
        init_file = Path(dir_path) / "__init__.py"
        assert init_file.exists(), f"__init__.py missing in {dir_path}"
```

**Nota:** These tests are optional but recommended for CI/CD validation.

### Criterios de Éxito

- [ ] All required source directories exist
- [ ] All required test directories exist
- [ ] All directories have `__init__.py` files
- [ ] Directory structure matches prerequisites document
- [ ] Structure documented in PROGRESS.md
- [ ] Optional tests pass (if implemented)

### Validación Manual

**Comandos para validar:**

```bash
# Verify source directories
ls -la src/soni/

# Verify test directories
ls -la tests/

# Check for __init__.py files
find src/soni -name "__init__.py" | sort
find tests -name "__init__.py" | sort

# Run optional tests
uv run pytest tests/unit/test_structure.py -v
```

**Resultado esperado:**
- All directories listed in prerequisites exist
- All directories have `__init__.py` files
- Directory structure matches the documented structure
- Tests pass (if implemented)

### Referencias

- [docs/implementation/00-prerequisites.md](../../docs/implementation/00-prerequisites.md) - Directory Structure section
- Python package structure documentation

### Notas Adicionales

- Some directories may already exist from previous work
- Only create missing directories, don't delete existing ones
- Ensure `__init__.py` files are empty or contain only package-level imports
- The `flow` directory might be new and need to be created
- If a directory already has content, preserve it and just ensure `__init__.py` exists
