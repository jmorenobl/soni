## Task: TD-003 - Remove Unused Type Ignores

**ID de tarea:** TD-003
**Fase:** Phase 1 - Quick Wins
**Prioridad:** 🟡 MEDIUM
**Dependencias:** Ninguna
**Duración estimada:** 30 minutos

### Objetivo

Eliminar todos los comentarios `# type: ignore` que ya no son necesarios, y auditar los restantes para asegurar que están justificados y documentados.

### Contexto

Mypy reporta comentarios `type: ignore` no utilizados, lo que indica que el problema de tipos subyacente ya fue resuelto o nunca existió. Estos comentarios enmascaran posibles errores de tipos y reducen la efectividad del type checking.

**Ubicación identificada por mypy:**
- `src/soni/config/loader.py:70` - `error: Unused "type: ignore" comment`

### Entregables

- [ ] Eliminar el type ignore no usado en `config/loader.py`
- [ ] Auditar todos los `type: ignore` en el codebase
- [ ] Documentar los type ignores que son necesarios mantener
- [ ] Mypy no reporta "Unused type: ignore" errors

### Implementación Detallada

#### Paso 1: Eliminar type ignore en `config/loader.py`

**Archivo(s) a modificar:** `src/soni/config/loader.py`

**Antes (línea 70):**
```python
return SoniConfig.model_validate(data)  # type: ignore[no-any-return]
```

**Después:**
```python
return SoniConfig.model_validate(data)
```

**Explicación:**
- Mypy indica que este `type: ignore` es innecesario
- Probablemente los tipos de Pydantic fueron actualizados o el contexto de tipado mejoró

#### Paso 2: Auditar todos los type ignores

**Comando de búsqueda:**
```bash
# Encontrar todos los type ignores
rg "# type: ignore" src/soni/ --line-number

# Verificar cuáles son innecesarios con mypy
uv run mypy src/soni/ --warn-unused-ignores
```

**Para cada type ignore encontrado, evaluar:**

1. **¿Es reportado como "Unused"?** → Eliminar
2. **¿Es necesario por limitaciones de mypy/librerías?** → Mantener con comentario explicativo
3. **¿Enmascara un problema real de tipos?** → Corregir el tipo subyacente

**Formato para type ignores necesarios:**
```python
# mypy no puede inferir el tipo de retorno de esta librería externa
result = external_lib.function()  # type: ignore[return-value]
```

#### Paso 3: Crear inventario de type ignores restantes

Si quedan type ignores después de la limpieza, documentar en un comentario cerca del código o en este archivo:

| Archivo | Línea | Razón |
|---------|-------|-------|
| `file.py` | 123 | Librería X no tiene stubs |

### Exception: Test-After

**Reason for test-after:**
- [x] Legacy code retrofit

**Justification:**
Esta tarea mejora la calidad del type checking sin cambiar comportamiento. Los tests existentes validan la funcionalidad.

### Criterios de Éxito

- [ ] `uv run mypy src/soni/ --warn-unused-ignores` no reporta unused ignores
- [ ] Todos los type ignores restantes tienen justificación documentada
- [ ] Todos los tests pasan: `uv run pytest tests/`

### Validación Manual

**Comandos para validar:**

```bash
# Verificar sin unused type ignores
uv run mypy src/soni/ --warn-unused-ignores

# Contar type ignores restantes (para tracking)
rg "# type: ignore" src/soni/ --count

# Verificar que no hay regresiones de tipos
uv run mypy src/soni/

# Ejecutar tests
uv run pytest tests/ -v
```

**Resultado esperado:**
- Sin warnings "Unused type: ignore"
- Número reducido de type ignores
- Todos los tests pasan

### Referencias

- [Technical Debt Analysis](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/technical-debt-analysis.md#L218-232)
- [Mypy --warn-unused-ignores](https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-warn-unused-ignores)

### Notas Adicionales

- Considerar añadir `--warn-unused-ignores` a la configuración de mypy en `pyproject.toml`
- Los type ignores para librerías sin stubs pueden requerir crear stubs locales en el futuro
- Priorizar eliminar type ignores sobre mantenerlos con justificaciones débiles
