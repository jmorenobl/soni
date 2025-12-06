# Análisis de Warnings en Tests

## Warnings Identificados

### 1. ResourceWarning: unclosed database (SQLite) ⚠️ CRÍTICO
**Ubicación**: `tests/unit/test_dm_persistence.py:79`
**Problema**: `test_factory_strategy_pattern` crea un checkpointer SQLite pero no lo cierra
**Impacto**: Conexiones de base de datos no cerradas, posibles leaks de recursos

**Solución**: Agregar cleanup al final del test:
```python
# Cleanup SQLite checkpointer
if sqlite_cm is not None:
    await sqlite_cm.__aexit__(None, None, None)
```

### 2. RuntimeWarning: coroutine never awaited ⚠️ CRÍTICO
**Ubicación**: `tests/integration/test_streaming_endpoint.py:263`
**Problema**: `mock_stream_nlu_error` es una coroutine pero se está usando como función síncrona
**Impacto**: Coroutine nunca se ejecuta, puede causar comportamiento inesperado

**Solución**: El mock debe ser una función async que retorna AsyncGenerator, no una coroutine directamente.

### 3. DeprecationWarning: Pydantic/Starlette/aiohttp ⚠️ MENOR
**Ubicación**: Dependencias externas
**Problema**: Warnings de librerías de terceros (Pydantic V2, Starlette, aiohttp)
**Impacto**: No podemos controlarlos directamente, pero podemos suprimirlos en tests

**Solución**: Agregar filtros de warnings en `pytest.ini` o `conftest.py`:
```python
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="starlette")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="aiohttp")
```

## Prioridad de Fixes

1. **ALTA**: ResourceWarning (SQLite) - Leaks de recursos
2. **ALTA**: RuntimeWarning (coroutine) - Comportamiento incorrecto
3. **BAJA**: DeprecationWarnings externos - Solo ruido, no afectan funcionalidad

## Plan de Acción

1. Fix `test_factory_strategy_pattern` - Agregar cleanup de SQLite
2. Fix `test_streaming_endpoint_nlu_error` - Corregir mock de coroutine
3. (Opcional) Suprimir warnings de dependencias externas en conftest.py
