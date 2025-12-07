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

### 2. Warnings de Nuestro Código (CONTROLAMOS)

#### 2.1 DeprecationWarning - Action handler paths
**Ubicación**: `src/soni/core/config.py:509`
**Tipo**: `DeprecationWarning`
**Problema**: Campo `handler` en `ActionConfig` está deprecado
**Impacto**: ✅ INTENCIONAL - Estamos deprecando este campo intencionalmente
**Solución**: Ya implementado - el warning es correcto y esperado

**Código afectado**:
```python
# src/soni/core/config.py:509
warnings.warn(
    f"Action handler paths are deprecated and will be removed in v0.3.0. "
    f"Use @ActionRegistry.register() to register actions in Python code. "
    f"Handler path '{self.handler}' will be ignored.",
    DeprecationWarning,
    stacklevel=2,
)
```

**Estado**: ✅ CORRECTO - Este warning es intencional y correcto

## Resumen

| Categoría | Cantidad | Controlamos | Acción Requerida |
|-----------|----------|-------------|------------------|
| Dependencias externas | 4 tipos | ❌ NO | Suprimir en conftest.py (opcional) |
| Nuestro código | 1 tipo | ✅ SÍ | ✅ Ya implementado correctamente |

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
