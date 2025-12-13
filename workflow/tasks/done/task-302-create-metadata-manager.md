## Task: 302 - Create MetadataManager Utility to Eliminate Duplication

**ID de tarea:** 302
**Hito:** Technical Debt Repayment - HIGH
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas
**Prioridad:** 🔴 HIGH - Reduces maintenance burden
**Related DEBT:** DEBT-003

### Objetivo

Eliminar la duplicación de lógica de manipulación de metadata creando una clase `MetadataManager` centralizada que encapsule todas las operaciones de clearing/setting de flags de metadata en un solo lugar, reduciendo mantenimiento y riesgo de inconsistencias.

### Contexto

**Problema Actual:**
La lógica para limpiar/actualizar metadata flags está duplicada en 9+ ubicaciones:

**Duplicaciones encontradas:**
- `handle_confirmation.py` (lines 55-58, 95-98, 121-124, 137-140, 164-167, 256-268)
- `handle_correction.py` (lines 90-95)
- `handle_modification.py` (lines 87-92)
- `understand.py` (lines 208-212)

**Patrón repetido:**
```python
metadata = state.get("metadata", {}).copy()
metadata.pop("_correction_slot", None)
metadata.pop("_correction_value", None)
metadata.pop("_modification_slot", None)
metadata.pop("_modification_value", None)
```

**Problemas:**
- ❌ Violación DRY: Mismo código copiado 9+ veces
- ❌ Error-prone: Fácil olvidar actualizar todas las ubicaciones
- ❌ Mantenimiento: Agregar nuevo flag requiere cambiar 9+ archivos
- ❌ Testing: Tests duplicados para cada ubicación

**Referencias:**
- Technical Debt: `docs/technical-debt.md` (DEBT-003)
- DRY Principle: "The Pragmatic Programmer" by Hunt & Thomas
- Architecture: `.cursor/rules/001-architecture.mdc` (SRP, DRY)

### Entregables

- [ ] Clase `MetadataManager` creada en `src/soni/utils/metadata_manager.py`
- [ ] Métodos para clear confirmation, correction, modification flags
- [ ] Método genérico `clear_all_flow_flags()`
- [ ] Todos los nodos actualizados para usar `MetadataManager`
- [ ] Tests unitarios para `MetadataManager`
- [ ] Código duplicado eliminado de todos los nodos
- [ ] Todos los tests existentes siguen pasando

### Implementación Detallada

#### Paso 1: Crear MetadataManager class

**Archivo a crear:** `src/soni/utils/metadata_manager.py`

**Código completo:**

