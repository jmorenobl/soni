## Task: 332 - Agregar Comentarios de Referencia al Diseño en Tests

**ID de tarea:** 332
**Hito:** Fase 3 - Quality Improvements
**Dependencias:** Ninguna
**Duración estimada:** 1 hora
**Prioridad:** 🟢 BAJA

### Objetivo

Agregar comentarios con referencias al diseño en los tests existentes para mejorar trazabilidad entre tests y especificaciones de diseño.

### Contexto

Según el informe de conformidad (`docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md`), agregar referencias al diseño mejora la mantenibilidad y comprensión de los tests.

**Beneficio**: Trazabilidad entre tests y diseño, mejor documentación.

**Impacto**: BAJO - Mejora de calidad y documentación.

### Entregables

- [ ] Comentarios de referencia agregados a tests críticos
- [ ] Formato consistente de referencias
- [ ] Referencias a `docs/design/10-dsl-specification/06-patterns.md` donde aplique
- [ ] Referencias a otros documentos de diseño relevantes

### Implementación Detallada

#### Paso 1: Identificar tests que necesitan referencias

**Archivos a modificar:**
- `tests/unit/test_dm_nodes_handle_correction.py`
- `tests/unit/test_dm_nodes_handle_modification.py`
- `tests/unit/test_handle_confirmation_node.py`
- `tests/unit/test_dm_nodes_handle_digression.py`
- `tests/unit/test_nodes_handle_intent_change.py`
- Otros tests de patrones conversacionales

#### Paso 2: Agregar formato de referencia

**Formato estándar:**

```python
async def test_handle_correction_returns_to_collect_step(...):
    """
    Test correction returns to current step (not restart).

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:59
    Pattern: "Both patterns are handled the same way: update the slot, return to current step"
    """
    # Test implementation
```

#### Paso 3: Agregar referencias a tests existentes

**Archivo(s) a modificar:** `tests/unit/test_dm_nodes_handle_correction.py`

**Ejemplo:**

```python
async def test_handle_correction_returns_to_collect_step(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """
    Correction returns to current step (not restart).

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:54-60
    Pattern: "Correction: User fixes a previously given value → Update slot, return to current step"
    """
    # Existing test code...
```

### TDD Cycle

**Nota**: Esta tarea NO requiere TDD ya que solo agrega comentarios/documentación.

#### Verificación: Tests Siguen Pasando

**Verificar que los tests siguen pasando después de agregar comentarios:**

```bash
uv run pytest tests/unit/ -v
# Expected: PASSED ✅ (comentarios no afectan ejecución)
```

**Commit:**
```bash
git add tests/unit/
git commit -m "docs: add design reference comments to tests"
```

---

### Tests Requeridos

**No se requieren nuevos tests, solo documentación de tests existentes.**

**Formato de referencia a agregar:**

```python
"""
Test description.

Design Reference: docs/design/[path]:[line]
Pattern: "[Description from design]"
"""
```

### Criterios de Éxito

- [ ] Comentarios agregados a tests críticos de patrones conversacionales
- [ ] Formato consistente de referencias
- [ ] Referencias apuntan a documentos de diseño correctos
- [ ] Todos los tests siguen pasando
- [ ] Linting pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Run tests to ensure they still pass
uv run pytest tests/unit/ -v

# Linting
uv run ruff check tests/unit/

# Type checking
uv run mypy tests/unit/
```

**Resultado esperado:**
- Todos los tests pasan (comentarios no afectan ejecución)
- Sin errores de linting o type checking

### Referencias

- `docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md` - Recommendation #1: Add Design Reference Comments
- `docs/design/10-dsl-specification/06-patterns.md` - Especificación de patrones
- `docs/design/05-message-flow.md` - Flujo de mensajes
- `docs/design/04-state-machine.md` - State machine

### Notas Adicionales

- **Formato**: Usar formato consistente para todas las referencias.
- **Líneas específicas**: Incluir números de línea cuando sea posible para referencias precisas.
- **Patrones**: Enfocarse en tests de patrones conversacionales primero.
- **Incremental**: Puede hacerse incrementalmente, no requiere hacer todo de una vez.
