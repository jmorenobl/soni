# Soni v2 - Milestone 9: DSPy Prompt Optimization

**Status**: Ready for Review  
**Date**: 2025-12-21  
**Type**: Design Document  
**Depends On**: M4 (CommandGenerator NLU)

---

## 1. Objective

Implement DSPy prompt optimization for NLU modules, providing automatic prompt engineering without manual training data. This is a **key differentiator vs Rasa CALM**.

**Features:**
- MIPROv2 and GEPA optimizer support
- Dataset generation from domain definitions
- Optimized model persistence (JSON)
- CLI for optimization workflows

---

## 2. Why This Matters (Rasa CALM Comparison)

| Feature | Rasa CALM | Soni v2 |
|---------|-----------|---------|
| Training Data | **Required** (YAML examples) | **Auto-generated** from domain |
| Prompt Engineering | Manual | **Automatic via MIPROv2/GEPA** |
| Model Lock-in | Rasa models only | Any LLM (OpenAI, Anthropic, etc.) |
| Optimization | Not supported | **DSPy optimizers** |

---

## 3. Legacy Code Reference

### 3.1 OptimizableDSPyModule (REUSE)

**Source**: `archive/v1/src/soni/du/base.py`

```python
class OptimizableDSPyModule(dspy.Module):
    """Base class with automatic optimized model loading."""
    
    optimized_files: ClassVar[list[str]] = []  # Priority-ordered
    default_use_cot: ClassVar[bool] = True
    
    def __init__(self, use_cot: bool | None = None):
        super().__init__()
        self._use_cot = use_cot if use_cot is not None else self.default_use_cot
        self.extractor = self._create_extractor(self._use_cot)
        self._load_optimized_if_available()
```

### 3.2 Optimizer Functions (REUSE)

**Source**: `archive/v1/src/soni/du/optimizer.py`

```python
def optimize_du(
    trainset: list[Example],
    metric: Callable,
    optimizer_type: str = "miprov2",  # or "gepa"
    auto: str = "light",              # light, medium, heavy
    ...
) -> SoniDU: ...

def optimize_slot_extractor(...) -> SlotExtractor: ...
```

### 3.3 Dataset Generation (REUSE)

**Source**: `archive/v1/src/soni/dataset/`

```python
# Pattern-based example generation
class DatasetBuilder:
    def build(self, config: SoniConfig) -> list[Example]: ...

# Domain-specific examples
class DomainExampleData:
    flow_examples: list[FlowExample]
    slot_extraction_cases: list[SlotExtractionCase]
```

---

## 4. New/Modified Files

### 4.1 du/base.py (Copy from archive)

```python
"""OptimizableDSPyModule - Base for optimizable modules."""

from abc import abstractmethod
from pathlib import Path
from typing import ClassVar

import dspy


class OptimizableDSPyModule(dspy.Module):
    """Base class for DSPy modules supporting optimization.
    
    Features:
    - Automatic loading of best optimized model
    - Configurable CoT vs Predict
    - Standard async/sync interfaces
    """
    
    optimized_files: ClassVar[list[str]] = []
    default_use_cot: ClassVar[bool] = True
    
    def __init__(self, use_cot: bool | None = None):
        super().__init__()
        self._use_cot = use_cot if use_cot is not None else self.default_use_cot
        self.extractor = self._create_extractor(self._use_cot)
        self._load_optimized_if_available()
    
    @abstractmethod
    def _create_extractor(self, use_cot: bool) -> dspy.Module:
        """Create the predictor/extractor."""
        ...
    
    def _load_optimized_if_available(self) -> None:
        """Load best available optimized model."""
        optimized_dir = Path(__file__).parent / "optimized"
        
        for filename in self.optimized_files:
            path = optimized_dir / filename
            if path.exists():
                self.load(str(path))
                return
```

### 4.2 du/optimizer.py