```python
"""Metadata management utilities for dialogue state.

This module provides centralized metadata manipulation following DRY principle.
All metadata flag clearing/setting should go through MetadataManager to avoid
code duplication and ensure consistency.
"""

from typing import Any


class MetadataManager:
    """Centralized metadata manipulation following DRY principle.

    This class encapsulates all metadata flag operations to avoid duplicating
    the same clearing/setting logic across multiple nodes.

    All methods follow immutable pattern: they return NEW metadata dict,
    never modify in place.
    """

    @staticmethod
    def clear_confirmation_flags(metadata: dict[str, Any]) -> dict[str, Any]:
        """Clear confirmation-related flags from metadata.

        Removes all flags related to confirmation flow:
        - _confirmation_attempts: retry counter
        - _confirmation_processed: processing status flag
        - _confirmation_unclear: unclear response flag

        Args:
            metadata: Current metadata dictionary

        Returns:
            New metadata dict with confirmation flags removed
        """
        updated = metadata.copy()
        updated.pop("_confirmation_attempts", None)
        updated.pop("_confirmation_processed", None)
        updated.pop("_confirmation_unclear", None)
        return updated

    @staticmethod
    def clear_correction_flags(metadata: dict[str, Any]) -> dict[str, Any]:
        """Clear correction-related flags from metadata.

        Removes all flags related to slot correction:
        - _correction_slot: name of corrected slot
        - _correction_value: new value after correction

        Args:
            metadata: Current metadata dictionary

        Returns:
            New metadata dict with correction flags removed
        """
        updated = metadata.copy()
        updated.pop("_correction_slot", None)
        updated.pop("_correction_value", None)
        return updated

    @staticmethod
    def clear_modification_flags(metadata: dict[str, Any]) -> dict[str, Any]:
        """Clear modification-related flags from metadata.

        Removes all flags related to slot modification:
        - _modification_slot: name of modified slot
        - _modification_value: new value after modification

        Args:
            metadata: Current metadata dictionary

        Returns:
            New metadata dict with modification flags removed
        """
        updated = metadata.copy()
        updated.pop("_modification_slot", None)
        updated.pop("_modification_value", None)
        return updated

    @staticmethod
    def clear_all_flow_flags(metadata: dict[str, Any]) -> dict[str, Any]:
        """Clear all flow-related flags (confirmation, correction, modification).

        Use this when resetting state between flows or on errors.

        Args:
            metadata: Current metadata dictionary

        Returns:
            New metadata dict with all flow flags removed
        """
        updated = metadata.copy()
        # Confirmation flags
        updated.pop("_confirmation_attempts", None)
        updated.pop("_confirmation_processed", None)
        updated.pop("_confirmation_unclear", None)
        # Correction flags
        updated.pop("_correction_slot", None)
        updated.pop("_correction_value", None)
        # Modification flags
        updated.pop("_modification_slot", None)
        updated.pop("_modification_value", None)
        return updated

    @staticmethod
    def set_correction_flags(
        metadata: dict[str, Any],
        slot_name: str,
        value: Any,
    ) -> dict[str, Any]:
        """Set correction flags and clear modification flags.

        When a correction occurs, we:
        1. Set correction_slot and correction_value
        2. Clear any existing modification flags (mutually exclusive)

        Args:
            metadata: Current metadata dictionary
            slot_name: Name of the corrected slot
            value: New value after correction

        Returns:
            New metadata dict with correction flags set
        """
        updated = metadata.copy()
        updated["_correction_slot"] = slot_name
        updated["_correction_value"] = value
        # Clear modification flags (mutually exclusive)
        updated.pop("_modification_slot", None)
        updated.pop("_modification_value", None)
        return updated

    @staticmethod
    def set_modification_flags(
        metadata: dict[str, Any],
        slot_name: str,
        value: Any,
    ) -> dict[str, Any]:
        """Set modification flags and clear correction flags.

        When a modification occurs, we:
        1. Set modification_slot and modification_value
        2. Clear any existing correction flags (mutually exclusive)

        Args:
            metadata: Current metadata dictionary
            slot_name: Name of the modified slot
            value: New value after modification

        Returns:
            New metadata dict with modification flags set
        """
        updated = metadata.copy()
        updated["_modification_slot"] = slot_name
        updated["_modification_value"] = value
        # Clear correction flags (mutually exclusive)
        updated.pop("_correction_slot", None)
        updated.pop("_correction_value", None)
        return updated

    @staticmethod
    def increment_confirmation_attempts(metadata: dict[str, Any]) -> dict[str, Any]:
        """Increment confirmation retry counter.

        Args:
            metadata: Current metadata dictionary

        Returns:
            New metadata dict with incremented confirmation attempts
        """
        updated = metadata.copy()
        current_attempts = metadata.get("_confirmation_attempts", 0)
        updated["_confirmation_attempts"] = current_attempts + 1
        return updated

    @staticmethod
    def get_confirmation_attempts(metadata: dict[str, Any]) -> int:
        """Get current confirmation retry count.

        Args:
            metadata: Current metadata dictionary

        Returns:
            Number of confirmation attempts (0 if not set)
        """
        return metadata.get("_confirmation_attempts", 0)
```

**Explicación:**
- Clase con métodos estáticos (no necesita instancia)
- Sigue patrón inmutable: retorna NUEVO dict, nunca modifica in-place
- Métodos específicos para cada tipo de flag (confirmation, correction, modification)
- Método genérico `clear_all_flow_flags()` para reset completo
- Métodos setter que automáticamente limpian flags mutuamente excluyentes
- Método getter para obtener valores de manera consistente

#### Paso 2: Actualizar handle_confirmation.py para usar MetadataManager

**Archivo a modificar:** `src/soni/dm/nodes/handle_confirmation.py`

**Imports a agregar (top of file):**

```python
from soni.utils.metadata_manager import MetadataManager
```

**Reemplazos a realizar:**

