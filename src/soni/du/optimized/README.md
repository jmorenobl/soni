# Soni Framework - Pre-trained NLU Models

This directory contains pre-trained NLU modules that ship with the Soni framework.

## Baseline v1

**File:** `baseline_v1.json`
**Created:** 2025-12-14
**Training examples:** 198

### Optimization Metrics

- **Baseline accuracy:** 58.11%
- **Optimized accuracy:** 87.51%
- **Improvement:** +29.4%
- **Optimizer:** MIPROv2
- **Trials:** 50
- **Training time:** 2406.5s

### Dataset Coverage

The baseline optimization covers:
- **9 conversational patterns**: SLOT_VALUE, CORRECTION, MODIFICATION, INTERRUPTION, DIGRESSION, CLARIFICATION, CANCELLATION, CONFIRMATION, CONTINUATION
- **4 business domains**: flight_booking, hotel_booking, restaurant, ecommerce
- **2 conversation contexts**: cold_start (no history), ongoing (with history)

### Usage

This module is automatically loaded by `SoniDU()` if no custom optimization is provided:

```python
from soni.du.modules import SoniDU

# Uses baseline_v1.json automatically
nlu = SoniDU()
```

To use a custom optimization:

```python
# Load custom optimized module
nlu = SoniDU()
nlu.load("path/to/custom_optimized.json")
```

Or train your own:

```python
from soni.dataset import DatasetBuilder
from soni.du.optimizers import optimize_soni_du

# Generate custom dataset
builder = DatasetBuilder()
trainset = builder.build(
    patterns=["slot_value", "correction"],  # Subset for your domain
    domains=["flight_booking"],
    contexts=["ongoing"],
    examples_per_combination=5,
)

# Optimize
optimized_nlu, metrics = optimize_soni_du(
    trainset=trainset,
    optimizer_type="MIPROv2",
    num_trials=50,
    output_dir="./my_optimization",
)
```

### Regenerating Baseline

To regenerate the baseline optimization (e.g., after dataset changes):

```bash
uv run python scripts/generate_baseline_optimization.py
```

**Note:** This requires `OPENAI_API_KEY` environment variable.

## Version History

### v1 (2025-12-14)
- Initial baseline optimization
- 198 training examples
- 87.51% accuracy on training set
- Covers 9 patterns × 4 domains × 2 contexts

## Custom Optimizations

Projects can create domain-specific optimizations:

1. **Create custom dataset** with project-specific examples
2. **Run optimization** with `optimize_soni_du()`
3. **Load custom module** in production:

```python
nlu = SoniDU()
nlu.load("optimizations/production_v2.json")
```

See [docs/design/09-dspy-optimization.md](../../docs/design/09-dspy-optimization.md) for details.
