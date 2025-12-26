## Task: TD-002 - Remove Debug Comments from Code

**ID de tarea:** TD-002
**Fase:** Phase 1 - Quick Wins
**Prioridad:** 🟡 MEDIUM
**Dependencias:** Ninguna
**Duración estimada:** 15 minutos

### Objetivo

Eliminar comentarios de debug dejados en el código de producción y, donde sea apropiado, convertirlos en llamadas a `logger.debug()` estructuradas.

### Contexto

Durante el desarrollo se dejaron comentarios de print debug que no deberían estar en código de producción. Estos comentarios reducen la legibilidad y pueden confundir a futuros desarrolladores sobre si deben descomentarlos.

**Ubicación identificada:**
- `src/soni/core/types.py:78` - Print debug comentado para `_merge_flow_slots`

### Entregables

- [ ] Eliminar o convertir el comentario debug en `core/types.py`
- [ ] Buscar y limpiar cualquier otro comentario debug similar en el codebase
- [ ] Si se convierte a logging, asegurar que el logger esté configurado

### Implementación Detallada

#### Paso 1: Limpiar debug en `core/types.py`

**Archivo(s) a modificar:** `src/soni/core/types.py`

**Código actual (línea 78):**
```python
# print(f"DEBUG: _merge_flow_slots called. Current keys: {list(current.keys()) if current else 'None'}, New keys: {list(new.keys()) if new else 'None'}")
```

**Opción A - Eliminar completamente:**
```python
# (eliminar la línea)
```

**Opción B - Convertir a logging estructurado:**
```python
import logging

logger = logging.getLogger(__name__)

# Dentro de la función _merge_flow_slots:
logger.debug(
    "_merge_flow_slots called",
    extra={
        "current_keys": list(current.keys()) if current else None,
        "new_keys": list(new.keys()) if new else None,
    }
)
```

**Recomendación:** Opción A (eliminar) a menos que este debug sea frecuentemente necesario para troubleshooting.

#### Paso 2: Buscar otros comentarios debug

**Comandos de búsqueda:**
```bash
# Buscar prints comentados
rg "# *print\(" src/soni/

# Buscar comentarios DEBUG
rg "# *DEBUG" src/soni/

# Buscar comentarios TODO relacionados con debug
rg "# *TODO.*debug" src/soni/ -i
```

**Acción:** Revisar cada resultado y decidir si eliminar o convertir a logging.

### Exception: Test-After

**Reason for test-after:**
- [x] Legacy code retrofit

**Justification:**
Esta tarea elimina comentarios, no modifica lógica. No requiere tests nuevos.

### Criterios de Éxito

- [ ] No hay comentarios `# print(` en el código
- [ ] No hay comentarios `# DEBUG` de desarrollo
- [ ] Linting pasa sin errores: `uv run ruff check src/soni/`

### Validación Manual

**Comandos para validar:**

```bash
# Verificar que no hay prints comentados
rg "# *print\(" src/soni/

# Verificar que no hay comentarios DEBUG de desarrollo
rg "# *DEBUG:" src/soni/

# Resultado esperado: sin coincidencias (o solo comentarios legítimos)
```

### Referencias

- [Technical Debt Analysis](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/technical-debt-analysis.md#L206-216)
- [Python logging documentation](https://docs.python.org/3/library/logging.html)

### Notas Adicionales

- Si se decide usar logging, seguir el patrón de logging existente en el proyecto
- No eliminar comentarios que explican código complejo - solo eliminar prints de debug
- Considerar añadir una regla de linting para prevenir futuros prints comentados
