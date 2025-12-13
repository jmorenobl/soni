## Task: 005 - Use Response Templates for Corrections/Modifications

**ID de tarea:** 005
**Hito:** 10
**Dependencias:** 002 (Create Dedicated Handlers) - puede hacerse en paralelo
**Duración estimada:** 3-4 horas

### Objetivo

Implementar el uso de templates de respuesta `correction_acknowledged` y `modification_acknowledged` cuando ocurren correcciones o modificaciones, según el diseño.

### Contexto

**Problema actual:**
- Los templates pueden existir en config pero no se usan
- El sistema no reconoce correcciones con estos mensajes
- Los usuarios no reciben feedback de que su corrección fue procesada

**Comportamiento esperado (según diseño):**
- Cuando ocurre corrección: usar template `correction_acknowledged`
- Cuando ocurre modificación: usar template `modification_acknowledged`
- Interpolar `{slot_name}` y `{new_value}` en los templates
- Incluir reconocimiento en la respuesta (puede combinarse con re-muestra de confirmación)

**Referencias:**
- Diseño: `docs/design/10-dsl-specification/02-configuration.md` (líneas 102-110)
- Inconsistencias: `docs/analysis/DESIGN_IMPLEMENTATION_INCONSISTENCIES.md` - Inconsistencia #6
- Backlog: `docs/analysis/BACKLOG_DESIGN_COMPLIANCE.md` (Fix #5)

### Entregables

- [ ] Template `correction_acknowledged` se usa para correcciones
- [ ] Template `modification_acknowledged` se usa para modificaciones
- [ ] Templates se interpolan correctamente con `{slot_name}` y `{new_value}`
- [ ] Usuarios reciben feedback de que corrección/modificación fue procesada
- [ ] Todos los tests relacionados pasan

### Implementación Detallada

#### Paso 1: Cargar templates desde config

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_correction.py` y `handle_modification.py`

**Explicación:**
- Acceder a `config.responses` para obtener los templates
- Usar valores por defecto si los templates no existen

**Código específico:**

```python
async def handle_correction_node(
    state: DialogueState,
    runtime: Any,
) -> dict:
    # ... código para actualizar slot ...

    # Get response template
    config = runtime.context["config"]
    template = None
    if hasattr(config, "responses") and config.responses:
        template = config.responses.get("correction_acknowledged")

    # Use default if template not found
    if not template or not template.get("default"):
        acknowledgment = f"Got it, I've updated {slot_name} to {normalized_value}."
    else:
        # Interpolate template
        template_str = template["default"]
        acknowledgment = template_str.replace("{slot_name}", slot_name)
        acknowledgment = acknowledgment.replace("{new_value}", str(normalized_value))

    # ... resto del código ...
```

#### Paso 2: Incluir reconocimiento en respuesta

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_correction.py` y `handle_modification.py`

**Explicación:**
- El reconocimiento puede incluirse en `last_response`
- Si se vuelve a confirmación, puede combinarse con el mensaje de confirmación

**Código específico:**

```python
    # If returning to confirmation, combine acknowledgment with confirmation message
    if new_state == "ready_for_confirmation":
        confirmation_msg = _generate_confirmation_message(...)
        combined_response = f"{acknowledgment}\n\n{confirmation_msg}"
    else:
        combined_response = acknowledgment

    return {
        # ... otros updates ...
        "last_response": combined_response,
    }
```

#### Paso 3: Implementar helper para cargar templates

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/handle_correction.py`

**Código específico:**

```python
def _get_response_template(
    config: Any,
    template_name: str,
    default_template: str,
    **kwargs: Any,
) -> str:
    """
    Get response template from config and interpolate variables.

    Args:
        config: SoniConfig instance
        template_name: Name of template in config.responses
        default_template: Default template if not found
        **kwargs: Variables to interpolate (e.g., slot_name="origin", new_value="NYC")

    Returns:
        Interpolated template string
    """
    template = None
    if hasattr(config, "responses") and config.responses:
        template_config = config.responses.get(template_name)
        if template_config:
            # Use default or first variation
            if isinstance(template_config, dict):
                template = template_config.get("default")
            elif isinstance(template_config, str):
                template = template_config

    if not template:
        template = default_template

    # Interpolate variables
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"{{{key}}}", str(value))

    return result
```

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_design_compliance_corrections.py`

**Tests específicos que deben pasar:**

```python
# Estos tests ya existen y deben pasar:
- test_correction_uses_acknowledgment_template
- test_modification_uses_acknowledgment_template
```

### Criterios de Éxito

- [ ] `test_correction_uses_acknowledgment_template` pasa
- [ ] `test_modification_uses_acknowledgment_template` pasa
- [ ] Template `correction_acknowledged` se usa para correcciones
- [ ] Template `modification_acknowledged` se usa para modificaciones
- [ ] Templates se interpolan correctamente
- [ ] Usuarios reciben feedback apropiado
- [ ] No hay regresiones en tests existentes
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar tests de templates
uv run pytest tests/integration/test_design_compliance_corrections.py::test_correction_uses_acknowledgment_template -v

# Verificar que las respuestas incluyen reconocimiento
# (Puede requerir logging o inspección manual de respuestas)
```

**Resultado esperado:**
- Los tests pasan
- Las respuestas incluyen reconocimiento usando los templates
- Los templates se interpolan correctamente

### Referencias

- Diseño: `docs/design/10-dsl-specification/02-configuration.md` (líneas 102-110)
- Análisis: `docs/analysis/DESIGN_IMPLEMENTATION_INCONSISTENCIES.md` (Inconsistencia #6)
- Backlog: `docs/analysis/BACKLOG_DESIGN_COMPLIANCE.md` (Fix #5)
- Código de referencia: `src/soni/core/config.py` (estructura de responses)
- Tests: `tests/integration/test_design_compliance_corrections.py`

### Notas Adicionales

- Esta tarea puede hacerse en paralelo con otras tareas
- Los templates pueden tener variaciones - usar la primera o default
- Considerar soporte para i18n si está implementado
- El reconocimiento puede combinarse con otros mensajes (confirmación, etc.)
