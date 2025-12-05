# Explicación de Tests: Skipped vs Deselected

## Cuando ejecutas `make test`

```bash
512 passed, 8 skipped, 50 deselected
```

Hay dos conceptos diferentes:

## 1. Deselected (50 tests) ✅ ESPERADO

**Qué son**: Tests que NO se ejecutan porque no pasan el filtro de markers

**Por qué**: `make test` usa `-m "not integration and not performance"`

**Breakdown**:
- 39 integration tests (en `tests/integration/` y algunos streaming)
- 11 performance tests (en `tests/performance/`)
- **Total**: 50 tests deselected

**Estado**: ✅ Esto es correcto y esperado. Son tests que queremos excluir del run diario.

### Cómo ejecutarlos

```bash
# Solo integration
make test-integration

# Solo performance
make test-performance

# Todos juntos
make test-all
```

## 2. Skipped (8 tests) ✅ INTENCIONAL

**Qué son**: Tests que tienen `@pytest.mark.skip(reason="...")` en el código

**Por qué**: Tienen alternativas con mock (más rápidas) o features no implementadas

### Lista de Tests Skipped

#### En `tests/unit/test_du.py` (5 tests)

1. **test_soni_du_forward_signature**
   - Razón: `"Requires LM configuration - use mocked test instead"`
   - ✅ Alternativa: `test_soni_du_forward_with_mock` (PASA)
   - Estado: **Redundante, mantener skipped**

2. **test_soni_du_aforward**
   - Razón: `"Requires LM configuration - use mocked test instead"`
   - ✅ Alternativa: `test_soni_du_aforward_with_mock` (PASA)
   - Estado: **Redundante, mantener skipped**

3. **test_soni_du_predict**
   - Razón: `"Requires LM configuration - use mocked test instead"`
   - ✅ Alternativa: `test_soni_du_predict_with_mock` (PASA)
   - Estado: **Redundante, mantener skipped**

4. **test_soni_du_forward_with_dummy_lm**
   - Razón: `"DummyLM has limitations with complex Pydantic models"`
   - Estado: **Limitación conocida de DSPy DummyLM**

5. **test_soni_du_integration_real_dspy**
   - Razón: `"Requires DSPy LM configuration and API key"`
   - Estado: **Debería ser @pytest.mark.integration** (ver abajo)

#### En `tests/unit/test_optimizers.py` (3 tests)

6. **test_optimize_soni_du_returns_module_and_metrics**
   - Razón: Requiere LM para entrenamiento (lento)
   - Estado: **Debería ser @pytest.mark.integration**

7. **test_optimize_soni_du_saves_module**
   - Razón: Requiere LM para entrenamiento (lento)
   - Estado: **Debería ser @pytest.mark.integration**

8. **test_optimize_soni_du_integration**
   - Razón: Requiere LM para entrenamiento (lento)
   - Estado: **Debería ser @pytest.mark.integration**

#### En `tests/integration/test_e2e.py` (3 tests)

6. **test_e2e_configuration_loading** (línea 173)
   - Razón: `"Test validates config loading, core functionality tested elsewhere"`

7. **test_e2e_context_switching** (línea 216)
   - Razón: `"Context switching not yet implemented"`

8. **test_e2e_error_recovery** (línea 258)
   - Razón: `"Error recovery behavior needs specification"`

## Análisis

### Tests DU (5 skipped)

**Situación**: Hay versiones "con mock" que SÍ se ejecutan y pasan.

**Razón original**: Los tests sin mock requerían un LM real configurado.

**Estado actual**: Ahora tenemos DSPy configurado con OpenAI en `conftest.py`, así que estos tests PODRÍAN ejecutarse.

**Recomendación**:
```python
# Opción 1: Eliminar los tests con LM real (redundantes)
# Opción 2: Cambiar @pytest.mark.skip por @pytest.mark.integration
```

### Tests E2E (3 skipped)

**Razón válida**: Features no implementadas o redundantes

**Estado**: ✅ Correcto dejarlos skipped hasta implementar las features

## ¿Por Qué Están Skipped?

### Tests DU (5 tests)
**Razón histórica**: Antes no teníamos DSPy configurado en conftest.py
**Razón actual**: Tenemos versiones con mock que son:
- ✅ Más rápidas (no hacen llamadas a LLM)
- ✅ Determinísticas (siempre mismo resultado)
- ✅ No requieren API key
- ✅ Más baratas (sin costo de API)

**Conclusión**: Mantener skipped - las versiones mock son mejores para unit tests

### Tests Optimizers (3 tests)
**Razón**: El entrenamiento de DSPy es:
- ⏱️ Lento (varios minutos por test)
- 💰 Costoso (muchas llamadas a LLM)
- 🎯 Más apropiado para integration tests

**Recomendación**: Convertir a `@pytest.mark.integration` en lugar de skip

### Tests E2E (3 skipped en integration/)
**Razón**: Features no implementadas o tests redundantes
**Estado**: ✅ Correcto mantenerlos skipped

## Recomendaciones

### Opción 1: Mantener Status Quo ✅ RECOMENDADO
- Dejar tests DU skipped (tenemos versiones mock)
- Dejar tests optimizers skipped (lentos, costosos)
- Total unit tests: 512 passing, 8 skipped
- **Beneficio**: Unit tests rápidos y baratos

### Opción 2: Convertir Optimizers a Integration
```python
# En tests/unit/test_optimizers.py
# Cambiar:
@pytest.mark.skip(reason="...")

# Por:
@pytest.mark.integration
```
- **Beneficio**: Validar optimización real con LLM
- **Costo**: Tests más lentos y costosos (API calls)

### Opción 3: Eliminar Tests Redundantes
Eliminar tests de DU con LM real que tienen versión mock:
- Eliminar `test_soni_du_forward_signature` → Usar `test_soni_du_forward_with_mock`
- Eliminar `test_soni_du_aforward` → Usar `test_soni_du_aforward_with_mock`
- Eliminar `test_soni_du_predict` → Usar `test_soni_du_predict_with_mock`
- **Beneficio**: Menos código, menos confusión
- **Resultado**: Solo 5 skipped (optimizers + dummy_lm + integration)

## Resumen

| Tipo | Cantidad | Acción Recomendada |
|------|----------|-------------------|
| **Deselected** | 50 | ✅ Correcto - son integration/performance |
| **Skipped DU** | 5 | 🔧 Eliminar (tenemos versiones mock) |
| **Skipped E2E** | 3 | ✅ Mantener (features no implementadas) |

## Comandos para Investigar

```bash
# Ver todos los tests skipped con razones
uv run pytest --collect-only -m "not integration and not performance" | grep -A 1 "skip"

# Ver solo los skipped (sin deselected)
uv run pytest -v 2>&1 | grep SKIPPED

# Ejecutar los tests skipped forzadamente
uv run pytest tests/unit/test_du.py::test_soni_du_forward --run-skipped
```

## Acción Sugerida

Limpiar los 5 tests duplicados de DU:
1. Eliminar tests con LM real (están skipped)
2. Mantener solo las versiones con mock (más rápidas, determinísticas)
3. Los tests con LLM real ya se cubren en integration tests

Esto dejaría: **0 skipped en unit tests** ✨
