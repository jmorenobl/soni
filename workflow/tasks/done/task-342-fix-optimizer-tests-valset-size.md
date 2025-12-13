## Task: 342 - Fix Optimizer Tests Valset Size

**ID de tarea:** 342
**Hito:** Test Configuration Fixes
**Dependencias:** Ninguna
**Duración estimada:** 1-2 horas

### Objetivo

Corregir los tests de optimizadores que fallan porque el valset es demasiado pequeño (1 ejemplo). El optimizador MIPROv2 requiere un valset de al menos el tamaño del minibatch.

### Contexto

**Problema identificado:**
- Los tests de optimización fallan con: `RuntimeError: Optimization failed: Minibatch size cannot exceed the size of the valset. Valset size: 1.`
- El optimizador MIPROv2 tiene un minibatch size por defecto que es mayor que 1
- Los tests están usando un valset de solo 1 ejemplo

**Tests afectados:**
- `test_optimize_soni_du_returns_module_and_metrics`
- `test_optimize_soni_du_saves_module`
- `test_optimize_soni_du_integration`

**Referencias:**
- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 3
- `tests/integration/test_optimizers_integration.py`
- `src/soni/du/optimizers.py` - Configuración de MIPROv2

### Entregables

- [ ] Los 3 tests de optimizadores pasan sin errores
- [ ] El valset tiene al menos el tamaño del minibatch
- [ ] La configuración del optimizador es correcta para tests
- [ ] Los tests son rápidos y no requieren muchos ejemplos

### Implementación Detallada

#### Paso 1: Investigar el problema

**Archivo(s) a revisar:**
- `tests/integration/test_optimizers_integration.py`
- `src/soni/du/optimizers.py` - Configuración de MIPROv2

**Acciones:**
1. Verificar qué tamaño de valset están usando los tests
2. Verificar qué minibatch size está usando MIPROv2 por defecto
3. Identificar la configuración mínima necesaria

**Comando de debug:**
```bash
uv run pytest tests/integration/test_optimizers_integration.py::test_optimize_soni_du_returns_module_and_metrics -v --tb=long -s
```

#### Paso 2: Aumentar tamaño del valset

**Archivo(s) a modificar:** `tests/integration/test_optimizers_integration.py`

**Opciones:**
1. **Opción A**: Aumentar el valset a al menos 4-5 ejemplos (recomendado)
2. **Opción B**: Configurar el optimizador para usar un minibatch size más pequeño en tests

**Código esperado:**
```python
# Opción A: Aumentar valset
val_examples = [
    # Al menos 4-5 ejemplos diferentes
    Example(...),
    Example(...),
    Example(...),
    Example(...),
]

# Opción B: Configurar minibatch size más pequeño
optimizer = MIPROv2(...)
optimizer.compile(..., num_trials=1, auto=None, minibatch_size=1)
```

#### Paso 3: Configurar optimizador para tests

**Archivo(s) a modificar:** `src/soni/du/optimizers.py` o `tests/integration/test_optimizers_integration.py`

**Verificaciones:**
- El optimizador debe aceptar configuración de minibatch size
- Los tests deben configurar el optimizador apropiadamente
- La configuración debe ser compatible con valsets pequeños

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_optimizers_integration.py`

**Tests que deben pasar:**
```python
async def test_optimize_soni_du_returns_module_and_metrics(...):
    # Debe pasar después de corregir valset size

async def test_optimize_soni_du_saves_module(...):
    # Debe pasar después de corregir valset size

async def test_optimize_soni_du_integration(...):
    # Debe pasar después de corregir valset size
```

### Criterios de Éxito

- [ ] Los 3 tests de optimizadores pasan sin errores
- [ ] No hay `RuntimeError` sobre valset size
- [ ] Los tests son rápidos (< 30 segundos cada uno)
- [ ] La configuración del optimizador es apropiada para tests
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**
```bash
# Ejecutar tests de optimizadores
uv run pytest tests/integration/test_optimizers_integration.py -v

# Ejecutar test específico
uv run pytest tests/integration/test_optimizers_integration.py::test_optimize_soni_du_returns_module_and_metrics -v
```

**Resultado esperado:**
- Los tests pasan sin errores de valset size
- El optimizador se ejecuta correctamente con la configuración de test

### Referencias

- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 3
- `src/soni/du/optimizers.py` - Implementación del optimizador
- `tests/integration/test_optimizers_integration.py` - Tests actuales
- Documentación de MIPROv2 en DSPy

### Notas Adicionales

- Este es un problema de configuración de tests, no del código de producción
- Los tests deben ser rápidos, así que no usar demasiados ejemplos
- Considerar usar `minibatch_size=1` en tests para permitir valsets pequeños
- Verificar que la configuración no afecta la funcionalidad real del optimizador
