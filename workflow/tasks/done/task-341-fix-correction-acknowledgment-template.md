## Task: 341 - Fix Correction Acknowledgment Template

**ID de tarea:** 341
**Hito:** Bug Fixes - High Priority
**Dependencias:** Ninguna
**Duración estimada:** 3-4 horas

### Objetivo

Corregir el uso del template de acknowledgment cuando se corrige un slot. El test `test_correction_uses_acknowledgment_template` falla porque el sistema no está usando el template `correction_acknowledged`.

### Contexto

**Problema identificado:**
- Cuando el usuario corrige un slot, el sistema debería usar el template `correction_acknowledged: "Got it, I've updated {slot_name} to {new_value}."`
- El test falla porque el sistema muestra resultados de vuelos (como si no hubiera detectado la corrección)
- Esto sugiere que el routing no está yendo a `handle_correction` o que `handle_correction` no está generando el acknowledgment correctamente

**Referencias:**
- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 2.3
- `tests/integration/test_design_compliance_corrections.py::test_correction_uses_acknowledgment_template`
- `src/soni/dm/nodes/handle_correction.py`
- `src/soni/core/config.py` - Configuración de templates
- `docs/design/02-architecture.md` - Especificación de templates

### Entregables

- [ ] El test `test_correction_uses_acknowledgment_template` pasa sin errores
- [ ] `handle_correction` usa el template `correction_acknowledged` cuando está disponible
- [ ] El template se interpola correctamente con `{slot_name}` y `{new_value}`
- [ ] El routing va correctamente a `handle_correction` cuando se detecta una corrección

### Implementación Detallada

#### Paso 1: Investigar el problema

**Archivo(s) a revisar:**
- `src/soni/dm/nodes/handle_correction.py`
- `src/soni/dm/routing.py` - routing después de understand cuando es CORRECTION
- `src/soni/core/config.py` - Configuración de templates
- `src/soni/utils/response_generator.py` - Generación de respuestas

**Acciones:**
1. Ejecutar el test fallido con debug
2. Verificar si el NLU está clasificando correctamente como CORRECTION
3. Verificar si el routing va a `handle_correction`
4. Verificar si `handle_correction` está usando el template

**Comando de debug:**
```bash
uv run pytest tests/integration/test_design_compliance_corrections.py::test_correction_uses_acknowledgment_template -v --tb=long -s
```

#### Paso 2: Verificar configuración de templates

**Archivo(s) a revisar:** `examples/flight_booking/soni.yaml`

**Verificaciones:**
- El template `correction_acknowledged` está definido en la configuración
- El formato del template es correcto: `"Got it, I've updated {slot_name} to {new_value}."`

#### Paso 3: Corregir handle_correction

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_correction.py`

**Verificaciones:**
- El nodo debe leer el template desde la configuración
- Debe interpolar `{slot_name}` y `{new_value}` correctamente
- Debe usar el template en el `last_response`
- Debe tener un fallback si el template no está definido

**Código esperado:**
```python
# handle_correction debe:
1. Obtener template de config.responses.correction_acknowledged
2. Interpolar {slot_name} y {new_value}
3. Usar en last_response
4. Fallback a mensaje genérico si template no existe
```

#### Paso 4: Verificar routing

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

**Verificaciones:**
- `route_after_understand` debe ir a `handle_correction` cuando `message_type="correction"`
- No debe ir a `execute_action` o `generate_response` cuando es corrección

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_design_compliance_corrections.py`

**Test existente que debe pasar:**
```python
async def test_correction_uses_acknowledgment_template(...):
    # Este test ya existe y debe pasar después de la corrección
    # Verifica que se usa el template correction_acknowledged
```

**Tests adicionales a considerar:**
```python
# Test: Corrección sin template definido
async def test_correction_without_template(...):
    """Test que corrección usa fallback cuando template no está definido."""

# Test: Corrección con múltiples slots
async def test_correction_multiple_slots_template(...):
    """Test que corrección maneja correctamente múltiples slots en template."""
```

### Criterios de Éxito

- [ ] `test_correction_uses_acknowledgment_template` pasa sin errores
- [ ] El template `correction_acknowledged` se usa cuando está disponible
- [ ] La interpolación de `{slot_name}` y `{new_value}` funciona correctamente
- [ ] Hay un fallback apropiado cuando el template no está definido
- [ ] El routing va correctamente a `handle_correction` cuando es CORRECTION
- [ ] Todos los tests de integración relacionados pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**
```bash
# Ejecutar test específico
uv run pytest tests/integration/test_design_compliance_corrections.py::test_correction_uses_acknowledgment_template -v

# Ejecutar todos los tests de corrección
uv run pytest tests/integration/ -k correction -v

# Ejecutar suite completa de integración
uv run pytest tests/integration/ -v
```

**Resultado esperado:**
- El sistema usa el template `correction_acknowledged` cuando se corrige un slot
- La respuesta incluye el nombre del slot y el nuevo valor

### Referencias

- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 2.3
- `docs/design/02-architecture.md` - Especificación de templates
- `src/soni/dm/nodes/handle_correction.py` - Implementación actual
- `src/soni/core/config.py` - Configuración de templates
- `examples/flight_booking/soni.yaml` - Configuración de ejemplo

### Notas Adicionales

- Este problema podría ser también del NLU si no está detectando la corrección, pero el error sugiere que el sistema está procesando como si fuera una acción normal
- Verificar que el NLU está clasificando correctamente como CORRECTION en el contexto del test
- El template debe estar definido en la configuración YAML
