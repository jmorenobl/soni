## Task: 303 - Improve Type Hints for Runtime Parameter Using TYPE_CHECKING

**ID de tarea:** 303
**Hito:** Technical Debt Repayment - MEDIUM
**Dependencias:** Ninguna
**Duración estimada:** 4-6 horas
**Prioridad:** 🟡 MEDIUM - Improves developer experience
**Related DEBT:** DEBT-002

### Objetivo

Reemplazar el uso extensivo de `runtime: Any` en todos los nodos con type hints apropiados usando `TYPE_CHECKING` guards, mejorando el soporte de IDE, type checking estático, y previniendo errores en tiempo de compilación.

### Contexto

**Problema:**
12 archivos de nodos usan `runtime: Any` con comentarios explicativos:
```python
runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
```

**Archivos afectados:**
- `handle_confirmation.py`, `generate_response.py`, `understand.py`, `confirm_action.py`
- `handle_intent_change.py`, `validate_slot.py`, `collect_next_slot.py`
- `handle_correction.py`, `handle_modification.py`, `execute_action.py`
- `handle_error.py`, `handle_digression.py`

**Impacto:**
- ❌ No static type checking
- ❌ Limited IDE autocomplete
- ❌ Refactoring errors not caught early

**Referencias:**
- Technical Debt: `docs/technical-debt.md` (DEBT-002)
- PEP 484 (Type Hints), PEP 563 (Postponed Evaluation)

### Entregables

- [ ] Type alias `NodeRuntime` creado en `src/soni/core/types.py`
- [ ] Todos los 12 nodos actualizados con proper type hints
- [ ] `TYPE_CHECKING` guards implementados para evitar circular imports
- [ ] IDE autocomplete funcionando correctamente
- [ ] Mypy passing sin errores
- [ ] No circular import issues

### Implementación Detallada

#### Paso 1: Crear type alias en core/types.py

**Archivo a modificar:** `src/soni/core/types.py`

**Agregar al inicio del archivo:**

```python
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from langgraph.graph import Runtime
    from soni.core.types import RuntimeContext

    # Type alias for node runtime parameter
    NodeRuntime: TypeAlias = Runtime[RuntimeContext]
else:
    # At runtime, use Any to avoid import overhead
    from typing import Any as NodeRuntime
```

**Exportar en `__all__`:**

```python
__all__ = [
    # ... existing exports ...
    "NodeRuntime",
]
```

#### Paso 2: Actualizar todos los nodos (template)

**Para cada archivo de nodo, aplicar este cambio:**

**BEFORE:**
```python
from typing import Any

async def [node_name](
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
```

**AFTER:**
```python
from soni.core.types import DialogueState, NodeRuntime

async def [node_name](
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
```

#### Paso 3: Actualizar cada nodo específico

**Archivos a modificar (lista completa):**

1. `src/soni/dm/nodes/handle_confirmation.py`
2. `src/soni/dm/nodes/generate_response.py`
3. `src/soni/dm/nodes/understand.py`
4. `src/soni/dm/nodes/confirm_action.py`
5. `src/soni/dm/nodes/handle_intent_change.py`
6. `src/soni/dm/nodes/validate_slot.py`
7. `src/soni/dm/nodes/collect_next_slot.py`
8. `src/soni/dm/nodes/handle_correction.py`
9. `src/soni/dm/nodes/handle_modification.py`
10. `src/soni/dm/nodes/execute_action.py`
11. `src/soni/dm/nodes/handle_error.py`
12. `src/soni/dm/nodes/handle_digression.py`

**Para cada archivo:**
1. Importar `NodeRuntime` desde `soni.core.types`
2. Reemplazar `runtime: Any` con `runtime: NodeRuntime`
3. Eliminar el comentario explicativo (ya no necesario)

#### Paso 4: Verificar con mypy

```bash
uv run mypy src/soni --strict
```

Resolver cualquier error de tipo que aparezca.

### Tests Requeridos

**No se requieren nuevos tests**, pero verificar que todos los existentes pasen:

```bash
uv run pytest tests/ -v
```

### Criterios de Éxito

- [ ] `NodeRuntime` type alias creado en `src/soni/core/types.py`
- [ ] CERO archivos usando `runtime: Any` en src/soni/dm/nodes/
- [ ] IDE autocomplete funciona para `runtime.context`
- [ ] Mypy pasa sin errores en modo strict
- [ ] No circular import errors
- [ ] Todos los tests existentes pasan

### Validación Manual

```bash
# 1. Verify no more "Any" for runtime
grep -r "runtime: Any" src/soni/dm/nodes/ && echo "❌ Found Any" || echo "✅ No Any found"

# 2. Type check
uv run mypy src/soni

# 3. Test
uv run pytest tests/

# 4. Test IDE autocomplete manually
# Open any node file in IDE, type "runtime." and verify autocomplete shows context
```

### Referencias

- **Technical Debt:** `docs/technical-debt.md` (DEBT-002)
- **PEP 484:** Type Hints
- **PEP 563:** Postponed Evaluation of Annotations
- **TYPE_CHECKING:** Python typing module

### Notas Adicionales

**Por qué TYPE_CHECKING:**
- Permite importar tipos solo para type checking, no en runtime
- Evita circular imports
- No overhead en runtime
- IDE y mypy pueden inferir tipos correctamente

**Alternative Considered:**
- String annotations (`"Runtime[RuntimeContext]"`) - menos type-safe
- Forward references - más complejo
- TYPE_CHECKING es la solución recomendada por PEP 484
