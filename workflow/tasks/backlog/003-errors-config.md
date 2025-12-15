## Task: 003 - Errors and Config

**ID de tarea:** 003
**Hito:** 1 - Core Foundations
**Dependencias:** 001, 002
**Duración estimada:** 4 horas

### Objetivo

Implement custom exception hierarchy and configuration loading from YAML.

### Entregables

- [ ] `core/errors.py` with SoniError hierarchy
- [ ] `core/config.py` with SoniConfig, FlowConfig, StepConfig
- [ ] YAML loading and validation
- [ ] Unit tests for both modules

### Implementación Detallada

**Archivo:** `src/soni/core/errors.py`

```python
"""Custom exception hierarchy for Soni."""


class SoniError(Exception):
    """Base exception for all Soni errors."""
    pass


class ConfigError(SoniError):
    """Configuration-related errors."""
    pass


class FlowError(SoniError):
    """Flow execution errors."""
    pass


class FlowStackError(FlowError):
    """Flow stack operations error (empty stack, etc.)."""
    pass


class ValidationError(SoniError):
    """Validation errors for slots, config, etc."""
    pass


class ActionError(SoniError):
    """Action execution errors."""
    pass


class NLUError(SoniError):
    """NLU/DU errors."""
    pass
```

**Archivo:** `src/soni/core/config.py`

```python
"""Configuration models for Soni."""
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field


class StepConfig(BaseModel):
    """Configuration for a flow step."""
    
    step: str
    type: str  # collect, action, branch, confirm, say, while
    slot: str | None = None
    call: str | None = None
    message: str | None = None
    input: str | None = None
    cases: dict[str, str] | None = None
    condition: str | None = None
    do: list[str] | None = None
    jump_to: str | None = None


class FlowConfig(BaseModel):
    """Configuration for a single flow."""
    
    description: str
    steps: list[StepConfig] | None = None
    process: list[StepConfig] | None = None
    
    @property
    def steps_or_process(self) -> list[StepConfig]:
        return self.process or self.steps or []


class SoniConfig(BaseModel):
    """Root configuration for Soni."""
    
    version: str = "1.0"
    flows: dict[str, FlowConfig] = Field(default_factory=dict)
    
    @classmethod
    def load(cls, path: str | Path) -> "SoniConfig":
        """Load configuration from YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        return cls(**data)
```

### TDD Cycle

```python
# tests/unit/core/test_errors.py
def test_soni_error_is_base_exception():
    from soni.core.errors import SoniError
    assert issubclass(SoniError, Exception)

def test_flow_stack_error_inherits_from_flow_error():
    from soni.core.errors import FlowError, FlowStackError
    assert issubclass(FlowStackError, FlowError)

# tests/unit/core/test_config.py
def test_soni_config_loads_from_yaml(tmp_path):
    config_file = tmp_path / "soni.yaml"
    config_file.write_text("""
version: "1.0"
flows:
  book_flight:
    description: Book a flight
    steps:
      - step: collect_origin
        type: collect
        slot: origin
""")
    
    config = SoniConfig.load(config_file)
    
    assert "book_flight" in config.flows
    assert len(config.flows["book_flight"].steps_or_process) == 1
```

### Criterios de Éxito

- [ ] All error classes inherit from SoniError
- [ ] SoniConfig loads YAML correctly
- [ ] Validation errors have clear messages
- [ ] Tests pass with 100% coverage
