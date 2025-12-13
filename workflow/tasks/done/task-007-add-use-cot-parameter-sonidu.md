## Task: 007 - Add use_cot Parameter to SoniDU for Performance Optimization

**ID de tarea:** 007
**Hito:** 10
**Dependencias:** Puede hacerse en paralelo con 006, pero es complementaria
**Duración estimada:** 2-3 horas

### Objetivo

Añadir un parámetro `use_cot` (use ChainOfThought) al constructor de `SoniDU` para permitir elegir entre `dspy.Predict` (más rápido, menos tokens) y `dspy.ChainOfThought` (más preciso, más tokens). Por defecto será `False` para usar `dspy.Predict` y reducir latencia, especialmente útil para la predicción en dos pasos.

**Configuración desde YAML:** El parámetro también se puede configurar desde el YAML del diálogo en `settings.models.nlu.use_reasoning` (nombre más explícito en YAML), permitiendo configurarlo manualmente sin modificar código. Internamente se mapea a `use_cot` para mantener consistencia con la terminología de DSPy.

### Contexto

**Problema:**
- `SoniDU` actualmente siempre usa `dspy.ChainOfThought`, que es más lento y consume más tokens
- Para la predicción en dos pasos (task-006), esto significa dos llamadas costosas
- `dspy.Predict` es más rápido y consume menos tokens, suficiente para muchos casos

**Solución propuesta:**
- Añadir parámetro `use_cot: bool = False` al `__init__` de `SoniDU`
- Si `False`: usar `dspy.Predict` (más rápido, menos tokens)
- Si `True`: usar `dspy.ChainOfThought` (más preciso, más tokens, comportamiento actual)
- Añadir campo `use_reasoning` a `NLUModelConfig` en `config.py` para configuración desde YAML (nombre más explícito)
- Mapear `use_reasoning` del YAML a `use_cot` al pasar a `SoniDU()` en `runtime.py`

**Beneficios:**
- Reduce latencia en predicciones simples
- Reduce costos de tokens
- Especialmente útil para el paso 1 de two-stage prediction (intent detection)
- Mantiene opción de usar ChainOfThought cuando se necesite más precisión

**Referencias:**
- Código actual: `src/soni/du/modules.py` (línea 39)
- Task relacionada: `task-006-two-stage-nlu-prediction.md`
- DSPy docs: `dspy.Predict` vs `dspy.ChainOfThought`

### Entregables

- [ ] Parámetro `use_cot: bool = False` añadido a `SoniDU.__init__`
- [ ] Lógica condicional para usar `dspy.Predict` o `dspy.ChainOfThought`
- [ ] Por defecto usa `dspy.Predict` (más rápido)
- [ ] Campo `use_reasoning` añadido a `NLUModelConfig` en `config.py` (nombre explícito en YAML)
- [ ] `RuntimeLoop` mapea `use_reasoning` del YAML a `use_cot` al pasar a `SoniDU()`
- [ ] Ejemplo YAML actualizado para mostrar configuración
- [ ] Tests actualizados para validar ambos modos
- [ ] Documentación en docstring sobre cuándo usar cada modo

### Implementación Detallada

#### Paso 1: Añadir parámetro use_cot al constructor

**Archivo(s) a modificar:** `src/soni/du/modules.py`

**Código específico:**

```python
def __init__(self, cache_size: int = 1000, cache_ttl: int = 300, use_cot: bool = False) -> None:
    """Initialize SoniDU module.

    Args:
        cache_size: Maximum number of cached NLU results
        cache_ttl: Time-to-live for cache entries in seconds
        use_cot: If True, use ChainOfThought (slower, more precise).
                 If False, use Predict (faster, less tokens). Default: False
    """
    super().__init__()  # CRITICAL: Must call super().__init__()

    # Create predictor based on use_cot parameter
    if use_cot:
        # ChainOfThought: More precise, shows reasoning, but slower and uses more tokens
        self.predictor = dspy.ChainOfThought(DialogueUnderstanding)
        logger.debug("SoniDU initialized with ChainOfThought (use_cot=True)")
    else:
        # Predict: Faster, fewer tokens, sufficient for most cases
        self.predictor = dspy.Predict(DialogueUnderstanding)
        logger.debug("SoniDU initialized with Predict (use_cot=False, default)")

    # Optional caching layer
    self.nlu_cache: TTLCache[str, NLUOutput] = TTLCache(
        maxsize=cache_size,
        ttl=cache_ttl,
    )

    self.use_cot = use_cot  # Store for reference
```

