## Task: [Task Number] - [Task Name]

**ID de tarea:** [XXX]
**Hito:** [Número de hito]
**Dependencias:** [Lista de tareas previas o "Ninguna"]
**Duración estimada:** [X horas/días]

### Objetivo

[Descripción clara y concisa del objetivo de esta tarea]

### Contexto

[Explicación del contexto: por qué esta tarea es necesaria, cómo encaja en el hito, referencias a ADRs o documentación relevante]

### Entregables

- [ ] [Entregable 1 específico y medible]
- [ ] [Entregable 2 específico y medible]
- [ ] [Entregable 3 específico y medible]

### Implementación Detallada

#### Paso 1: [Nombre del paso]

**Archivo(s) a crear/modificar:** `ruta/al/archivo.py`

**Código específico:**

```python
# Código exacto o estructura esperada
```

**Explicación:**
- [Detalle específico de qué hacer]
- [Detalle específico de cómo hacerlo]
- [Consideraciones importantes]

#### Paso 2: [Nombre del paso]

[Repetir estructura del Paso 1]

### TDD Cycle (MANDATORY for new features)

**This section is MANDATORY for new features. Delete only if test-after exception applies.**

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/[module]/test_[feature].py`

**Failing tests to write FIRST:**

```python
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
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/[module]/test_[feature].py -v
# Expected: FAILED (feature not implemented yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for [feature]"
```

#### Green Phase: Make Tests Pass

**Implement minimal code to pass tests.**

See "Implementación Detallada" section for implementation steps.

**Verify tests pass:**
```bash
uv run pytest tests/unit/[module]/test_[feature].py -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: implement [feature]"
```

#### Refactor Phase: Improve Design

**Refactor implementation while keeping tests green.**

- Add docstrings
- Improve type hints
- Optimize if needed
- Extract helper functions
- Tests must still pass!

**Commit:**
```bash
git add src/
git commit -m "refactor: improve [feature] implementation"
```

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

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_[modulo].py` o `tests/integration/test_[feature].py`

**Tests específicos a implementar:**

```python
# Test 1: [Descripción]
def test_[nombre_descriptivo]():
    """Test que [descripción clara]"""
    # Arrange
    # Act
    # Assert

# Test 2: [Descripción]
def test_[nombre_descriptivo]():
    """Test que [descripción clara]"""
    # Arrange
    # Act
    # Assert
```

### Criterios de Éxito

- [ ] [Criterio medible 1]
- [ ] [Criterio medible 2]
- [ ] [Criterio medible 3]
- [ ] Todos los tests pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Comando 1
# Comando 2
```

**Resultado esperado:**
- [Descripción del resultado esperado]

### Referencias

- [Enlace a ADR relevante]
- [Enlace a documentación]
- [Enlace a código de referencia]

### Notas Adicionales

[Notas sobre edge cases, consideraciones especiales, o información adicional relevante]
