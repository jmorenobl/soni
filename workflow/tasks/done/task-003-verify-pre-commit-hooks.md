## Task: 003 - Verify Pre-Commit Hooks Configuration

**ID de tarea:** 003
**Hito:** Phase 0 - Prerequisites
**Dependencias:** Task 000 (Environment verification)
**Duración estimada:** 15 minutos

### Objetivo

Verify that pre-commit hooks are properly configured and functioning correctly. The project already has pre-commit setup, so this task focuses on verification rather than initial setup.

### Contexto

The project already has pre-commit configured (`.pre-commit-config.yaml` exists and pre-commit is in dependencies). Before starting the refactoring work, we need to verify that:
- Pre-commit is installed and accessible
- Hooks are properly installed in git
- Hooks run correctly and catch issues
- Configuration is appropriate for the refactoring work

This ensures code quality checks will work correctly during the refactoring process.

**Reference:** [docs/implementation/00-prerequisites.md](../../docs/implementation/00-prerequisites.md) - Validation Tools section

### Entregables

- [ ] Pre-commit is installed and accessible
- [ ] `.pre-commit-config.yaml` exists and is valid
- [ ] Hooks are installed in git (`.git/hooks/pre-commit` exists)
- [ ] Hooks run successfully on all files
- [ ] Hooks run correctly on staged files
- [ ] Pre-commit verification documented in PROGRESS.md

### Implementación Detallada

#### Paso 1: Verify Pre-Commit Installation

**Archivo(s) a verificar:** `pyproject.toml`

**Comandos a ejecutar:**

```bash
# Check if pre-commit is in dependencies
grep -i pre-commit pyproject.toml

# Verify pre-commit is installed and accessible
uv run pre-commit --version

# Verify it's in the environment
uv run python -c "import pre_commit; print('✅ Pre-commit available')"
```

**Explicación:**
- Verify pre-commit is listed in `pyproject.toml` dependencies
- Confirm pre-commit command is accessible via `uv run`
- Verify it can be imported in Python environment

#### Paso 2: Verify Configuration File

**Archivo(s) a verificar:** `.pre-commit-config.yaml`

**Comandos a ejecutar:**

```bash
# Verify configuration file exists
ls -la .pre-commit-config.yaml

# Validate configuration syntax
uv run pre-commit validate-config

# Show current configuration
cat .pre-commit-config.yaml
```

**Explicación:**
- Verify `.pre-commit-config.yaml` file exists
- Validate YAML syntax and hook configuration
- Review current hook configuration
- Document what hooks are configured

#### Paso 3: Verify Hooks Installation

**Archivo(s) a verificar:** `.git/hooks/pre-commit`

**Comandos a ejecutar:**

```bash
# Check if hooks are installed
ls -la .git/hooks/pre-commit

# Verify hook is executable
test -x .git/hooks/pre-commit && echo "✅ Hook is executable" || echo "❌ Hook not executable"

# Check hook content (should reference pre-commit)
head -5 .git/hooks/pre-commit
```

**Explicación:**
- Verify pre-commit hook file exists in `.git/hooks/`
- Confirm hook is executable
- Verify hook content references pre-commit
- If not installed, install with `uv run pre-commit install`

#### Paso 4: Test Pre-Commit Hooks

**Archivo(s) a crear/modificar:** None (testing only)

**Comandos a ejecutar:**

```bash
# Test hooks manually on all files
uv run pre-commit run --all-files

# Test hooks on staged files (simulate commit scenario)
# Create a temporary test file with intentional issues
cat > /tmp/test_precommit.py << 'EOF'
# Test file with linting issues
def bad_function(  ):
    x=1+2
    return x
EOF

# Stage the test file
git add /tmp/test_precommit.py 2>/dev/null || true

# Run hooks on staged files (this is what happens on commit)
uv run pre-commit run

# Clean up
git reset HEAD /tmp/test_precommit.py 2>/dev/null || true
rm -f /tmp/test_precommit.py
```

**Explicación:**
- Test hooks run correctly on all files in the repository
- Test hooks run on staged files (simulating a commit scenario)
- Verify hooks catch issues (if test file has problems)
- Note: Some hooks may fail due to broken code in the current state (expected during refactoring)
- Document any issues found

#### Paso 5: Document Pre-Commit Verification

**Archivo(s) a crear/modificar:** `docs/implementation/PROGRESS.md`

**Contenido esperado:**

```markdown
## Pre-Commit Hooks Verification - [DATE]

### Installation
- ✅ Pre-commit installed (version: x.x.x)
- ✅ Pre-commit in pyproject.toml dependencies

### Configuration
- ✅ .pre-commit-config.yaml exists
- ✅ Configuration validated
- ✅ Hooks configured: [list of hooks from config]

### Installation Status
- ✅ Hooks installed in .git/hooks/pre-commit
- ✅ Hook is executable

### Testing
- ✅ Hooks run on all files (some failures expected due to broken code)
- ✅ Hooks run on staged files
- ⚠️ Note: Some hook failures are expected during refactoring

### Status
- Pre-commit hooks verified and working
- Ready for use during refactoring
```

**Explicación:**
- Document verification results
- List configured hooks from the config file
- Note that some failures are expected due to broken code
- Mark verification as completed

### Tests Requeridos

**Archivo de tests:** None (configuration task, hooks are tested manually)

**Nota:** Pre-commit hooks are tested through manual validation. No unit tests required.

### Criterios de Éxito

- [ ] Pre-commit is installed and accessible via `uv run pre-commit`
- [ ] `.pre-commit-config.yaml` file exists and is valid
- [ ] Configuration validates successfully (`pre-commit validate-config`)
- [ ] Hooks are installed in `.git/hooks/pre-commit`
- [ ] Hooks can run on all files (failures due to broken code are acceptable)
- [ ] Hooks can run on staged files
- [ ] Verification documented in PROGRESS.md

### Validación Manual

**Comandos para validar:**

```bash
# Verify pre-commit is installed
uv run pre-commit --version

# Verify configuration file exists and is valid
ls -la .pre-commit-config.yaml
uv run pre-commit validate-config

# Verify hooks are installed
ls -la .git/hooks/pre-commit

# Test hooks on all files (may show failures due to broken code - expected)
uv run pre-commit run --all-files

# If hooks not installed, install them
uv run pre-commit install
```

**Resultado esperado:**
- Pre-commit shows version number
- Configuration file exists and validates
- Pre-commit hook file exists in `.git/hooks/` (or can be installed)
- Hooks can run (some failures expected due to current broken code state)
- Hooks are ready to use during refactoring

### Referencias

- [docs/implementation/00-prerequisites.md](../../docs/implementation/00-prerequisites.md) - Validation Tools section
- [Pre-commit documentation](https://pre-commit.com/)
- [Ruff pre-commit hook](https://github.com/astral-sh/ruff-pre-commit)
- [Mypy pre-commit hook](https://github.com/pre-commit/mirrors-mypy)

### Notas Adicionales

- **Expected Failures**: During refactoring, some hooks may fail due to broken code. This is expected and acceptable. The important thing is that hooks are configured and will work once code is fixed.
- Pre-commit hooks can be bypassed with `git commit --no-verify`, but this should be avoided
- Hooks run automatically on `git commit`, but can be run manually with `pre-commit run`
- If hooks are not installed, run `uv run pre-commit install` to install them
- The `--all-files` flag is useful for running hooks on the entire codebase
- If configuration needs updates during refactoring, we can adjust `.pre-commit-config.yaml`
- Current broken code state may cause hook failures - this is expected and will be resolved during refactoring