**Explicación:**
- Parámetro `use_cot` con valor por defecto `False`
- Si `True`: usa `dspy.ChainOfThought` (comportamiento actual)
- Si `False`: usa `dspy.Predict` (más rápido, nuevo comportamiento por defecto)
- Almacena `use_cot` como atributo para referencia
- Logging para debugging

#### Paso 2: Actualizar docstrings y documentación

**Archivo(s) a modificar:** `src/soni/du/modules.py`

**Código específico:**

```python
class SoniDU(dspy.Module):
    """
    Soni Dialogue Understanding module with structured types.

    This module provides:
    - Type-safe async interface for runtime
    - Sync interface for DSPy optimizers
    - Automatic prompt optimization via DSPy
    - Structured Pydantic models throughout
    - Configurable predictor: Predict (fast) or ChainOfThought (precise)

    Performance Notes:
    - Predict (use_cot=False): Faster, fewer tokens, sufficient for most cases
    - ChainOfThought (use_cot=True): Slower, more tokens, shows reasoning,
      useful when precision is critical or debugging NLU behavior
    """
```

**Explicación:**
- Documentar la diferencia entre ambos modos
- Explicar cuándo usar cada uno
- Notas de rendimiento

#### Paso 3: Añadir use_reasoning a NLUModelConfig

**Archivo(s) a modificar:** `src/soni/core/config.py`

**Código específico:**

```python
class NLUModelConfig(ModelConfig):
    """Configuration for NLU model."""

    use_reasoning: bool = Field(
        default=False,
        description=(
            "If True, use ChainOfThought with explicit reasoning (slower, more precise). "
            "If False, use Predict without reasoning (faster, fewer tokens). Default: False"
        ),
    )
```

**Explicación:**
- Añade campo `use_reasoning` a `NLUModelConfig` con valor por defecto `False`
- Nombre más explícito y user-friendly en YAML (vs `use_cot` técnico)
- Documenta el propósito y comportamiento de cada modo
- Permite configuración desde YAML

#### Paso 4: Mapear use_reasoning desde configuración a SoniDU

**Archivo(s) a modificar:** `src/soni/runtime/runtime.py`

**Código específico:**

```python
# Línea ~109, cambiar:
else:
    self.du = SoniDU()
    logger.info("Using default (non-optimized) DU module")

# Por:
else:
    # Get use_reasoning from YAML configuration (defaults to False if not set)
    # Map to use_cot for SoniDU (maintains DSPy terminology in code)
    use_reasoning = getattr(self.config.settings.models.nlu, "use_reasoning", False)
    self.du = SoniDU(use_cot=use_reasoning)
    logger.info(
        f"Using default (non-optimized) DU module with use_reasoning={use_reasoning}"
    )
```

**Explicación:**
- Obtiene `use_reasoning` desde `self.config.settings.models.nlu.use_reasoning` (nombre explícito en YAML)
- Mapea a `use_cot` al pasar a `SoniDU()` (mantiene terminología DSPy en código)
- Usa `getattr` con valor por defecto `False` para compatibilidad hacia atrás
- Logging para debugging

#### Paso 5: Actualizar ejemplo YAML

**Archivo(s) a modificar:** `examples/flight_booking/soni.yaml`

**Código específico:**

```yaml
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
      temperature: 0.1
      use_reasoning: false  # Use Predict (fast) instead of ChainOfThought (precise)
      # Set to true for more precise NLU with explicit reasoning traces (slower, more tokens)
```

**Explicación:**
- Añade comentario explicativo sobre `use_reasoning` (nombre más explícito)
- Muestra valor por defecto (`false`)
- Documenta cuándo usar cada modo
- Nombre `use_reasoning` es más claro para usuarios que `use_cot`

#### Paso 6: Actualizar tests existentes

**Archivo(s) a modificar:** Tests que crean instancias de `SoniDU`

**Búsqueda necesaria:**
- Buscar todos los lugares donde se instancia `SoniDU`
- Verificar si los tests asumen comportamiento de ChainOfThought
- Actualizar si es necesario

**Código específico:**

```python
# En tests, si necesitan ChainOfThought explícitamente:
nlu = SoniDU(use_cot=True)  # Para tests que requieren reasoning

# En tests normales:
nlu = SoniDU()  # Usa Predict por defecto (más rápido)
```

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_du_modules.py` o similar

**Tests específicos a implementar:**

```python
def test_sonidu_default_uses_predict():
    """Test that SoniDU defaults to Predict (not ChainOfThought)."""
    nlu = SoniDU()
    # Verify predictor is dspy.Predict, not ChainOfThought
    assert isinstance(nlu.predictor, dspy.Predict)
    assert not isinstance(nlu.predictor, dspy.ChainOfThought)
    assert nlu.use_cot is False

