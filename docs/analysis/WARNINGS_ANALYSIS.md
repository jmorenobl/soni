# Análisis de Warnings en Tests

**Fecha**: 2025-12-07
**Contexto**: Análisis de warnings después de implementar fixes para graph recursion

## Categorización de Warnings

### 1. Warnings de Dependencias Externas (NO CONTROLAMOS)

#### 1.1 PydanticDeprecatedSince20 - litellm
**Ubicación**: `.venv/lib/python3.13/site-packages/litellm/types/llms/anthropic.py:531`
**Tipo**: `PydanticDeprecatedSince20`
**Problema**: litellm usa class-based `config` en lugar de `ConfigDict`
**Impacto**: ⚠️ BAJO - No afecta nuestro código, solo ruido en tests
**Solución**: Suprimir en `conftest.py` o esperar actualización de litellm

**Código afectado**: Ninguno (es de litellm)

#### 1.2 DeprecationWarning - Starlette HTTP_422
**Ubicación**: `starlette/_exception_handler.py:59`
**Tipo**: `DeprecationWarning`
**Problema**: `HTTP_422_UNPROCESSABLE_ENTITY` deprecado, usar `HTTP_422_UNPROCESSABLE_CONTENT`
**Impacto**: ⚠️ BAJO - FastAPI/Starlette maneja esto internamente
**Solución**: Esperar actualización de FastAPI o suprimir warning

**Código afectado**: Ninguno (es de Starlette)

#### 1.3 DeprecationWarning - aiohttp enable_cleanup_closed
**Ubicación**: `aiohttp/connector.py:963`
**Tipo**: `DeprecationWarning`
**Problema**: `enable_cleanup_closed` ignorado en Python 3.13
**Impacto**: ⚠️ BAJO - Solo ruido, no afecta funcionalidad
**Solución**: Suprimir o esperar actualización de aiohttp

**Código afectado**: Ninguno (es de aiohttp)

#### 1.4 UserWarning - Pydantic Serializer
**Ubicación**: `pydantic/main.py:464`
**Tipo**: `UserWarning`
**Problema**: Pydantic serializa objetos con campos inesperados (de DSPy/litellm)
**Impacto**: ⚠️ BAJO - No afecta funcionalidad, solo advertencia de serialización
**Solución**: Suprimir o esperar actualización de dependencias

**Código afectado**: Ninguno (es de Pydantic/DSPy)

#### 1.5 ResourceWarning - SQLite Connections
**Ubicación**: Varios (pytest garbage collection)
**Tipo**: `ResourceWarning`
**Problema**: Conexiones SQLite no cerradas durante garbage collection de pytest
**Impacto**: ⚠️ CORREGIDO - Eran fugas reales en tests

**Análisis y Corrección (2025-12-08)**:

Se realizó una auditoría exhaustiva y se encontraron **2 tests con fugas reales**:

1. **`test_builder_warns_if_not_cleaned_up`** - Intencionalmente no llamaba `cleanup()` para verificar el mecanismo de warning, pero no limpiaba después.
   - **Solución**: Agregar `await builder.cleanup()` al final del test después de verificar el flag.

2. **`test_checkpointer_creation_unsupported_backend`** - No llamaba `cleanup()` aunque el backend devuelve None.
   - **Solución**: Agregar `await builder.cleanup()` como buena práctica.

3. **Fixture `graph_builder` en `test_dm_runtime.py`** - Era síncrono y no tenía cleanup.
   - **Solución**: Convertir a async con yield y cleanup automático.

**Verificación post-corrección**:
- ✅ Todos los tests que crean `SoniGraphBuilder` ahora llaman `cleanup()`
- ✅ Todos los tests que crean `RuntimeLoop` llaman `cleanup()`
- ✅ Los fixtures (`runtime_loop`, `sqlite_checkpointer`, `graph_builder`) limpian automáticamente
- ✅ El código de producción siempre llama `cleanup()` en `RuntimeLoop`
- ✅ No hay ResourceWarnings en la ejecución de tests

**Resultado**: Los ResourceWarnings ya no aparecen porque las fugas fueron corregidas.

**Código corregido**:
- `tests/unit/test_dm_graph.py` - `test_builder_warns_if_not_cleaned_up`, `test_checkpointer_creation_unsupported_backend`
- `tests/unit/test_dm_runtime.py` - Fixture `graph_builder`

### 2. Warnings de Nuestro Código (CONTROLAMOS)

**Estado**: ✅ No hay warnings de nuestro código en la ejecución de tests.

El campo `handler` en `ActionConfig` fue completamente eliminado en v0.5.0+ como parte de la limpieza de código legacy antes de v1.0. Las acciones ahora deben registrarse exclusivamente usando `@ActionRegistry.register()` en Python, siguiendo el principio de Zero-Leakage Architecture.

## Resumen

| Categoría | Cantidad | Controlamos | Acción Requerida |
|-----------|----------|-------------|------------------|
| Dependencias externas | 4 tipos | ❌ NO | ✅ Suprimidos en pyproject.toml |
| Nuestro código | 0 tipos | ✅ SÍ | ✅ Fugas corregidas, código legacy eliminado |

## Recomendación

### Opción 1: Suprimir warnings de dependencias (RECOMENDADO)
Añadir a `tests/conftest.py`:

```python
import warnings

# Suprimir warnings de dependencias externas que no controlamos
warnings.filterwarnings(
    "ignore",
    category=PydanticDeprecatedSince20,
    module="litellm",
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="starlette",
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="aiohttp",
)
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Pydantic serializer warnings",
)
```

### Opción 2: Dejar como está
Los warnings no afectan funcionalidad, solo añaden ruido. Podemos dejarlos hasta que las dependencias se actualicen.

## Warnings Críticos

**Ninguno** - Todos los warnings son:
- De dependencias externas (no controlamos)
- O intencionales (deprecación de handler field)

## Conclusión

✅ **No hay warnings críticos en nuestro código**
⚠️ **Warnings de dependencias externas son normales y no afectan funcionalidad**
✅ **El warning de Action handler es intencional y correcto**
