## Task: TD-004 - Fix Mypy Errors in dataset/slot_extraction.py

**ID de tarea:** TD-004
**Fase:** Phase 1 - Quick Wins
**Prioridad:** 🔴 HIGH
**Dependencias:** Ninguna
**Duración estimada:** 30 minutos

### Objetivo

Corregir los errores de tipos reportados por mypy en `dataset/slot_extraction.py` para mantener la integridad del sistema de tipos.

### Contexto

Mypy reporta dos errores de tipos en este archivo que deben corregirse para mantener la calidad del codebase:

```
src/soni/dataset/slot_extraction.py:92: error: List item incompatible type
src/soni/dataset/slot_extraction.py:127: error: Argument incompatible type
```

### Entregables

- [ ] Corregir error de tipo en línea 92 (List item incompatible)
- [ ] Corregir error de tipo en línea 127 (Argument incompatible)
- [ ] Mypy pasa sin errores en este archivo

### Implementación Detallada

#### Paso 1: Investigar y corregir línea 92

**Archivo(s) a modificar:** `src/soni/dataset/slot_extraction.py`

**Comandos para investigar:**
```bash
# Ver el contexto del error
uv run mypy src/soni/dataset/slot_extraction.py --show-error-context

# Ver el código
sed -n '85,100p' src/soni/dataset/slot_extraction.py
```

**Patrón común de error "List item incompatible":**

```python
# Antes (problema típico):
items: list[SpecificType] = [generic_item]  # generic_item es de tipo más amplio

# Después (soluciones posibles):
# Opción A: Cast explícito si se sabe que es del tipo correcto
items: list[SpecificType] = [cast(SpecificType, generic_item)]

# Opción B: Asegurar que el item sea del tipo correcto en origen
items: list[SpecificType] = [create_specific_item(...)]

# Opción C: Ampliar el tipo de la lista
items: list[BaseType] = [generic_item]
```

**Acción:** Revisar el código específico y aplicar la solución apropiada.

#### Paso 2: Investigar y corregir línea 127

**Comandos para investigar:**
```bash
# Ver el contexto del error
sed -n '120,135p' src/soni/dataset/slot_extraction.py
```

**Patrón común de error "Argument incompatible":**

```python
# Antes (problema típico):
def function(param: SpecificType) -> None: ...
function(generic_value)  # generic_value es de tipo más amplio

# Después (soluciones posibles):
# Opción A: Validar y cast si se sabe que es del tipo correcto
if isinstance(generic_value, SpecificType):
    function(generic_value)

# Opción B: Ampliar la firma del parámetro
def function(param: BaseType) -> None: ...

# Opción C: Transformar el valor antes de pasar
function(SpecificType.from_generic(generic_value))
```

**Acción:** Revisar el código específico y aplicar la solución que mantenga la seguridad de tipos.

### Exception: Test-After

**Reason for test-after:**
- [x] Legacy code retrofit

**Justification:**
Estos son errores de tipos que no cambian la lógica del programa. Los tests existentes de slot extraction deben seguir pasando.

### Criterios de Éxito

- [ ] `uv run mypy src/soni/dataset/slot_extraction.py` pasa sin errores
- [ ] No se introducen regresiones: `uv run pytest tests/unit/dataset/ -v`
- [ ] El código corregido es type-safe sin usar `Any` innecesariamente

### Validación Manual

**Comandos para validar:**

```bash
# Verificar mypy
uv run mypy src/soni/dataset/slot_extraction.py

# Verificar tests del módulo
uv run pytest tests/unit/dataset/ -v

# Verificar mypy global
uv run mypy src/soni/
```

**Resultado esperado:**
- Sin errores de mypy en slot_extraction.py
- Tests pasan

### Referencias

- [Technical Debt Analysis](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/technical-debt-analysis.md#L278-291)
- [Mypy common issues](https://mypy.readthedocs.io/en/stable/common_issues.html)

### Notas Adicionales

- Evitar usar `# type: ignore` como parche - preferir correcciones reales de tipos
- Si el error viene de incompatibilidad con DSPy, documentar la razón
- Considerar si el tipo esperado debería ser más amplio o si el valor proporcionado debería ser más específico
