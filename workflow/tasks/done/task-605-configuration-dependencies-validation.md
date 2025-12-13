## Task: 605 - Configuration and Dependencies Validation

**ID de tarea:** 605
**Hito:** 6 - Final Validation & Cleanup
**Dependencias:** Task 604 (Manual Testing Validation)
**Duración estimada:** 1 hora

### Objetivo

Validar que la configuración de ejemplo carga correctamente y que todas las dependencias están en las versiones correctas.

### Contexto

Es importante verificar que:
- La configuración YAML de ejemplo es válida y carga sin errores
- Todas las dependencias están en las versiones especificadas
- El archivo de lock existe y está actualizado

Referencia: `docs/implementation/99-validation.md` - Secciones 5 y 8: Example Configuration y Dependencies

### Entregables

- [ ] Configuración de ejemplo carga sin errores
- [ ] Todas las dependencias en versiones correctas
- [ ] Archivo uv.lock existe y está actualizado
- [ ] Cualquier problema documentado

### Implementación Detallada

#### Paso 1: Validar Configuración de Ejemplo

**Comando:**
```bash
uv run python -c "
from soni.core.config import SoniConfig
config = SoniConfig.from_yaml('examples/flight_booking/soni.yaml')
print('✅ Configuration valid')
print(f'Model: {config.settings.models.nlu.model}')
"
```

**Explicación:**
- Cargar configuración desde YAML de ejemplo
- Verificar que no hay errores al cargar
- Verificar que los campos esperados están presentes
- Documentar cualquier error

#### Paso 2: Verificar Versiones de Dependencias

**Comando:**
```bash
uv pip list | grep -E "dspy|langgraph|fastapi|pydantic"
```

**Versiones esperadas:**
- dspy >= 3.0.4, < 4.0.0
- langgraph >= 1.0.4, < 2.0.0
- fastapi >= 0.122.0, < 1.0.0
- pydantic >= 2.12.5, < 3.0.0

**Explicación:**
- Verificar que las versiones instaladas cumplen los rangos especificados
- Documentar cualquier discrepancia
- Verificar que no hay conflictos de versiones

#### Paso 3: Verificar Archivo de Lock

**Comando:**
```bash
test -f uv.lock && echo "✅ Lock file exists"
```

**Explicación:**
- Verificar que el archivo uv.lock existe
- Verificar que está actualizado (no hay cambios sin lockear)
- Documentar si falta o está desactualizado

#### Paso 4: Verificar Otras Dependencias Críticas

**Comando:**
```bash
uv pip list
```

**Explicación:**
- Revisar todas las dependencias instaladas
- Verificar que no hay dependencias conflictivas
- Documentar cualquier dependencia inesperada

### Tests Requeridos

**No se requieren tests nuevos**, pero se puede verificar:
- Que los tests existentes siguen pasando con las versiones actuales
- Que la configuración de ejemplo se usa en tests de integración

### Criterios de Éxito

- [ ] Configuración de ejemplo carga sin errores
- [ ] Todas las dependencias principales en versiones correctas
- [ ] Archivo uv.lock existe
- [ ] No hay conflictos de versiones
- [ ] Resultados documentados

### Validación Manual

**Comandos para validar:**
```bash
# Validar configuración
uv run python -c "
from soni.core.config import SoniConfig
config = SoniConfig.from_yaml('examples/flight_booking/soni.yaml')
print('✅ Configuration valid')
print(f'Model: {config.settings.models.nlu.model}')
"

# Verificar dependencias
uv pip list | grep -E "dspy|langgraph|fastapi|pydantic"

# Verificar lock file
test -f uv.lock && echo "✅ Lock file exists"
```

**Resultado esperado:**
- Configuración carga correctamente
- Todas las dependencias en versiones correctas
- Lock file existe

### Referencias

- `docs/implementation/99-validation.md` - Secciones 5 y 8
- `examples/flight_booking/soni.yaml` - Configuración de ejemplo
- `pyproject.toml` - Definición de dependencias
- `uv.lock` - Archivo de lock

### Notas Adicionales

- Si hay problemas con versiones, considerar actualizar `pyproject.toml` y regenerar lock
- Verificar que las versiones son compatibles entre sí
- Documentar cualquier dependencia opcional que se use
