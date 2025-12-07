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
**Cuándo aparece**: Cuando se carga un YAML o se crea un `ActionConfig` con el campo `handler`
**Impacto**: ✅ INTENCIONAL - Estamos deprecando este campo intencionalmente
**Solución**: Ya implementado - el warning es correcto y esperado

**¿Qué es el campo `handler`?**

El campo `handler` era la forma antigua (pre-v0.4.0) de especificar dónde estaba la función que implementa una acción:

```yaml
# ❌ FORMA ANTIGUA (deprecada)
actions:
  search_flights:
    handler: "examples.flight_booking.handlers.search_available_flights"  # Python path
    inputs: ["origin", "destination"]
    outputs: ["flights"]
```

**¿Por qué se deprecó?**

Sigue el principio de **Zero-Leakage Architecture**: YAML debe describir QUÉ (semántica), no CÓMO (implementación técnica). Un path de Python es un detalle técnico que no debería estar en YAML.

**Forma nueva (correcta):**

```yaml
# ✅ FORMA NUEVA (correcta)
actions:
  search_flights:
    # No handler field - se registra en Python
    inputs: ["origin", "destination"]
    outputs: ["flights"]
```

```python
# ✅ Registro en Python (handlers.py)
@ActionRegistry.register("search_flights")
async def search_available_flights(
    origin: str,
    destination: str,
) -> dict[str, Any]:
    return {"flights": [...]}
```

**¿Dónde aparece el warning?**

1. **En tests intencionales**: `test_action_handler_requires_registry_no_fallback` crea un `ActionConfig` con `handler` para verificar que:
   - El warning se emite ✅
   - El handler path se ignora ✅
   - Solo funciona si está en ActionRegistry ✅

2. **En configuraciones legacy**: Si alguien carga un YAML antiguo con `handler` field

**Código que emite el warning**:
```python
# src/soni/core/config.py:504-515
def model_post_init(self, __context: Any) -> None:
    """Warn if handler field is used (deprecated)."""
    if self.handler is not None:
        warnings.warn(
            f"Action handler paths are deprecated and will be removed in v0.3.0. "
            f"Use @ActionRegistry.register() to register actions in Python code. "
            f"Handler path '{self.handler}' will be ignored.",
            DeprecationWarning,
            stacklevel=2,
        )
```

**Estado**: ✅ CORRECTO - Este warning es intencional y correcto. Indica que alguien está usando la forma antigua y debe migrar a `@ActionRegistry.register()`.

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
