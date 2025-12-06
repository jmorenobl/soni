# Análisis de Tests Skipped

## Resumen Ejecutivo

**Tests Skipped**: 8 tests en total
**Ubicación**: `tests/unit/test_du.py` (5) + `tests/unit/test_optimizers.py` (3)
**Razón principal**: Tests redundantes con versiones mock o tests de optimización lentos

## Desglose Detallado

### Categoría A: Tests DU Redundantes (3 tests) - ELIMINAR

Estos tests están completamente duplicados con versiones mock:

| Test Original (Skipped) | Alternativa con Mock | Estado Mock |
|------------------------|---------------------|-------------|
| `test_soni_du_forward_signature` | `test_soni_du_forward_with_mock` | ✅ PASA |
| `test_soni_du_aforward` | `test_soni_du_aforward_with_mock` | ✅ PASA |
| `test_soni_du_predict` | `test_soni_du_predict_with_mock` | ✅ PASA |

**Análisis**:
- Los tests con mock son mejores: más rápidos, determinísticos, no cuestan dinero
- Los tests con LM real no aportan valor adicional (DSPy ya está testeado)
- Mantenerlos skipped solo crea confusión

**Recomendación**: ❌ **ELIMINAR estos 3 tests**

### Categoría B: Tests con DummyLM Limitado (1 test) - MANTENER SKIP

| Test | Razón |
|------|-------|
| `test_soni_du_forward_with_dummy_lm` | DummyLM no soporta Pydantic models complejos |

**Análisis**:
- Limitación conocida de DSPy DummyLM
- No es un problema de nuestro código
- Alternativa con mock completo ya existe y pasa

**Recomendación**: ✅ **MANTENER skipped** con nota explicativa

### Categoría C: Test de Integración Real (1 test) - RECLASIFICAR

| Test | Estado Actual | Estado Deseado |
|------|---------------|----------------|
| `test_soni_du_integration_real_dspy` | ⏭️ Skipped | 🔗 Integration |

**Análisis**:
- Test válido para validar integración real con DSPy
- Debería ejecutarse como integration test
- Tenemos API key configurada

**Recomendación**: 🔧 **Cambiar a @pytest.mark.integration**

### Categoría D: Tests de Optimización (3 tests) - RECLASIFICAR

| Test | Problema | Solución |
|------|----------|----------|
| `test_optimize_soni_du_returns_module_and_metrics` | Lento (entrenamiento) | → Integration |
| `test_optimize_soni_du_saves_module` | Lento (entrenamiento) | → Integration |
| `test_optimize_soni_du_integration` | Lento (entrenamiento) | → Integration |

**Análisis**:
- Tests valiosos que validan optimización DSPy
- Lentos porque entrenan el modelo (múltiples llamadas LLM)
- No deberían ser unit tests (son lentos)
- Deberían ejecutarse en CI/CD antes de release

**Recomendación**: 🔧 **Cambiar a @pytest.mark.integration**

## Plan de Acción Recomendado

### Paso 1: Eliminar Tests Redundantes (3 tests)
```bash
# En tests/unit/test_du.py, eliminar:
- test_soni_du_forward_signature (línea 48-76)
- test_soni_du_aforward (línea 79-108)
- test_soni_du_predict (línea 111-143)
```

**Resultado**: -3 skipped

### Paso 2: Reclasificar Tests de Optimización (3 tests)
```python
# En tests/unit/test_optimizers.py, cambiar:

@pytest.mark.skip(reason="...")  # ❌ ELIMINAR
@pytest.mark.integration          # ✅ AÑADIR
def test_optimize_soni_du_returns_module_and_metrics():
    ...
```

**Resultado**: -3 skipped, +3 integration tests

### Paso 3: Reclasificar Test de Integración Real (1 test)
```python
# En tests/unit/test_du.py, cambiar:

@pytest.mark.skip(reason="...")  # ❌ ELIMINAR
@pytest.mark.integration          # ✅ AÑADIR
def test_soni_du_integration_real_dspy():
    ...
```

**Resultado**: -1 skipped, +1 integration test

### Paso 4: Mantener DummyLM Test (1 test)
```python
# En tests/unit/test_du.py, mantener:

@pytest.mark.skip(reason="DummyLM has limitations with complex Pydantic models")
def test_soni_du_forward_with_dummy_lm():
    ...
```

**Resultado**: 1 skipped (válido)

## Resultado Esperado Después del Plan

### Antes
```
512 passed, 8 skipped, 50 deselected
```

### Después
```
512 passed, 1 skipped, 57 deselected
```

**Cambios**:
- ❌ 3 tests eliminados (redundantes)
- 🔗 4 tests movidos a integration
- ⏭️ 1 test mantiene skip (DummyLM limitation)

## ¿Ejecutar Este Plan?

### Ventajas
- ✅ Menos confusión (sin tests redundantes)
- ✅ Mejor organización (optimizers en integration)
- ✅ Mayor coverage de integration tests
- ✅ Solo 1 test skipped (con razón válida)

### Desventajas
- ⚠️ Integration tests más lentos (por optimizers)
- ⚠️ Integration tests más costosos (API calls)

### Recomendación Final

**Ejecutar Pasos 1, 2 y 3**: Limpiar redundantes y reclasificar correctamente

**Beneficio neto**:
- Tests unit más limpios
- Integration tests más completos
- Solo 1 skip (con razón válida)
- Total: 512 unit, 43 integration, 11 performance, 1 skipped

## Comandos para Verificar

```bash
# Ver todos los skipped con razones
uv run pytest -v | grep SKIPPED

# Contar tests por categoría
uv run pytest --collect-only -q -m "not integration and not performance" | tail -1
uv run pytest --collect-only -q -m integration | tail -1
uv run pytest --collect-only -q -m performance | tail -1
```
