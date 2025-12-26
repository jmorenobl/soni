## Task: TD-009 - Modularize du/metrics.py

**ID de tarea:** TD-009
**Fase:** Phase 3 - Consolidation
**Prioridad:** 🟡 MEDIUM
**Dependencias:** Ninguna
**Duración estimada:** 1 hora

### Objetivo

Dividir el archivo monolítico `du/metrics.py` (375 líneas) en módulos más pequeños y enfocados para mejorar la organización y mantenibilidad.

### Contexto

El archivo `du/metrics.py` contiene múltiples responsabilidades:
- `MetricScore` dataclass
- `FieldRegistry` class (registry pattern)
- Múltiples funciones de scoring
- GEPA adapter
- Slot extraction metric

**Archivo afectado:** [du/metrics.py](file:///Users/jorge/Projects/Playground/soni/src/soni/du/metrics.py)

### Entregables

- [ ] Crear paquete `du/metrics/` con módulos separados
- [ ] `core.py` - MetricScore, normalize_value, compare_values
- [ ] `registry.py` - FieldRegistry con comandos registrados
- [ ] `scoring.py` - score_command_pair, score_command_lists
- [ ] `factory.py` - create_granular_metric, create_strict_metric
- [ ] `adapters.py` - adapt_metric_for_gepa, create_slot_extraction_metric
- [ ] Mantener backward compatibility en `__init__.py`

### Implementación Detallada

#### Paso 1: Crear estructura de directorio

```
src/soni/du/metrics/
├── __init__.py          # Public exports (backward compatibility)
├── core.py              # MetricScore, normalize_value, compare_values
├── registry.py          # FieldRegistry with registered commands
├── scoring.py           # score_command_pair, score_command_lists
├── factory.py           # create_granular_metric, create_strict_metric
└── adapters.py          # adapt_metric_for_gepa, create_slot_extraction_metric
```

#### Paso 2: Crear core.py

**Archivo a crear:** `src/soni/du/metrics/core.py`

```python
"""Core metric types and utilities."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricScore:
    """Represents a metric score with breakdown."""

    total: float
    max_possible: float
    breakdown: dict[str, float] = field(default_factory=dict)

    @property
    def normalized(self) -> float:
        """Return normalized score between 0 and 1."""
        if self.max_possible == 0:
            return 0.0
        return self.total / self.max_possible


def normalize_value(value: Any) -> Any:
    """Normalize a value for comparison.

    Handles string normalization, None values, etc.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip().lower()
    return value


def compare_values(expected: Any, actual: Any) -> bool:
    """Compare two values for equality after normalization."""
    return normalize_value(expected) == normalize_value(actual)
```

#### Paso 3: Crear registry.py

**Archivo a crear:** `src/soni/du/metrics/registry.py`

```python
"""Field registry for metric computation."""

from typing import Any, Callable


class FieldRegistry:
    """Registry for field comparison functions.

    Allows registering custom comparison logic for different
    command types and their fields.
    """

    def __init__(self) -> None:
        self._comparators: dict[str, Callable[[Any, Any], float]] = {}

    def register(
        self,
        command_type: str,
        field_name: str,
        comparator: Callable[[Any, Any], float],
    ) -> None:
        """Register a comparator for a command field.

        Args:
            command_type: Type of command (e.g., "StartFlow")
            field_name: Name of the field to compare
            comparator: Function that returns score between 0 and 1
        """
        key = f"{command_type}.{field_name}"
        self._comparators[key] = comparator

    def get_comparator(
        self,
        command_type: str,
        field_name: str,
    ) -> Callable[[Any, Any], float] | None:
        """Get comparator for a command field."""
        key = f"{command_type}.{field_name}"
        return self._comparators.get(key)


# Default registry with standard comparators
default_registry = FieldRegistry()

# Register standard comparators
# ... (move from original metrics.py)
```

#### Paso 4: Crear scoring.py

**Archivo a crear:** `src/soni/du/metrics/scoring.py`

```python
"""Scoring functions for command comparison."""

from typing import Sequence

from soni.core.commands import Command
from soni.du.metrics.core import MetricScore, compare_values
from soni.du.metrics.registry import FieldRegistry, default_registry


def score_command_pair(
    expected: Command,
    actual: Command,
    registry: FieldRegistry | None = None,
) -> MetricScore:
    """Score how well actual command matches expected.

    Args:
        expected: Expected command
        actual: Actual command to compare
        registry: Optional field registry (uses default if None)

    Returns:
        MetricScore with breakdown by field
    """
    if registry is None:
        registry = default_registry

    # ... implementation moved from metrics.py


def score_command_lists(
    expected: Sequence[Command],
    actual: Sequence[Command],
    registry: FieldRegistry | None = None,
) -> MetricScore:
    """Score how well actual command list matches expected.

    Uses optimal matching algorithm to pair commands.
    """
    # ... implementation moved from metrics.py
```

#### Paso 5: Crear factory.py y adapters.py

Similar estructura - mover funciones correspondientes del archivo original.

#### Paso 6: Crear __init__.py para backward compatibility

**Archivo a crear:** `src/soni/du/metrics/__init__.py`

```python
"""Metrics module for NLU evaluation.

This module provides tools for computing metrics on NLU outputs,
particularly for DSPy optimization.
"""

from soni.du.metrics.core import (
    MetricScore,
    normalize_value,
    compare_values,
)
from soni.du.metrics.registry import (
    FieldRegistry,
    default_registry,
)
from soni.du.metrics.scoring import (
    score_command_pair,
    score_command_lists,
)
from soni.du.metrics.factory import (
    create_granular_metric,
    create_strict_metric,
)
from soni.du.metrics.adapters import (
    adapt_metric_for_gepa,
    create_slot_extraction_metric,
)

__all__ = [
    # Core
    "MetricScore",
    "normalize_value",
    "compare_values",
    # Registry
    "FieldRegistry",
    "default_registry",
    # Scoring
    "score_command_pair",
    "score_command_lists",
    # Factory
    "create_granular_metric",
    "create_strict_metric",
    # Adapters
    "adapt_metric_for_gepa",
    "create_slot_extraction_metric",
]
```

### Exception: Test-After

**Reason for test-after:**
- [x] Legacy code retrofit

**Justification:**
Este es un refactoring de organización. Los tests existentes validan que la funcionalidad se mantiene. Solo cambia la estructura de archivos.

### Criterios de Éxito

- [ ] `du/metrics.py` eliminado y reemplazado por paquete `du/metrics/`
- [ ] Cada módulo tiene < 100 LOC
- [ ] Imports existentes siguen funcionando
- [ ] Todos los tests existentes pasan
- [ ] `uv run mypy src/soni/du/metrics/` pasa

### Validación Manual

**Comandos para validar:**

```bash
# Verificar estructura
ls -la src/soni/du/metrics/

# Verificar tamaño de archivos
wc -l src/soni/du/metrics/*.py

# Verificar que imports funcionan
python -c "from soni.du.metrics import MetricScore, score_command_pair"

# Tests
uv run pytest tests/unit/du/ -v

# Type check
uv run mypy src/soni/du/
```

### Referencias

- [Technical Debt Analysis](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/technical-debt-analysis.md#L179-203)
- [Python Package Structure](https://docs.python.org/3/tutorial/modules.html#packages)

### Notas Adicionales

- El archivo original `du/metrics.py` debe eliminarse después de crear el paquete
- Mantener el mismo API público para no romper código existente
- Considerar añadir `py.typed` marker en el nuevo paquete
