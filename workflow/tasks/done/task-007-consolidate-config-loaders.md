## Task: 007 - Consolidate Configuration Loaders

**ID de tarea:** 007
**Hito:** 2 - Quality Improvements
**Dependencias:** Ninguna
**Duración estimada:** 3 horas
**Prioridad:** MEDIA

### Objetivo

Eliminar las capas redundantes de indirección en el sistema de carga de configuración, consolidando a un único `ConfigLoader` en `soni.config.loader` y actualizando todos los imports en el codebase.

### Contexto

Actualmente existen tres capas de loaders que crean confusión:

1. **`soni.config.loader.ConfigLoader`** - Implementación real (96 líneas)
2. **`soni.core.loader.ConfigLoader`** - Facade que delega a config.loader (32 líneas)
3. **`soni.core.config`** - Re-exporta desde soni.config (línea 71)

**Problemas:**
- Tres lugares diferentes para importar lo mismo
- Código duplicado de mantenimiento
- Confusión sobre cuál usar
- `core.loader` existe solo por "backward compatibility" pero no hay versión 1.0

**Imports actuales en el código:**
```python
# server/api.py:16
from soni.core.loader import ConfigLoader

# cli/commands/server.py (implícito)
from soni.core.config import ConfigLoader

# Ambos funcionan pero son inconsistentes
```

### Entregables

- [ ] Eliminar `soni.core.loader.py` (facade innecesario)
- [ ] Actualizar `soni.core.config.py` para importar directamente de `soni.config`
- [ ] Actualizar todos los imports en el codebase para usar `soni.config.loader`
- [ ] Agregar deprecation warning temporal si se importa de ubicación antigua
- [ ] Documentar la ubicación canónica

### Implementación Detallada

#### Paso 1: Auditar imports actuales

**Comando para encontrar todos los imports:**

```bash
grep -r "from soni.core.loader import\|from soni.core.config import ConfigLoader" src/
grep -r "from soni.core.loader import\|from soni.core.config import ConfigLoader" tests/
```

**Ubicaciones conocidas:**
- `src/soni/server/api.py`
- `src/soni/cli/commands/server.py`
- `src/soni/cli/commands/chat.py`
- Tests varios

#### Paso 2: Actualizar imports en server/

**Archivo a modificar:** `src/soni/server/api.py`

```python
# ANTES
from soni.core.loader import ConfigLoader

# DESPUÉS
from soni.config.loader import ConfigLoader
```

#### Paso 3: Actualizar imports en cli/

**Archivo a modificar:** `src/soni/cli/commands/server.py`

```python
# ANTES
from soni.core.config import ConfigLoader

# DESPUÉS
from soni.config.loader import ConfigLoader
```

**Archivo a modificar:** `src/soni/cli/commands/chat.py`

```python
# ANTES
from soni.core.config import SoniConfig  # o similar

# DESPUÉS
from soni.config import SoniConfig
from soni.config.loader import ConfigLoader
```

#### Paso 4: Simplificar core/config.py

**Archivo a modificar:** `src/soni/core/config.py`

**ANTES (extracto):**
```python
"""Backward compatibility re-exports from soni.config package."""

from soni.config import (
    SoniConfig,
    FlowConfig,
    SlotConfig,
    # ... muchos más
)

# Re-export ConfigLoader for backwards compatibility
from soni.core.loader import ConfigLoader

__all__ = [
    "ConfigLoader",
    "SoniConfig",
    # ...
]
```

**DESPUÉS:**
```python
"""Re-exports from soni.config package.

DEPRECATED: Import directly from soni.config instead.
This module will be removed in v1.0.

Example:
    # Old (deprecated)
    from soni.core.config import SoniConfig

    # New (preferred)
    from soni.config import SoniConfig
"""

import warnings

# Issue deprecation warning on import
warnings.warn(
    "soni.core.config is deprecated. Import from soni.config instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from soni.config import (
    SoniConfig,
    FlowConfig,
    SlotConfig,
    ActionConfig,
    PatternConfig,
    SettingsConfig,
)

from soni.config.loader import ConfigLoader

__all__ = [
    "ConfigLoader",
    "SoniConfig",
    "FlowConfig",
    "SlotConfig",
    "ActionConfig",
    "PatternConfig",
    "SettingsConfig",
]
```

#### Paso 5: Eliminar core/loader.py

**Archivo a eliminar:** `src/soni/core/loader.py`

**ANTES (archivo completo):**
```python
"""Configuration loading facade.

This module provides a facade to soni.config.loader for backward compatibility.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from soni.core.errors import ConfigError

if TYPE_CHECKING:
    from soni.config.main import SoniConfig


class ConfigLoader:
    """Facade for configuration loading."""

    @staticmethod
    def load(path: str | Path) -> "SoniConfig":
        """Load configuration from file or directory."""
        # Import here to avoid circular dependency
        from soni.config.loader import ConfigLoader as RealLoader

        return RealLoader.load(path)

    def from_yaml(self, path: Path) -> "SoniConfig":
        """Load from YAML file."""
        from soni.config.loader import ConfigLoader as RealLoader

        return RealLoader().from_yaml(path)
```

