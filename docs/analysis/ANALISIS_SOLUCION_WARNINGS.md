# Análisis: ¿Son las soluciones apropiadas o workarounds?

## 1. ResourceWarning (SQLite) - ✅ SOLUCIÓN APROPIADA

### Solución implementada:
```python
# Cleanup SQLite checkpointer to prevent ResourceWarning
if sqlite_cm is not None:
    await sqlite_cm.__aexit__(None, None, None)
```

### Análisis:
- **✅ Es apropiada**: Es la forma estándar de limpiar recursos que requieren cleanup explícito
- **✅ Sigue best practices**: Los context managers async deben cerrarse explícitamente
- **✅ Consistente con el código**: Otros tests (como `test_create_sqlite_checkpointer`) ya hacen esto
- **✅ No es workaround**: Es la forma correcta de manejar recursos con lifecycle

### Comparación con otros tests:
- `test_create_sqlite_checkpointer` (línea 118-119) ya hace cleanup similar
- Es el patrón estándar para recursos que requieren cleanup

**Conclusión**: ✅ Solución apropiada, no es workaround

---

## 2. RuntimeWarning (coroutine never awaited) - ⚠️ PARCIALMENTE WORKAROUND

### Solución implementada:
```python
async def mock_stream_nlu_error(user_msg: str, user_id: str) -> AsyncGenerator[str, None]:
    raise NLUError("Cannot understand message")
    yield  # Unreachable, but needed for type checker to recognize as AsyncGenerator
```

### Análisis:

#### Problema:
- El warning sugiere que hay una coroutine que nunca se awaita
- El mock es una función async con yield (async generator)
- Cuando se usa con `monkeypatch.setattr`, puede haber confusión

#### Solución actual:
- ✅ Funciona: El mock es un async generator correcto
- ⚠️ El `yield` unreachable es un poco "hacky" pero necesario para type checking
- ⚠️ No es ideal: El yield nunca se ejecuta, solo está para que Python reconozca la función como async generator

#### Alternativas mejores:

**Opción 1: Usar AsyncMock con side_effect** (MÁS APROPIADO)
```python
from unittest.mock import AsyncMock
from collections.abc import AsyncGenerator

mock_stream = AsyncMock(side_effect=lambda *args, **kwargs: _async_generator_that_raises())
```

**Opción 2: Crear helper function** (MÁS LIMPIO)
```python
async def _async_generator_that_raises():
    raise NLUError("Cannot understand message")
    yield  # Unreachable

mock_stream_nlu_error = lambda *args, **kwargs: _async_generator_that_raises()
```

**Opción 3: Usar fixture con AsyncMock** (MÁS PYTHONICO)
```python
@pytest.fixture
def mock_stream_error():
    async def _gen():
        raise NLUError("Cannot understand message")
        yield
    return _gen
```

### Comparación con otros tests:
- `test_streaming_manager.py` usa `async def mock_astream(*args, **kwargs): yield ...` (similar)
- Pero esos mocks sí tienen yield que se ejecuta
- Nuestro caso es especial porque queremos que falle inmediatamente

**Conclusión**: ⚠️ Parcialmente workaround - funciona pero hay formas más elegantes

---

## Recomendación

### Para ResourceWarning:
✅ **Mantener como está** - Es la solución correcta

### Para RuntimeWarning:
⚠️ **Mejorar a Opción 1 o 2** - Usar AsyncMock o helper function sería más apropiado

### ¿Es crítico cambiar?
- **No es crítico**: La solución actual funciona y resuelve el warning
- **Pero mejoraría**: Usar AsyncMock sería más explícito y menos "hacky"
- **Prioridad**: Baja - funciona, pero podríamos mejorarlo en el futuro
