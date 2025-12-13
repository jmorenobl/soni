## Task: 314 - Tests Unitarios para du/optimizers.py

**ID de tarea:** 314
**Hito:** Tests Unitarios - Cobertura >85% (Fase CRÍTICA)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 1 día

### Objetivo

Implementar tests unitarios para `du/optimizers.py` usando mocks de LLM para tests deterministas. Alcanzar cobertura >85% (actualmente 27%).

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 27%
- **Gap**: 58%
- **LOC**: 84 líneas
- **Tests estimados**: ~7-10 tests
- **Prioridad**: CRÍTICA (pero menor que otros módulos)
- **Nota**: Requiere mocks de LLM para tests deterministas

El módulo maneja optimización DSPy de módulos NLU.

### Entregables

- [ ] Tests para optimize_soni_du con mock LM
- [ ] Tests para evaluación de módulos
- [ ] Tests para convergencia
- [ ] Tests para max iterations
- [ ] Tests para load_optimized_module
- [ ] Cobertura >85% para el módulo

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_du_optimizers.py`

**Tests específicos:**

- [ ] **Optimización** (~4 tests)
  - [ ] test_optimize_soni_du_with_mock_lm
  - [ ] test_optimize_soni_du_evaluation_metric
  - [ ] test_optimize_soni_du_convergence
  - [ ] test_optimize_soni_du_max_iterations

- [ ] **Evaluación** (~2 tests)
  - [ ] test_evaluate_module_with_mock
  - [ ] test_evaluate_module_returns_metrics

- [ ] **Carga de módulos** (~2 tests)
  - [ ] test_load_optimized_module_exists
  - [ ] test_load_optimized_module_not_exists

**Total estimado**: ~8 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `du/optimizers.py`
- [ ] Todos los tests usan mocks de LLM (nunca LLM real)
- [ ] Tests son deterministas
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_du_optimizers.py -v
uv run pytest tests/unit/test_du_optimizers.py \
    --cov=src/soni/du/optimizers \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.7
- `src/soni/du/optimizers.py` - Código fuente

### Notas Adicionales

- **CRÍTICO**: Usar mocks de LLM (DummyLM o similar) para determinismo
- No usar LLM real en tests unitarios
- Enfocarse en lógica de optimización, no en resultados de LLM
- **IMPORTANTE - Consideración de Scope**: Este módulo puede ser complejo de testear debido a la integración con DSPy. Considerar si es más apropiado:
  - Refactorizar el módulo para separar la lógica de optimización de la interacción con DSPy
  - Crear tests de integración en lugar de unitarios para este módulo
  - Extender la duración estimada si se decide testear exhaustivamente

### Ejemplo: Mocking DSPy Language Models

**Para tests deterministas, usar DummyLM de DSPy:**

```python
import pytest
from unittest.mock import MagicMock, patch
import dspy
from soni.du.optimizers import optimize_soni_du

@pytest.fixture
def mock_dspy_lm():
    """Mock DSPy Language Model para tests deterministas."""
    # Opción 1: Usar DummyLM de DSPy
    dummy_lm = dspy.DummyLM(
        responses={
            "What is the user's intent?": "book_flight",
            "Extract slots from message": '{"origin": "Madrid", "destination": "Barcelona"}'
        }
    )
    return dummy_lm

@pytest.fixture
def mock_dspy_module():
    """Mock DSPy Module (SoniDU) para tests."""
    module = MagicMock()
    module.predict.return_value = MagicMock(
        intent="book_flight",
        slots=[{"name": "origin", "value": "Madrid"}],
        confidence=0.95
    )
    return module

@pytest.mark.asyncio
async def test_optimize_soni_du_with_mock_lm(mock_dspy_lm, mock_dspy_module):
    """Test que optimize_soni_du usa mock LM correctamente."""
    # Arrange
    trainset = [
        {"input": "I want to fly to Madrid", "expected_intent": "book_flight"}
    ]

    # Mock dspy.configure para usar DummyLM
    with patch('dspy.configure') as mock_configure:
        mock_configure.return_value = None

        # Act
        result = optimize_soni_du(
            module=mock_dspy_module,
            trainset=trainset,
            lm=mock_dspy_lm,
            max_iterations=3
        )

        # Assert
        assert result is not None
        assert mock_configure.called
        # Verificar que no se usó LLM real
        assert isinstance(result.lm, (dspy.DummyLM, MagicMock))

@pytest.mark.asyncio
async def test_optimize_soni_du_max_iterations():
    """Test que optimización respeta max iterations."""
    # Arrange
    mock_lm = dspy.DummyLM(responses={"*": "book_flight"})
    mock_module = MagicMock()
    trainset = [{"input": "test", "expected": "test"}]

    # Act
    with patch('soni.du.optimizers.BootstrapFewShot') as mock_optimizer:
        mock_optimizer.return_value.compile.return_value = mock_module

        result = optimize_soni_du(
            module=mock_module,
            trainset=trainset,
            lm=mock_lm,
            max_iterations=5
        )

        # Assert
        # Verificar que se llamó con max_bootstrapped_demos=5
        assert mock_optimizer.called
        call_kwargs = mock_optimizer.call_args[1]
        assert call_kwargs.get('max_bootstrapped_demos') == 5
```

**Nota sobre DummyLM**: `dspy.DummyLM` retorna respuestas predefinidas sin llamar a LLMs reales:
```python
# Ejemplo de uso de DummyLM
dummy = dspy.DummyLM(responses={
    "prompt1": "response1",
    "prompt2": "response2",
    "*": "default_response"  # Wildcard para cualquier prompt
})
```