```python
"""DSPy Optimization with MIPROv2 and GEPA."""

from collections.abc import Callable
from typing import Any

import dspy
from dspy import Example
from dspy.teleprompt import MIPROv2

from soni.du.modules import SoniDU


def create_metric(
    validate_command_fn: Callable | None = None,
) -> Callable:
    """Create evaluation metric for optimization."""
    
    def metric(example: Example, prediction: Any, trace: Any = None) -> float:
        expected = example.result.commands
        actual = prediction.result.commands if hasattr(prediction.result, "commands") else []
        
        if len(expected) != len(actual):
            return 0.0
        
        matches = sum(
            1 for e, a in zip(expected, actual)
            if _commands_match(e, a, validate_command_fn)
        )
        return matches / len(expected) if expected else 1.0
    
    return metric


def optimize_du(
    trainset: list[Example],
    metric: Callable,
    valset: list[Example] | None = None,
    optimizer_type: str = "miprov2",
    auto: str = "light",
    prompt_model: Any = None,
    teacher_model: Any = None,
    verbose: bool = True,
) -> SoniDU:
    """Optimize SoniDU with chosen optimizer.
    
    Args:
        trainset: Training examples
        metric: Evaluation metric
        valset: Validation examples (optional)
        optimizer_type: "miprov2" or "gepa"
        auto: Optimization intensity ("light", "medium", "heavy")
    """
    du = SoniDU(use_cot=True)
    
    if optimizer_type == "miprov2":
        optimizer = MIPROv2(
            metric=metric,
            auto=auto,
            prompt_model=prompt_model,
            teacher_model=teacher_model,
        )
        optimized = optimizer.compile(du, trainset=trainset)
    else:
        # GEPA optimizer
        from dspy.teleprompt import GEPA
        optimizer = GEPA(metric=metric, auto=auto)
        optimized = optimizer.compile(du, trainset=trainset, valset=valset)
    
    return optimized
```

### 4.3 dataset/builder.py

```python
"""Dataset generation from domain configuration."""

from dspy import Example

from soni.config import SoniConfig
from soni.dataset.patterns import INTENT_PATTERNS, SLOT_PATTERNS


class DatasetBuilder:
    """Generate training examples from flow definitions."""
    
    def build(self, config: SoniConfig) -> list[Example]:
        """Build training dataset from config."""
        examples = []
        
        for flow_name, flow in config.flows.items():
            # Generate intent examples
            examples.extend(self._generate_intent_examples(flow_name, flow))
            
            # Generate slot extraction examples
            examples.extend(self._generate_slot_examples(flow_name, flow))
        
        return examples
    
    def _generate_intent_examples(self, flow_name: str, flow) -> list[Example]:
        # Use trigger phrases + pattern variations
        ...
    
    def _generate_slot_examples(self, flow_name: str, flow) -> list[Example]:
        # Generate examples for each collect step
        ...
```

### 4.4 cli/optimize.py

```python
"""CLI for optimization workflows."""

import typer

from soni.config import ConfigLoader
from soni.dataset.builder import DatasetBuilder
from soni.du.optimizer import create_metric, optimize_du


app = typer.Typer()


@app.command()
def run(
    config_path: str = typer.Argument(..., help="Path to domain config"),
    output: str = typer.Option("optimized.json", help="Output file"),
    optimizer: str = typer.Option("miprov2", help="Optimizer: miprov2 or gepa"),
    auto: str = typer.Option("light", help="Intensity: light, medium, heavy"),
):
    """Run DSPy optimization on SoniDU."""
    # Load config
    config = ConfigLoader().load(config_path)
    
    # Generate dataset
    builder = DatasetBuilder()
    trainset = builder.build(config)
    
    # Optimize
    metric = create_metric()
    optimized_du = optimize_du(
        trainset=trainset,
        metric=metric,
        optimizer_type=optimizer,
        auto=auto,
    )
    
    # Save
    optimized_du.save(output)
    typer.echo(f"Saved optimized model to {output}")


# soni optimize run --config examples/banking/domain
```

---

## 5. TDD Tests (AAA Format)

### 5.1 Integration Test

```python
# tests/integration/test_m9_optimization.py
@pytest.mark.asyncio
async def test_optimization_improves_accuracy():
    """Optimization improves NLU accuracy on test set."""
    # Arrange
    config = load_test_config()
    builder = DatasetBuilder()
    trainset = builder.build(config)
    testset = trainset[:5]  # Hold out for testing
    trainset = trainset[5:]
    
    # Act - Baseline
    baseline_du = SoniDU(use_cot=False)
    baseline_score = evaluate(baseline_du, testset)
    
    # Act - Optimized
    metric = create_metric()
    optimized_du = optimize_du(trainset, metric, auto="light")
    optimized_score = evaluate(optimized_du, testset)
    
    # Assert
    assert optimized_score >= baseline_score
```

### 5.2 Unit Tests

