# Test Organization

## Test Categories

Los tests están organizados en tres categorías con markers de pytest:

### 1. Unit Tests (Por defecto)
- **Ubicación**: `tests/unit/`
- **Marker**: Sin marker especial
- **Ejecución**: `make test`
- **Descripción**: Tests rápidos que no requieren LLM real ni I/O externo
- **Cantidad**: ~531 tests

### 2. Integration Tests
- **Ubicación**: `tests/integration/` + algunos en `tests/unit/test_runtime_streaming.py`
- **Marker**: `@pytest.mark.integration`
- **Ejecución**: `make test-integration`
- **Descripción**: Tests que integran múltiples componentes y pueden hacer llamadas reales al LLM
- **Cantidad**: ~13 tests en integration + 5 en streaming

### 3. Performance Tests
- **Ubicación**: `tests/performance/`
- **Marker**: `@pytest.mark.performance`
- **Ejecución**: `make test-performance`
- **Descripción**: Tests de rendimiento con métricas de latencia, throughput, memoria y CPU
- **Cantidad**: ~8 tests

## Comandos Make Disponibles

```bash
# Tests unitarios únicamente (rápido, ~1-2 min)
make test

# Todos los tests (puede tardar 5+ minutos)
make test-all

# Solo tests de integración
make test-integration

# Solo tests de performance
make test-performance

# Unit + Integration (sin performance) - ideal para CI
make test-ci
```

## Estado Actual

### Unit Tests: ✅ 531/531 passing (100%)
- Tiempo de ejecución: ~76 segundos
- Coverage: 86.74%
- Todos los tests unitarios pasan correctamente

### Integration Tests: ⚠️ ~5 failing (flaky)
- Tests e2e que dependen de respuestas del LLM real
- Pueden fallar por la naturaleza no determinística de los LLMs
- DSPy configurado correctamente con OpenAI API key

### Performance Tests: ⚠️ Variable
- Dependen de recursos del sistema
- Thresholds pueden necesitar ajuste según entorno

## Uso en CI/CD

Para CI/CD, se recomienda:

```bash
# Ejecutar unit + integration tests
make test-ci

# O solo unit tests para feedback rápido
make test
```

## Marcado de Tests

### Tests en tests/integration/
Todos están marcados con `@pytest.mark.integration`:
- test_e2e.py
- test_output_mapping.py
- test_conditional_compiler.py
- test_linear_compiler.py
- test_scoping_integration.py
- test_api_endpoints.py
- test_dialogue_flow.py
- test_graph_builder.py
- test_validator_registry_pipeline.py
- test_action_registry_compiler.py
- test_runtime_api.py
- test_streaming_endpoint.py
- test_normalizer_integration.py

### Tests en tests/unit/test_runtime_streaming.py
También marcados como `@pytest.mark.integration` porque hacen llamadas reales al LLM.

### Tests en tests/performance/
Todos están marcados con `@pytest.mark.performance`:
- test_e2e_performance.py
- test_streaming.py
- test_throughput.py
- test_latency.py

## Configuración

La configuración de markers está en `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
    "performance: marks tests as performance tests (deselect with '-m \"not performance\"')",
]
```

## Beneficios

1. **Feedback rápido**: Los unit tests ejecutan en ~1 minuto
2. **CI eficiente**: Se pueden ejecutar solo tests rápidos en cada commit
3. **Tests costosos opcionales**: Integration y performance tests se ejecutan bajo demanda
4. **Claridad**: Separación clara entre tipos de tests
