# Pre-trained NLU Models

This directory contains pre-trained NLU modules that ship with the Soni framework.

## Generating Baseline Optimization

To generate the baseline optimization:

```bash
uv run python scripts/generate_baseline_optimization.py
```

This will create:
- `baseline_v1.json` - The optimized DSPy module
- `baseline_v1_metrics.json` - Optimization metrics

## Usage

The optimized module is automatically loaded by `SoniDU()` when available.

```python
from soni.du.modules import SoniDU

nlu = SoniDU()  # Uses baseline if available
```

## Requirements

- `OPENAI_API_KEY` environment variable set
- Run from project root directory