```python
# tests/unit/du/test_optimizer.py
def test_create_metric_returns_callable():
    """create_metric returns a callable."""
    # Arrange & Act
    metric = create_metric()
    
    # Assert
    assert callable(metric)


def test_dataset_builder_generates_examples():
    """DatasetBuilder generates examples from config."""
    # Arrange
    config = SoniConfig(flows={"greet": FlowConfig(...)})
    builder = DatasetBuilder()
    
    # Act
    examples = builder.build(config)
    
    # Assert
    assert len(examples) > 0
    assert all(hasattr(e, "user_message") for e in examples)
```

---

## 6. Success Criteria

- [ ] `uv run soni optimize run --config examples/banking/domain` works
- [ ] Optimized model saved to JSON
- [ ] Optimized model loads automatically in SoniDU
- [ ] Tests pass for DatasetBuilder
- [ ] Documentation for optimization workflow

---

## 7. Implementation Order

1. Write tests first (RED)
2. `du/base.py` - OptimizableDSPyModule
3. `du/optimizer.py` - Optimizer functions
4. `dataset/builder.py` - Dataset generation
5. `cli/optimize.py` - CLI commands
6. Run tests (GREEN)
7. Test with banking domain

---

## 8. Baseline Optimization Script (EXISTS - NOT ARCHIVED)

### 8.1 generate_baseline_optimization.py

**Location**: `scripts/generate_baseline_optimization.py` (NOT archived - stays in scripts/)

This script already exists and will continue to work with the new implementation.
The key requirement is that **M4's SoniDU implementation MUST include the auto-loading pattern**.

```python
#!/usr/bin/env python3
"""Generate baseline NLU optimization for Soni framework.

This script generates a baseline optimized NLU module that will be shipped
with the framework to provide reasonable out-of-the-box performance.

Usage:
    uv run python scripts/generate_baseline_optimization.py --auto medium
"""

def main(auto: str = "medium", optimizer: str = "miprov2") -> int:
    """Generate baseline optimization."""
    
    # 1. Generate dataset from all patterns and domains
    builder = DatasetBuilder()
    trainset = builder.build_all(
        examples_per_combination=5,
        include_edge_cases=True,
    )
    
    # 2. Stratified split (ensures all command types represented)
    train_split, val_split = stratified_split(trainset, train_ratio=0.9)
    
    # 3. Optimize SoniDU
    optimized = optimize_du(
        trainset=train_split,
        valset=val_split,
        metric=create_granular_metric(),
        auto=auto,
        optimizer_type=optimizer,
    )
    
    # 4. Optimize SlotExtractor
    generate_and_optimize_slots(...)
    
    # 5. Save to src/soni/du/optimized/
    optimized.save("src/soni/du/optimized/baseline_v1_miprov2.json")
```

### 8.2 Auto-Loading Pattern (CRITICAL for M4)

> [!IMPORTANT]
> M4 MUST implement `OptimizableDSPyModule` with `create_with_best_model()` to preserve this feature.

The `create_with_best_model()` pattern ensures automatic loading:

```python
class SoniDU(OptimizableDSPyModule):
    """Dialogue Understanding with automatic optimization loading."""
    
    # Priority-ordered optimization files
    optimized_files: ClassVar[list[str]] = [
        "baseline_v1_miprov2.json",
        "baseline_v1_gepa.json", 
        "baseline_v1.json",
    ]
    
    # ... rest of class

# Auto-loading in NLUService:
class NLUService:
    def __init__(self, du: DUProtocol | None = None):
        # Auto-load best optimization if available
        self.du = du or SoniDU.create_with_best_model()
```

### 8.3 Output Structure

```
src/soni/du/
├── optimized/
│   ├── README.md                    # Auto-generated docs
│   ├── baseline_v1_miprov2.json     # Optimized SoniDU
│   ├── baseline_v1_slots_miprov2.json  # Optimized SlotExtractor
│   └── baseline_v1_metrics.json     # Metrics for tracking
└── datasets/
    ├── baseline_v1.json             # Training dataset
    └── baseline_v1_slots.json       # Slot extraction dataset
```

---

## 9. Why This Matters

```
Traditional NLU (Rasa):
    Define intents → Write training data → Train model → Test → Repeat

Soni v2 with DSPy:
    Define flows → Generate examples automatically → Optimize → Done
```

**Time savings estimate**: 10x faster iteration cycle for NLU improvements.