def test_sonidu_with_use_cot_true_uses_chain_of_thought():
    """Test that SoniDU uses ChainOfThought when use_cot=True."""
    nlu = SoniDU(use_cot=True)
    # Verify predictor is ChainOfThought
    assert isinstance(nlu.predictor, dspy.ChainOfThought)
    assert nlu.use_cot is True

def test_sonidu_predict_vs_cot_performance():
    """Test that Predict is faster than ChainOfThought (optional performance test)."""
    # This could be a benchmark test
    # Measure time difference between Predict and ChainOfThought
    pass

def test_sonidu_uses_config_from_yaml():
    """Test that SoniDU uses use_reasoning from YAML configuration."""
    # Create temporary YAML with use_reasoning: true
    import tempfile
    import yaml
    from soni.runtime import RuntimeLoop

    config = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                    "use_reasoning": True,  # Configure from YAML (maps to use_cot internally)
                }
            },
            "persistence": {"backend": "memory"},
        },
        "flows": {},
        "slots": {},
        "actions": {},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        temp_path = f.name

    try:
        runtime = RuntimeLoop(temp_path)
        # Verify that DU uses ChainOfThought (use_reasoning=True maps to use_cot=True)
        assert runtime.du.use_cot is True
        assert isinstance(runtime.du.predictor, dspy.ChainOfThought)
    finally:
        Path(temp_path).unlink()
```

### Criterios de Éxito

- [ ] `test_sonidu_default_uses_predict` pasa
- [ ] `test_sonidu_with_use_cot_true_uses_chain_of_thought` pasa
- [ ] `test_sonidu_uses_config_from_yaml` pasa (nuevo test)
- [ ] Tests existentes siguen pasando (compatibilidad hacia atrás)
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores
- [ ] Documentación actualizada en docstrings
- [ ] Por defecto usa `dspy.Predict` (más rápido)
- [ ] Configuración desde YAML funciona correctamente

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar tests de SoniDU
uv run pytest tests/unit/test_du_modules.py -v

# Ejecutar todos los tests para verificar no hay regresiones
uv run pytest tests/ -v

# Verificar que el comportamiento por defecto es Predict
uv run python -c "from soni.du.modules import SoniDU; nlu = SoniDU(); print(type(nlu.predictor).__name__)"
# Debería imprimir: Predict
```

**Resultado esperado:**
- Tests pasan correctamente
- Por defecto usa `dspy.Predict`
- Con `use_cot=True` usa `dspy.ChainOfThought`
- No hay regresiones en tests existentes

### Referencias

- Código actual: `src/soni/du/modules.py` (línea 39)
- Configuración: `src/soni/core/config.py` (línea 285, `NLUModelConfig`)
- Runtime: `src/soni/runtime/runtime.py` (línea 109, inicialización de `SoniDU`)
- Ejemplo YAML: `examples/flight_booking/soni.yaml`
- DSPy documentation: `dspy.Predict` vs `dspy.ChainOfThought`
- Task relacionada: `task-006-two-stage-nlu-prediction.md`
- Diseño NLU: `docs/design/06-nlu-system.md`

### Notas Adicionales

**Cuándo usar cada modo:**

| Modo | Cuándo usar | Pros | Contras |
|------|-------------|------|---------|
| **Predict** (default) | Producción, casos normales, two-stage paso 1 | Rápido, menos tokens, suficiente precisión | No muestra reasoning explícito |
| **ChainOfThought** | Debugging, casos complejos, optimización | Muestra reasoning, más preciso | Más lento, más tokens |

**Compatibilidad:**
- Cambio de comportamiento por defecto (de ChainOfThought a Predict)
- Puede afectar tests que asumen reasoning explícito
- Revisar tests y actualizar si es necesario
- Para mantener comportamiento anterior: `SoniDU(use_cot=True)`

**Integración con task-006:**
- El paso 1 de two-stage prediction puede usar `Predict` (más rápido)
- El paso 2 puede usar `ChainOfThought` si se necesita más precisión
- O ambos pueden usar `Predict` para máxima velocidad

**Consideraciones:**
- `Predict` puede ser suficiente para la mayoría de casos
- `ChainOfThought` es útil para debugging y casos complejos
- El usuario puede elegir según sus necesidades
- Por defecto optimizado para rendimiento (Predict)
- **Configuración desde YAML:** Permite cambiar el comportamiento sin modificar código
- **Nomenclatura:** YAML usa `use_reasoning` (explícito), código Python usa `use_cot` (término DSPy)
- **Compatibilidad hacia atrás:** Si `use_reasoning` no está en YAML, usa `False` por defecto
