"""Soni Configuration Package.

Provides configuration models and loading utilities.
All exports are backwards-compatible with the original core/config.py.
"""

# Models
from soni.config.loader import ConfigLoader
from soni.config.main import SoniConfig
from soni.config.models import (
    FlowConfig,
    SlotConfig,
    TriggerConfig,
)

# Patterns
from soni.config.patterns import (
    CancellationPatternConfig,
    ClarificationPatternConfig,
    ConfirmationPatternConfig,
    CorrectionPatternConfig,
    HumanHandoffPatternConfig,
    PatternBehaviorsConfig,
)

# Settings
from soni.config.settings import (
    ModelsConfig,
    NLUModelConfig,
    PersistenceConfig,
    SettingsConfig,
)

# Step types (discriminated unions)
from soni.config.steps import (
    ActionStepConfig,
    BaseStepConfig,
    BranchStepConfig,
    CollectStepConfig,
    ConfirmStepConfig,
    SayStepConfig,
    SetStepConfig,
    StepConfig,
    WhileStepConfig,
)

__all__ = [
    # Models
    "TriggerConfig",
    "SlotConfig",
    "FlowConfig",
    # Step types
    "StepConfig",
    "BaseStepConfig",
    "SayStepConfig",
    "CollectStepConfig",
    "ActionStepConfig",
    "BranchStepConfig",
    "ConfirmStepConfig",
    "WhileStepConfig",
    "SetStepConfig",
    # Patterns
    "ConfirmationPatternConfig",
    "CorrectionPatternConfig",
    "ClarificationPatternConfig",
    "CancellationPatternConfig",
    "HumanHandoffPatternConfig",
    "PatternBehaviorsConfig",
    # Settings
    "NLUModelConfig",
    "ModelsConfig",
    "PersistenceConfig",
    "SettingsConfig",
    # Main
    "SoniConfig",
    "ConfigLoader",
]