**Ubicación 1: Lines 55-58 (clear on max attempts exceeded)**

```python
# BEFORE:
metadata_cleared = metadata.copy()
metadata_cleared.pop("_confirmation_attempts", None)
metadata_cleared.pop("_confirmation_processed", None)
metadata_cleared.pop("_confirmation_unclear", None)

# AFTER:
metadata_cleared = MetadataManager.clear_confirmation_flags(metadata)
```

**Ubicación 2: Lines 95-98 (clear on success)**

```python
# BEFORE:
metadata_cleared = metadata.copy()
metadata_cleared.pop("_confirmation_attempts", None)
metadata_cleared.pop("_confirmation_processed", None)
metadata_cleared.pop("_confirmation_unclear", None)

# AFTER:
metadata_cleared = MetadataManager.clear_confirmation_flags(metadata)
```

**Ubicación 3: Lines 121-124 (clear on denial after max attempts)**

```python
# BEFORE:
metadata_cleared = metadata.copy()
metadata_cleared.pop("_confirmation_attempts", None)
metadata_cleared.pop("_confirmation_processed", None)
metadata_cleared.pop("_confirmation_unclear", None)

# AFTER:
metadata_cleared = MetadataManager.clear_confirmation_flags(metadata)
```

**Ubicación 4: Lines 137-140 (clear on explicit denial)**

```python
# BEFORE:
metadata_cleared = metadata.copy()
metadata_cleared.pop("_confirmation_attempts", None)
metadata_cleared.pop("_confirmation_processed", None)
metadata_cleared.pop("_confirmation_unclear", None)

# AFTER:
metadata_cleared = MetadataManager.clear_confirmation_flags(metadata)
```

**Ubicación 5: Lines 164-167 (clear after max retries in unclear path)**

```python
# BEFORE:
metadata_cleared = metadata_updated.copy()
metadata_cleared.pop("_confirmation_attempts", None)
metadata_cleared.pop("_confirmation_processed", None)
metadata_cleared.pop("_confirmation_unclear", None)

# AFTER:
metadata_cleared = MetadataManager.clear_confirmation_flags(metadata_updated)
```

**Ubicación 6: Lines 256-268 (set correction/modification flags)**

```python
# BEFORE:
metadata = state.get("metadata", {}).copy()
if message_type == "correction":
    metadata["_correction_slot"] = slot_name
    metadata["_correction_value"] = normalized_value
    # Clear modification variables if any
    metadata.pop("_modification_slot", None)
    metadata.pop("_modification_value", None)
elif message_type == "modification":
    metadata["_modification_slot"] = slot_name
    metadata["_modification_value"] = normalized_value
    # Clear correction variables if any
    metadata.pop("_correction_slot", None)
    metadata.pop("_correction_value", None)

# AFTER:
metadata = state.get("metadata", {})
if message_type == "correction":
    metadata = MetadataManager.set_correction_flags(metadata, slot_name, normalized_value)
elif message_type == "modification":
    metadata = MetadataManager.set_modification_flags(metadata, slot_name, normalized_value)
```

#### Paso 3: Actualizar handle_correction.py

**Archivo a modificar:** `src/soni/dm/nodes/handle_correction.py`

**Imports a agregar:**

```python
from soni.utils.metadata_manager import MetadataManager
```

**Reemplazo en lines 90-95:**

```python
# BEFORE:
metadata = state.get("metadata", {}).copy()
metadata["_correction_slot"] = slot_name
metadata["_correction_value"] = normalized_value
# Clear modification variables if any
metadata.pop("_modification_slot", None)
metadata.pop("_modification_value", None)

# AFTER:
metadata = state.get("metadata", {})
metadata = MetadataManager.set_correction_flags(metadata, slot_name, normalized_value)
```

#### Paso 4: Actualizar handle_modification.py

**Archivo a modificar:** `src/soni/dm/nodes/handle_modification.py`

**Imports a agregar:**

```python
from soni.utils.metadata_manager import MetadataManager
```

**Reemplazo en lines 87-92:**

```python
# BEFORE:
metadata = state.get("metadata", {}).copy()
metadata["_modification_slot"] = slot_name
metadata["_modification_value"] = normalized_value
# Clear correction variables if any
metadata.pop("_correction_slot", None)
metadata.pop("_correction_value", None)

# AFTER:
metadata = state.get("metadata", {})
metadata = MetadataManager.set_modification_flags(metadata, slot_name, normalized_value)
```

