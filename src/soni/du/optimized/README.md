# Soni Framework - Pre-trained NLU Models

This directory contains pre-trained NLU modules that ship with the Soni framework.

## Baseline v1

**File:** `baseline_v1.json`
**Created:** 2025-12-17
**Training examples:** 137

### Optimization Metrics

- **Baseline accuracy:** N/A
- **Optimized accuracy:** N/A
- **Optimizer:** MIPROv2 (auto=light)
- **Training time:** 298.4s

### Dataset Coverage

The baseline optimization covers:
- **8 conversational patterns**: SLOT_VALUE, CORRECTION, MODIFICATION, INTERRUPTION,
  DIGRESSION, CLARIFICATION, CANCELLATION, CONFIRMATION
- **5 business domains**: flight_booking, hotel_booking, restaurant, ecommerce, banking
- **2 conversation contexts**: cold_start (no history), ongoing (with history)

### Usage

This module is automatically loaded by `SoniDU()` if available:

```python
from soni.du.modules import SoniDU

# Default - uses baseline if available
nlu = SoniDU()
```

To use a custom optimization:

```python
nlu = SoniDU()
nlu.load("path/to/custom_optimized.json")
```

### Regenerating Baseline

To regenerate the baseline optimization:

```bash
uv run python scripts/generate_baseline_optimization.py
```

**Note:** Requires `OPENAI_API_KEY` environment variable.

## Version History

### v1 (2025-12-17)
- Initial baseline optimization
- 137 training examples
