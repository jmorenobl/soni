## Task: TD-001 - Remove Redundant cast() Calls

**ID de tarea:** TD-001
**Fase:** Phase 1 - Quick Wins
**Prioridad:** 🔴 HIGH
**Dependencias:** Ninguna
**Duración estimada:** 1 hora

### Objetivo

Eliminar todas las llamadas redundantes a `cast()` identificadas por mypy en el codebase, reduciendo el ruido en el código y mejorando la seguridad de tipos.

### Contexto

El análisis de deuda técnica identificó 25+ instancias de `cast()` que son redundantes o enmascaran problemas del sistema de tipos. Mypy confirma que varios casts son innecesarios porque el tipo ya es correcto. Estas llamadas añaden complejidad visual sin aportar valor.

**Archivos afectados:**
- `src/soni/du/base.py` (líneas 38, 43, 47, 51) - Casts redundantes a "T"
- `src/soni/compiler/subgraph.py` (líneas 118, 124) - `cast(str, END)` innecesario
- `src/soni/dm/nodes/orchestrator.py` (líneas 59, 68, 97, 113) - Casts en dicts
- `src/soni/dm/nodes/understand.py` (líneas 123, 124, 179, 183, 189, 198)

### Entregables

- [ ] Eliminar casts redundantes confirmados por mypy en `du/base.py`
- [ ] Eliminar `cast(str, END)` en `compiler/subgraph.py`
- [ ] Evaluar y eliminar casts innecesarios en `orchestrator.py`
- [ ] Evaluar y eliminar casts innecesarios en `understand.py`
- [ ] Pasar mypy sin nuevos errores

### Implementación Detallada

#### Paso 1: Eliminar casts en `du/base.py`

**Archivo(s) a modificar:** `src/soni/du/base.py`

**Antes:**
```python
return cast(T, result)  # líneas 38, 43, 47, 51
```

**Después:**
```python
return result  # El tipo T ya está inferido correctamente
```

**Explicación:**
- Mypy reporta `Redundant cast to "T"` - el tipo genérico ya está correctamente inferido
- Eliminar sin cambiar comportamiento

#### Paso 2: Eliminar casts en `compiler/subgraph.py`

**Archivo(s) a modificar:** `src/soni/compiler/subgraph.py`

**Antes:**
```python
cast(str, END)  # líneas 118, 124
```

**Después:**
```python
END  # END ya es de tipo str desde langgraph.constants
```

**Explicación:**
- `END` es una constante str de LangGraph
- No necesita cast explícito

#### Paso 3: Evaluar casts en `orchestrator.py` y `understand.py`

**Archivo(s) a modificar:**
- `src/soni/dm/nodes/orchestrator.py`
- `src/soni/dm/nodes/understand.py`

**Estrategia:**
1. Ejecutar `mypy src/soni/dm/nodes/orchestrator.py src/soni/dm/nodes/understand.py` para identificar casts redundantes
2. Para casts que mypy NO marca como redundantes pero trabajan con dicts copiados de TypedDict:
   - Opción A: Crear un tipo intermedio `WorkingState` para operaciones mutables
   - Opción B: Usar `TypedDict(total=False)` para campos opcionales
   - Opción C: Mantener el cast con comentario explicativo si es necesario para claridad

**Código de referencia para tipo intermedio (Opción A):**
```python
# En core/types.py o inline
class WorkingState(TypedDict, total=False):
    """Estado mutable intermedio para operaciones de nodo."""
    flow_stack: list[FlowContext]
    flow_slots: dict[str, dict[str, Any]]
    # ... otros campos que se manipulan
```

### Exception: Test-After

**Reason for test-after:**
- [x] Legacy code retrofit

**Justification:**
Esta tarea elimina código redundante sin cambiar comportamiento. Los tests existentes deben seguir pasando sin modificación. No se añade nueva funcionalidad.

### Criterios de Éxito

- [ ] `uv run mypy src/soni/` no reporta "Redundant cast" errors
- [ ] Todos los tests pasan: `uv run pytest tests/ -v`
- [ ] No se introducen nuevos errores de tipo
- [ ] El código es más limpio y legible

### Validación Manual

**Comandos para validar:**

```bash
# Verificar eliminación de redundant casts
uv run mypy src/soni/du/base.py src/soni/compiler/subgraph.py --show-error-codes

# Verificar que no hay regresiones
uv run mypy src/soni/ --show-error-codes

# Ejecutar tests
uv run pytest tests/ -v

# Verificar linting
uv run ruff check src/soni/
```

**Resultado esperado:**
- Sin errores "Redundant cast" en mypy
- Todos los tests pasan
- Sin nuevos errores de linting

### Referencias

- [Technical Debt Analysis](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/technical-debt-analysis.md#L74-92)
- [Python typing.cast documentation](https://docs.python.org/3/library/typing.html#typing.cast)

### Notas Adicionales

- Los casts en orchestrator.py y understand.py pueden requerir más análisis si están cubriendo problemas reales de tipos
- Si un cast no es redundante pero es confuso, considerar añadir un comentario explicativo
- Priorizar la seguridad de tipos sobre la brevedad del código