#### Paso 5: Actualizar understand.py

**Archivo a modificar:** `src/soni/dm/nodes/understand.py`

**Imports a agregar:**

```python
from soni.utils.metadata_manager import MetadataManager
```

**Reemplazo en lines 208-212:**

```python
# BEFORE:
metadata = state.get("metadata", {}).copy()
metadata.pop("_correction_slot", None)
metadata.pop("_correction_value", None)
metadata.pop("_modification_slot", None)
metadata.pop("_modification_value", None)

# AFTER:
metadata = state.get("metadata", {})
# Clear correction and modification flags at start of new turn
metadata = MetadataManager.clear_correction_flags(metadata)
metadata = MetadataManager.clear_modification_flags(metadata)
```

**O más conciso:**

```python
# AFTER (alternative):
metadata = state.get("metadata", {})
# Clear correction and modification flags at start of new turn
# (confirmation flags are NOT cleared here - they persist across understand)
metadata_temp = MetadataManager.clear_correction_flags(metadata)
metadata = MetadataManager.clear_modification_flags(metadata_temp)
```

#### Paso 6: Agregar MetadataManager a __init__.py

**Archivo a modificar:** `src/soni/utils/__init__.py`

**Agregar export:**

```python
from soni.utils.metadata_manager import MetadataManager

__all__ = [
    # ... existing exports ...
    "MetadataManager",
]
```

### Tests Requeridos

**Archivo de tests:** `tests/unit/utils/test_metadata_manager.py`

**Tests completos:**

