# Training Datasets

This directory contains training datasets used for DSPy optimization.

## Generating Dataset

Datasets are generated automatically by the optimization script:

```bash
uv run python scripts/generate_baseline_optimization.py
```

This creates `baseline_v1.json` containing all training examples.

## Dataset Format

```json
{
  "version": "1.0",
  "created_at": "2025-12-16T...",
  "total_examples": 500,
  "examples": [
    {
      "user_message": "...",
      "history": {...},
      "context": {...},
      "result": {...}
    }
  ]
}
```

## Custom Datasets

You can create custom datasets using the `DatasetBuilder`:

```python
from soni.dataset import DatasetBuilder

builder = DatasetBuilder()
trainset = builder.build(
    patterns=["slot_value", "correction"],
    domains=["flight_booking"],
    examples_per_combination=5,
)
```
