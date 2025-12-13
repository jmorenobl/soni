## Task: 004 - Set State Variables for Corrections/Modifications

**ID de tarea:** 004
**Hito:** 10
**Dependencias:** 002 (Create Dedicated Handlers) - puede hacerse en paralelo
**Duración estimada:** 3-4 horas

### Objetivo

Implementar el establecimiento de variables de estado `_correction_slot`, `_correction_value`, `_modification_slot`, y `_modification_value` cuando ocurren correcciones o modificaciones, según el diseño.

### Contexto

**Problema actual:**
- Las variables de estado no se establecen cuando ocurren correcciones/modificaciones
- No se puede usar estas variables en branch conditions o responses como está diseñado

**Comportamiento esperado (según diseño):**
- Cuando ocurre corrección: establecer `_correction_slot` y `_correction_value`
- Cuando ocurre modificación: establecer `_modification_slot` y `_modification_value`
- Estas variables deben estar disponibles para uso en branch conditions y response templates

**Referencias:**
- Diseño: `docs/design/10-dsl-specification/06-patterns.md` (líneas 225-228)
- Inconsistencias: `docs/analysis/DESIGN_IMPLEMENTATION_INCONSISTENCIES.md` - Inconsistencia #4
- Backlog: `docs/analysis/BACKLOG_DESIGN_COMPLIANCE.md` (Fix #4)

### Entregables

- [ ] `_correction_slot` y `_correction_value` se establecen en correcciones
- [ ] `_modification_slot` y `_modification_value` se establecen en modificaciones
- [ ] Variables son accesibles en branch conditions
- [ ] Variables son accesibles en response templates
- [ ] Variables se limpian apropiadamente (al inicio del siguiente turno)
- [ ] Tests pueden verificar que las variables están establecidas

### Implementación Detallada

#### Paso 1: Agregar variables al estado (si no existen)

**Archivo(s) a modificar:** `src/soni/core/state.py` o `src/soni/core/types.py`

**Explicación:**
- Verificar si `DialogueState` incluye estas variables en metadata
- Si no, asegurar que metadata puede contener estas variables
- Las variables pueden ir en `metadata` o directamente en el estado

**Código específico:**

```python
# En DialogueState TypedDict, metadata ya existe
# Las variables pueden ir en metadata:
# metadata["_correction_slot"] = slot_name
# metadata["_correction_value"] = value
```

#### Paso 2: Establecer variables en handle_correction_node

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_correction.py` (cuando se cree en tarea 002)

**Código específico:**

```python
async def handle_correction_node(
    state: DialogueState,
    runtime: Any,
) -> dict:
    # ... código para actualizar slot ...

    # Set state variables
    metadata = state.get("metadata", {}).copy()
    metadata["_correction_slot"] = slot_name
    metadata["_correction_value"] = normalized_value

    # Clear modification variables (if any)
    metadata.pop("_modification_slot", None)
    metadata.pop("_modification_value", None)

    return {
        # ... otros updates ...
        "metadata": metadata,
    }
```

#### Paso 3: Establecer variables en handle_modification_node

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_modification.py` (cuando se cree en tarea 002)

**Código específico:**

```python
async def handle_modification_node(
    state: DialogueState,
    runtime: Any,
) -> dict:
    # ... código para actualizar slot ...

    # Set state variables
    metadata = state.get("metadata", {}).copy()
    metadata["_modification_slot"] = slot_name
    metadata["_modification_value"] = normalized_value

    # Clear correction variables (if any)
    metadata.pop("_correction_slot", None)
    metadata.pop("_correction_value", None)

    return {
        # ... otros updates ...
        "metadata": metadata,
    }
```

#### Paso 4: Limpiar variables al inicio del siguiente turno

**Archivo(s) a modificar:** `src/soni/dm/nodes/understand.py` o donde se inicializa el turno

**Explicación:**
- Las variables deben limpiarse al inicio de cada nuevo turno
- Esto asegura que solo reflejen la corrección/modificación más reciente

**Código específico:**

```python
async def understand_node(
    state: DialogueState,
    runtime: Any,
) -> dict:
    # ... código existente ...

    # Clear correction/modification variables at start of new turn
    metadata = state.get("metadata", {}).copy()
    metadata.pop("_correction_slot", None)
    metadata.pop("_correction_value", None)
    metadata.pop("_modification_slot", None)
    metadata.pop("_modification_value", None)

    return {
        # ... otros updates ...
        "metadata": metadata,
    }
```

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_design_compliance_corrections.py`

**Tests específicos:**

```python
# Estos tests existen pero están skipped - deben pasar después de implementar:
- test_correction_sets_state_variables
- test_modification_sets_state_variables

# Test adicional recomendado:
@pytest.mark.integration
@pytest.mark.asyncio
async def test_state_variables_accessible_in_branch(runtime, skip_without_api_key):
    """Test that correction/modification variables can be used in branch conditions."""
    # Arrange: Create flow with branch that uses _correction_slot
    # Act: Perform correction
    # Assert: Branch condition can access _correction_slot
```

**Nota:** Los tests actuales están skipped porque requieren API para acceder al estado. Puede ser necesario:
1. Implementar API para acceder al estado en tests, o
2. Verificar indirectamente que las variables están establecidas

### Criterios de Éxito

- [ ] `_correction_slot` y `_correction_value` se establecen en correcciones
- [ ] `_modification_slot` y `_modification_value` se establecen en modificaciones
- [ ] Variables se limpian al inicio del siguiente turno
- [ ] Variables son accesibles en branch conditions (verificar con test)
- [ ] Variables son accesibles en response templates (verificar con test)
- [ ] Tests pueden verificar las variables (ya sea directamente o indirectamente)
- [ ] No hay regresiones en tests existentes
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar tests de variables de estado (cuando se implementen)
uv run pytest tests/integration/test_design_compliance_corrections.py::test_correction_sets_state_variables -v

# Verificar que las variables están en el estado
# (Puede requerir agregar logging temporal o API de acceso)
```

**Resultado esperado:**
- Las variables se establecen correctamente
- Las variables están disponibles para uso en branches y responses
- Las variables se limpian apropiadamente

### Referencias

- Diseño: `docs/design/10-dsl-specification/06-patterns.md` (líneas 225-228)
- Análisis: `docs/analysis/DESIGN_IMPLEMENTATION_INCONSISTENCIES.md` (Inconsistencia #4)
- Backlog: `docs/analysis/BACKLOG_DESIGN_COMPLIANCE.md` (Fix #4)
- Código de referencia: `src/soni/core/state.py` (estructura de DialogueState)
- Tests: `tests/integration/test_design_compliance_corrections.py`

### Notas Adicionales

- Esta tarea puede hacerse en paralelo con otras tareas
- Las variables pueden ir en `metadata` del estado (ya existe)
- Considerar si las variables deben persistir más allá de un turno (probablemente no)
- Puede ser necesario agregar API para acceder al estado en tests si no existe