```python
"""Tests for MetadataManager utility."""

import pytest
from soni.utils.metadata_manager import MetadataManager


class TestClearConfirmationFlags:
    """Tests for clearing confirmation flags."""

    def test_clears_all_confirmation_flags(self):
        """Test that all confirmation flags are removed."""
        # Arrange
        metadata = {
            "_confirmation_attempts": 2,
            "_confirmation_processed": True,
            "_confirmation_unclear": True,
            "other_key": "should_remain",
        }

        # Act
        result = MetadataManager.clear_confirmation_flags(metadata)

        # Assert
        assert "_confirmation_attempts" not in result
        assert "_confirmation_processed" not in result
        assert "_confirmation_unclear" not in result
        assert result["other_key"] == "should_remain"

    def test_handles_missing_flags_gracefully(self):
        """Test clearing when flags don't exist."""
        # Arrange
        metadata = {"other_key": "value"}

        # Act
        result = MetadataManager.clear_confirmation_flags(metadata)

        # Assert - should not raise error
        assert result == {"other_key": "value"}

    def test_returns_new_dict_immutable(self):
        """Test that original metadata is not modified (immutable)."""
        # Arrange
        metadata = {"_confirmation_attempts": 2}

        # Act
        result = MetadataManager.clear_confirmation_flags(metadata)

        # Assert
        assert metadata["_confirmation_attempts"] == 2  # Original unchanged
        assert "_confirmation_attempts" not in result  # New dict cleared


class TestClearCorrectionFlags:
    """Tests for clearing correction flags."""

    def test_clears_correction_flags(self):
        """Test that correction flags are removed."""
        # Arrange
        metadata = {
            "_correction_slot": "origin",
            "_correction_value": "NYC",
            "other_key": "remains",
        }

        # Act
        result = MetadataManager.clear_correction_flags(metadata)

        # Assert
        assert "_correction_slot" not in result
        assert "_correction_value" not in result
        assert result["other_key"] == "remains"


class TestClearModificationFlags:
    """Tests for clearing modification flags."""

    def test_clears_modification_flags(self):
        """Test that modification flags are removed."""
        # Arrange
        metadata = {
            "_modification_slot": "destination",
            "_modification_value": "LAX",
            "other_key": "remains",
        }

        # Act
        result = MetadataManager.clear_modification_flags(metadata)

        # Assert
        assert "_modification_slot" not in result
        assert "_modification_value" not in result
        assert result["other_key"] == "remains"


class TestClearAllFlowFlags:
    """Tests for clearing all flow flags."""

    def test_clears_all_flow_flags(self):
        """Test that all flow-related flags are removed."""
        # Arrange
        metadata = {
            "_confirmation_attempts": 2,
            "_confirmation_processed": True,
            "_confirmation_unclear": False,
            "_correction_slot": "origin",
            "_correction_value": "NYC",
            "_modification_slot": "destination",
            "_modification_value": "LAX",
            "other_key": "should_remain",
        }

        # Act
        result = MetadataManager.clear_all_flow_flags(metadata)

        # Assert
        # All flow flags removed
        assert "_confirmation_attempts" not in result
        assert "_confirmation_processed" not in result
        assert "_confirmation_unclear" not in result
        assert "_correction_slot" not in result
        assert "_correction_value" not in result
        assert "_modification_slot" not in result
        assert "_modification_value" not in result
        # Other keys remain
        assert result["other_key"] == "should_remain"


class TestSetCorrectionFlags:
    """Tests for setting correction flags."""

    def test_sets_correction_flags(self):
        """Test that correction flags are set correctly."""
        # Arrange
        metadata = {}

        # Act
        result = MetadataManager.set_correction_flags(metadata, "origin", "NYC")

        # Assert
        assert result["_correction_slot"] == "origin"
        assert result["_correction_value"] == "NYC"

    def test_clears_modification_flags_when_setting_correction(self):
        """Test that modification flags are cleared when setting correction."""
        # Arrange
        metadata = {
            "_modification_slot": "destination",
            "_modification_value": "LAX",
        }

        # Act
        result = MetadataManager.set_correction_flags(metadata, "origin", "NYC")

        # Assert
        assert result["_correction_slot"] == "origin"
        assert result["_correction_value"] == "NYC"
        assert "_modification_slot" not in result
        assert "_modification_value" not in result


class TestSetModificationFlags:
    """Tests for setting modification flags."""

    def test_sets_modification_flags(self):
        """Test that modification flags are set correctly."""
        # Arrange
        metadata = {}

        # Act
        result = MetadataManager.set_modification_flags(metadata, "destination", "LAX")

        # Assert
        assert result["_modification_slot"] == "destination"
        assert result["_modification_value"] == "LAX"

    def test_clears_correction_flags_when_setting_modification(self):
        """Test that correction flags are cleared when setting modification."""
        # Arrange
        metadata = {
            "_correction_slot": "origin",
            "_correction_value": "NYC",
        }

        # Act
        result = MetadataManager.set_modification_flags(metadata, "destination", "LAX")

        # Assert
        assert result["_modification_slot"] == "destination"
        assert result["_modification_value"] == "LAX"
        assert "_correction_slot" not in result
        assert "_correction_value" not in result


class TestConfirmationAttempts:
    """Tests for confirmation attempts counter."""

    def test_increment_confirmation_attempts(self):
        """Test incrementing confirmation attempts."""
        # Arrange
        metadata = {"_confirmation_attempts": 1}

        # Act
        result = MetadataManager.increment_confirmation_attempts(metadata)

        # Assert
        assert result["_confirmation_attempts"] == 2

    def test_increment_from_zero(self):
        """Test incrementing when no attempts exist."""
        # Arrange
        metadata = {}

        # Act
        result = MetadataManager.increment_confirmation_attempts(metadata)

        # Assert
        assert result["_confirmation_attempts"] == 1

    def test_get_confirmation_attempts_existing(self):
        """Test getting existing confirmation attempts."""
        # Arrange
        metadata = {"_confirmation_attempts": 3}

        # Act
        result = MetadataManager.get_confirmation_attempts(metadata)

        # Assert
        assert result == 3

    def test_get_confirmation_attempts_default(self):
        """Test getting confirmation attempts returns 0 if not set."""
        # Arrange
        metadata = {}

        # Act
        result = MetadataManager.get_confirmation_attempts(metadata)

        # Assert
        assert result == 0
```

**Actualizar tests de integración:**

**Archivo:** `tests/integration/test_confirmation_flow.py` (y similares)

No necesitan cambios grandes, pero verificar que siguen pasando después de refactor.

### Criterios de Éxito