**DESPUÉS:** Eliminar archivo completamente.

#### Paso 6: Actualizar __init__.py de core

**Archivo a modificar:** `src/soni/core/__init__.py`

Remover cualquier export de `loader` si existe.

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/config/test_loader_consolidation.py`

```python
import pytest
import warnings


class TestConfigLoaderImports:
    """Tests for consolidated ConfigLoader imports."""

    def test_import_from_config_loader(self):
        """Test that ConfigLoader can be imported from soni.config.loader."""
        from soni.config.loader import ConfigLoader

        assert ConfigLoader is not None
        assert hasattr(ConfigLoader, "load")

    def test_import_from_config_package(self):
        """Test that ConfigLoader can be imported from soni.config."""
        from soni.config import ConfigLoader

        assert ConfigLoader is not None

    def test_deprecated_core_config_import_warns(self):
        """Test that importing from core.config issues deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # This should trigger deprecation warning
            from soni.core import config as core_config

            # Reload to trigger warning (may be cached)
            import importlib
            importlib.reload(core_config)

            assert len(w) >= 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "deprecated" in str(w[-1].message).lower()

    def test_core_loader_removed(self):
        """Test that soni.core.loader no longer exists."""
        with pytest.raises(ImportError):
            from soni.core.loader import ConfigLoader


class TestConfigLoaderFunctionality:
    """Tests that ConfigLoader works correctly after consolidation."""

    def test_load_from_file(self, tmp_path):
        """Test loading config from YAML file."""
        from soni.config.loader import ConfigLoader

        config_file = tmp_path / "soni.yaml"
        config_file.write_text("""
settings:
  models:
    provider: openai
    model: gpt-4
flows:
  greeting:
    name: greeting
    description: A greeting flow
    steps:
      - step: greet
        type: say
        message: Hello!
""")

        config = ConfigLoader.load(config_file)

        assert config is not None
        assert "greeting" in config.flows

    def test_load_from_directory(self, tmp_path):
        """Test loading config from directory with multiple YAML files."""
        from soni.config.loader import ConfigLoader

        # Create multiple YAML files
        (tmp_path / "settings.yaml").write_text("""
settings:
  models:
    provider: openai
    model: gpt-4
""")

        (tmp_path / "flows.yaml").write_text("""
flows:
  greeting:
    name: greeting
    steps:
      - step: greet
        type: say
        message: Hello!
""")

        config = ConfigLoader.load(tmp_path)

        assert config is not None
        assert config.settings.models.provider == "openai"
        assert "greeting" in config.flows
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/config/test_loader_consolidation.py -v
# Expected: test_core_loader_removed FAILS (module still exists)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for config loader consolidation"
```

#### Green Phase: Make Tests Pass

See "Implementación Detallada" section.

**Verify tests pass:**
```bash
uv run pytest tests/unit/config/test_loader_consolidation.py -v
# Expected: PASSED
```

**Commit:**
```bash
git add src/ tests/
git commit -m "refactor: consolidate config loaders to single location

- Remove soni.core.loader facade
- Add deprecation warning to soni.core.config
- Update all imports to use soni.config.loader
- Single source of truth for ConfigLoader"
```

### Criterios de Éxito

- [ ] `soni.core.loader` eliminado
- [ ] `soni.core.config` tiene deprecation warning
- [ ] Todos los imports usan `soni.config.loader` o `soni.config`
- [ ] No hay imports rotos en el código
- [ ] Todos los tests pasan
- [ ] Linting pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Verificar que core.loader no existe
python -c "from soni.core.loader import ConfigLoader" 2>&1
# Esperado: ImportError

# Verificar deprecation warning
python -c "from soni.core.config import SoniConfig" 2>&1
# Esperado: DeprecationWarning

# Verificar import correcto funciona
python -c "from soni.config.loader import ConfigLoader; print('OK')"
# Esperado: OK

# Buscar imports antiguos
grep -r "from soni.core.loader" src/ tests/
# Esperado: ningún resultado

# Ejecutar tests
uv run pytest -v
```

### Referencias

- `src/soni/config/loader.py` - Implementación canónica
- `src/soni/core/loader.py` - A eliminar
- `src/soni/core/config.py` - A simplificar

### Notas Adicionales

**Plan de migración:**
1. Actualizar imports primero (sin eliminar archivos)
2. Verificar que todo funciona
3. Agregar deprecation warnings
4. Eliminar `core/loader.py`
5. Documentar cambio en CHANGELOG

**Consideraciones:**
- Si hay usuarios externos, mantener deprecation warning por 1-2 releases
- Como no hay v1.0, podemos ser más agresivos con la limpieza
