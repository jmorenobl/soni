# Slow Tests Marker

## Objetivo

Identificar y marcar tests lentos (>3s) con `@pytest.mark.slow` para excluirlos del flujo de desarrollo rápido.

## Tests Marcados como Slow

### test_dm_runtime.py (7 tests)

Estos tests son lentos porque crean grafos completos con checkpointer SQLite:

| Test | Duración | Razón |
|------|----------|-------|
| `test_state_persistence_basic` | ~11.7s | Crea graph + checkpointer + múltiples invocaciones |
| `test_state_isolation_basic` | ~11.0s | Crea graph + checkpointer + múltiples sesiones |
| `test_execute_linear_flow_basic` | ~7.4s | Ejecuta flow completo con checkpointer |
| `test_handle_action_error` | ~5.9s | Graph execution con error handling |
| `test_execute_flow_with_action_basic` | ~5.1s | Ejecuta flow con action |
| `test_handle_missing_slot` | ~4.8s | Graph execution con slots |
| `test_handle_nlu_error` | ~3.5s | Graph execution con NLU mock |

**Total tiempo**: ~49.4s de los 64s del test suite original

### test_performance_optimizations.py (2 tests)

Estos tests son lentos porque esperan TTL expiration:

| Test | Duración | Razón |
|------|----------|-------|
| `test_scoping_cache_ttl_expiry` | ~1.1s | `await asyncio.sleep(1.1)` para TTL |
| `test_nlu_cache_ttl_expiry` | ~1.1s | `await asyncio.sleep(1.1)` para TTL |

### test_normalizer.py (1 test)

| Test | Duración | Razón |
|------|----------|-------|
| `test_normalizer_cache_ttl_expiry` | ~1.1s | `await asyncio.sleep(1.1)` para TTL |

## Configuración

### pyproject.toml

```toml
markers = [
    "integration: marks tests as integration tests",
    "performance: marks tests as performance tests",
    "slow: marks tests as slow (>3s) (deselect with '-m \"not slow\"')",
]
```

### Makefile

```makefile
# Fast unit tests (desarrollo diario)
test:
    uv run pytest -m "not integration and not performance and not slow" -n auto

# Todos los unit tests (incluye slow)
test-unit:
    uv run pytest -m "not integration and not performance" -n auto

# Solo tests lentos
test-slow:
    uv run pytest -m slow -n auto

# CI/CD (todos menos performance)
test-ci:
    uv run pytest -m "not performance" -n auto

# Todos los tests
test-all:
    uv run pytest -n auto
```

## Impacto en Velocidad

### Antes (con slow tests)

```bash
$ make test
512 passed, 54 deselected in 64.52s (1:04)
```

### Después (sin slow tests)

```bash
$ make test
502 passed, 64 deselected in 8.17s
```

**Mejora**: 87% más rápido (64s → 8s) 🚀

## Breakdown de Tests

| Categoría | Cantidad | Comando |
|-----------|----------|---------|
| **Fast unit** | 502 | `make test` (8s) |
| **Slow unit** | 10 | `make test-slow` (~50s) |
| **Total unit** | 512 | `make test-unit` (~60s) |
| **Integration** | 43 | `make test-integration` |
| **Performance** | 11 | `make test-performance` |
| **Total** | 566 | `make test-all` |

## Uso Recomendado

### Desarrollo Diario

```bash
# Tests rápidos durante desarrollo
make test  # 8 segundos ✅
```

### Antes de Commit

```bash
# Todos los unit tests
make test-unit  # ~60 segundos
```

### Antes de PR

```bash
# Unit + Integration
make test-ci
```

### Antes de Release

```bash
# Todos los tests
make test-all
```

## Verificación

```bash
# Ver tests marcados como slow
uv run pytest --collect-only -m slow -q

# Resultado:
# 10/566 tests collected (556 deselected)

# Ver tests excluidos de make test
uv run pytest --collect-only -m "not integration and not performance and not slow" -q

# Resultado:
# 502/566 tests collected (64 deselected)
```

## Tests Específicos Marcados

### tests/unit/test_dm_runtime.py

```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_state_persistence_basic(sample_config, tmp_path):
    ...

@pytest.mark.slow
@pytest.mark.asyncio
async def test_state_isolation_basic(sample_config, tmp_path):
    ...

@pytest.mark.slow
@pytest.mark.asyncio
async def test_execute_linear_flow_basic(sample_config):
    ...

@pytest.mark.slow
@pytest.mark.asyncio
async def test_handle_action_error(sample_config):
    ...

@pytest.mark.slow
@pytest.mark.asyncio
async def test_execute_flow_with_action_basic(sample_config):
    ...

@pytest.mark.slow
@pytest.mark.asyncio
async def test_handle_missing_slot(sample_config):
    ...

@pytest.mark.slow
@pytest.mark.asyncio
async def test_handle_nlu_error(sample_config):
    ...
```

### tests/unit/test_performance_optimizations.py

```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_nlu_cache_ttl_expiry():
    ...

@pytest.mark.slow
def test_scoping_cache_ttl_expiry():
    ...
```

### tests/unit/test_normalizer.py

```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_normalizer_cache_ttl_expiry():
    ...
```

## Beneficios

1. **Desarrollo más rápido**: 8s vs 64s (87% mejora)
2. **Feedback inmediato**: Loop de desarrollo más corto
3. **Tests organizados**: Clara separación por velocidad
4. **CI/CD flexible**: Ejecutar solo lo necesario en cada etapa
5. **Cobertura completa**: Nada se pierde, solo se organiza

## Comandos Útiles

```bash
# Ver duración de tests
uv run pytest -m "not integration and not performance" --durations=20

# Ejecutar un solo test lento
uv run pytest -k test_state_persistence_basic -v

# Ejecutar todos los slow tests
make test-slow

# Ver tiempo total con slow tests
make test-unit
```

## Consideraciones

### ¿Por Qué No Optimizar los Tests Lentos?

Los tests de `test_dm_runtime.py` son lentos porque:
- Crean grafos LangGraph completos (no mockeable fácilmente)
- Usan checkpointer SQLite real (necesario para validar persistencia)
- Ejecutan flujos completos end-to-end (valor del test)

**Son lentos por diseño** - validan comportamiento real del sistema.

### Alternativa: Paralelización

Con `pytest-xdist`, los 10 tests lentos se distribuyen en cores:
- Sin paralelizar: ~50s
- Con `-n auto`: ~15-20s (depende de cores)

Pero aún así, para desarrollo rápido, mejor excluirlos.

## Conclusión

La estrategia de marcar tests lentos permite:
- ✅ Desarrollo rápido (8s)
- ✅ Tests completos cuando importa (60s)
- ✅ CI/CD flexible
- ✅ Ninguna pérdida de cobertura

**Resultado**: Mejor experiencia de desarrollo sin comprometer calidad.