- [ ] `MetadataManager` class creada en `src/soni/utils/metadata_manager.py`
- [ ] Todos los métodos implementados con docstrings
- [ ] `handle_confirmation.py` usa `MetadataManager` (6 ubicaciones actualizadas)
- [ ] `handle_correction.py` usa `MetadataManager` (1 ubicación)
- [ ] `handle_modification.py` usa `MetadataManager` (1 ubicación)
- [ ] `understand.py` usa `MetadataManager` (1 ubicación)
- [ ] ZERO duplicación de metadata clearing logic
- [ ] Tests unitarios completos para `MetadataManager` (20+ tests)
- [ ] Todos los tests existentes siguen pasando
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores
- [ ] Code coverage para `MetadataManager` >= 95%

### Validación Manual

**Comandos para validar:**

```bash
# 1. Run new tests for MetadataManager
uv run pytest tests/unit/utils/test_metadata_manager.py -v --cov=src/soni/utils/metadata_manager

# 2. Run all node tests to ensure no regressions
uv run pytest tests/unit/dm/nodes/test_handle_confirmation.py -v
uv run pytest tests/unit/dm/nodes/test_handle_correction.py -v
uv run pytest tests/unit/dm/nodes/test_handle_modification.py -v
uv run pytest tests/unit/dm/nodes/test_understand.py -v

# 3. Run integration tests
uv run pytest tests/integration/ -v

# 4. Verify no duplicated metadata clearing logic remains
grep -r "metadata.pop.*correction" src/soni/dm/nodes/ || echo "✅ No duplication found"
grep -r "metadata.pop.*modification" src/soni/dm/nodes/ || echo "✅ No duplication found"

# 5. Lint and type check
uv run ruff check src/
uv run mypy src/soni
```

**Resultado esperado:**
- All tests pass (new and existing)
- ZERO grep results (no duplicated clearing logic)
- Code coverage for MetadataManager >= 95%
- No lint or type errors

### Referencias

- **Technical Debt Document:** `docs/technical-debt.md` (DEBT-003)
- **DRY Principle:** "The Pragmatic Programmer" by Hunt & Thomas
- **Architecture Rules:** `.cursor/rules/001-architecture.mdc` (SRP, DRY)
- **Code Style:** `.cursor/rules/002-code-style.mdc`
- **Affected Files:**
  - `src/soni/dm/nodes/handle_confirmation.py`
  - `src/soni/dm/nodes/handle_correction.py`
  - `src/soni/dm/nodes/handle_modification.py`
  - `src/soni/dm/nodes/understand.py`

### Notas Adicionales

**Design Decisions:**

1. **Static Methods vs Instance:**
   - Usamos static methods porque `MetadataManager` no necesita estado
   - Es esencialmente un namespace para funciones relacionadas
   - Podría ser un módulo con funciones, pero clase da mejor agrupación

2. **Immutability:**
   - TODOS los métodos retornan NUEVO dict
   - NUNCA modifican metadata in-place
   - Sigue patrón funcional y previene bugs sutiles

3. **Naming Convention:**
   - Métodos `clear_*`: eliminan flags
   - Métodos `set_*`: establecen flags (y limpian mutuamente excluyentes)
   - Métodos `get_*`: obtienen valores
   - Métodos `increment_*`: incrementan contadores

4. **Future Extensions:**
   Si en el futuro necesitamos más flags:
   - Agregar método `clear_[new_flag]_flags()`
   - Agregar a `clear_all_flow_flags()`
   - Un solo lugar para mantener, no 9+ archivos

5. **Mutual Exclusivity:**
   - Correction y Modification son mutuamente excluyentes
   - `set_correction_flags()` automáticamente limpia modification
   - `set_modification_flags()` automáticamente limpia correction
   - Esto previene estados inconsistentes

**Testing Strategy:**

- Test cada método independientemente
- Test immutability (original no se modifica)
- Test mutual exclusivity (correction vs modification)
- Test graceful handling (missing keys no causa errores)
- Test edge cases (empty dict, partial flags, etc.)

**Migration Notes:**

Para desarrolladores que revisen este cambio:
- Antes: 9+ lugares con lógica duplicada
- Después: 1 lugar centralizado (`MetadataManager`)
- Si necesitas limpiar metadata flags: usa `MetadataManager`
- No copies/pegues código de metadata clearing nunca más
