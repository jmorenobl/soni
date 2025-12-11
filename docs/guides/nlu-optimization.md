# NLU Optimization Guide

This guide explains how to use the Soni framework's NLU optimization capabilities.

## Overview

Soni ships with a **baseline pre-trained NLU module** that provides reasonable out-of-the-box performance. You can also create **custom optimizations** tailored to your specific domain and use cases.

### What Gets Optimized

DSPy optimization improves the NLU's ability to:
- Classify message types accurately (SLOT_VALUE, CORRECTION, etc.)
- Extract slot values with correct metadata
- Detect intent changes and digressions
- Maintain high confidence on clear inputs

### Baseline Optimization (Included with Framework)

The framework includes a pre-trained baseline optimization in `src/soni/du/optimized/baseline_v1.json`:

```python
from soni.du.modules import SoniDU

# Automatically loads baseline optimization
nlu = SoniDU()
```

**Coverage:**
- **9 conversational patterns**: All MessageType patterns
- **4 business domains**: flight_booking, hotel_booking, restaurant, ecommerce
- **2 conversation contexts**: cold_start and ongoing
- **~150-200 training examples**: Manually curated for quality

This baseline provides general-purpose NLU that works across common dialogue scenarios.

## Using Baseline Optimization

### Automatic Loading (Default)

By default, `SoniDU()` automatically loads the baseline optimization:

```python
import dspy
from soni.du.modules import SoniDU

# Configure LM
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Create NLU - baseline loaded automatically
nlu = SoniDU()

# Use immediately
result = await nlu.predict(
    user_message="I want to fly to Madrid",
    history=dspy.History(messages=[]),
    context=dialogue_context,
)
```

### Disabling Baseline (For Testing)

To use the unoptimized module (e.g., during development):

```python
nlu = SoniDU(load_baseline=False)
```

## Creating Custom Optimizations

For production systems, you should create domain-specific optimizations using your own training data.

### Step 1: Create Training Dataset

Use the `soni.dataset` package to generate training examples:

```python
from soni.dataset import DatasetBuilder

builder = DatasetBuilder()

# Option A: Use all patterns and domains (similar to baseline)
trainset = builder.build_all(examples_per_combination=3)

# Option B: Customize for your domain
trainset = builder.build(
    patterns=["slot_value", "correction", "modification", "confirmation"],
    domains=["flight_booking"],  # Your specific domain
    contexts=["ongoing"],
    examples_per_combination=5,
)

print(f"Generated {len(trainset)} training examples")
```

### Step 2: Add Domain-Specific Examples

The generated dataset provides a foundation, but you should add real examples from your domain:

```python
import dspy
from soni.du.models import (
    DialogueContext,
    NLUOutput,
    MessageType,
    SlotValue,
)

# Add custom example
custom_example = dspy.Example(
    user_message="Change my flight to Barcelona",
    history=dspy.History(messages=[...]),
    context=DialogueContext(
        current_flow="book_flight",
        current_slots={"destination": "Madrid"},
        expected_slots=[],
        available_actions=["modify_booking"],
        available_flows=["book_flight"],
    ),
    result=NLUOutput(
        message_type=MessageType.MODIFICATION,
        command="book_flight",
        slots=[SlotValue(name="destination", value="Barcelona", confidence=0.95)],
        confidence=0.95,
        reasoning="User requests to change destination",
    ),
).with_inputs("user_message", "history", "context")

trainset.append(custom_example)
```

### Step 3: Run Optimization

```python
import dspy
from soni.du.optimizers import optimize_soni_du

# Configure LM
lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
dspy.configure(lm=lm)

# Run optimization
optimized_nlu, metrics = optimize_soni_du(
    trainset=trainset,
    optimizer_type="MIPROv2",  # Recommended for dialogue NLU
    num_trials=50,  # More trials = better optimization (but slower)
    timeout_seconds=1800,  # 30 minutes
    output_dir="./optimizations/production_v1",
    minibatch_size=4,
)

print(f"Baseline accuracy: {metrics['baseline_accuracy']:.2%}")
print(f"Optimized accuracy: {metrics['optimized_accuracy']:.2%}")
print(f"Improvement: {metrics['improvement_pct']:+.1f}%")
```

**Output:**
- `./optimizations/production_v1/optimized_nlu.json` - Optimized module
- Metrics printed to console

### Step 4: Load Custom Optimization in Production

```python
from soni.du.modules import SoniDU

# Create NLU
nlu = SoniDU()

# Load custom optimization (overrides baseline)
nlu.load("./optimizations/production_v1/optimized_nlu.json")

# Use in production
result = await nlu.predict(...)
```

## Optimization Best Practices

### Dataset Quality

1. **Coverage**: Ensure examples cover all patterns your users might use
2. **Variety**: Include multiple phrasings for each pattern
3. **Real Data**: Add real examples from your production logs
4. **Balance**: Don't over-represent common patterns (creates bias)

### Optimization Parameters

**num_trials:**
- Low (10-20): Quick experimentation
- Medium (30-50): Production baseline
- High (100+): Maximum quality (diminishing returns)

**minibatch_size:**
- Smaller (2-4): More stable, slower
- Larger (8-16): Faster, may be less stable
- Use validation set size / 4 as guideline

**timeout_seconds:**
- Set based on your num_trials and dataset size
- 30-60 seconds per trial is typical
- Monitor first few trials to estimate

### Iteration Workflow

1. **Start with baseline**: Use framework baseline for MVP
2. **Collect real data**: Gather examples from production logs
3. **Augment dataset**: Add domain-specific examples to generated dataset
4. **Optimize incrementally**: Run optimization with small num_trials first
5. **Validate thoroughly**: Test on held-out examples
6. **Deploy gradually**: A/B test against baseline
7. **Monitor metrics**: Track accuracy in production
8. **Repeat**: Continuously improve with new examples

## Regenerating Baseline (For Framework Maintainers)

To regenerate the framework's baseline optimization:

```bash
# Ensure OPENAI_API_KEY is set
export OPENAI_API_KEY='your-key-here'

# Run generation script
uv run python scripts/generate_baseline_optimization.py
```

**When to regenerate:**
- Dataset patterns/domains updated
- Bugs fixed in NLU logic
- Better optimization strategies discovered

**Output:**
- `src/soni/du/optimized/baseline_v1.json` (commit to repo)
- `src/soni/du/datasets/baseline_v1.json` (commit to repo)
- `src/soni/du/optimized/baseline_v1_metrics.json` (commit to repo)

## Troubleshooting

### Baseline Not Loading

**Symptom:** Logs show "Baseline optimization not found"

**Solution:** Regenerate baseline:
```bash
uv run python scripts/generate_baseline_optimization.py
```

### Low Optimization Accuracy

**Symptom:** Optimized accuracy < baseline accuracy

**Possible causes:**
- Dataset too small (need 20+ examples minimum)
- Dataset imbalanced (one pattern dominates)
- Validation set too small (MIPROv2 needs 4+ examples)

**Solutions:**
- Increase `examples_per_combination`
- Balance pattern distribution
- Increase `minibatch_size` if valset is small

### Optimization Too Slow

**Symptom:** Optimization takes hours

**Solutions:**
- Reduce `num_trials`
- Reduce dataset size (start with subset)
- Use faster LM (gpt-4o-mini instead of gpt-4)
- Set `timeout_seconds` to fail fast

### OOM (Out of Memory)

**Symptom:** Process crashes during optimization

**Solutions:**
- Reduce `minibatch_size`
- Reduce dataset size
- Run on machine with more RAM
- Use cloud GPU instance

## Advanced: Multi-Domain Optimization

For systems supporting multiple domains, you can:

1. **Create separate optimizations per domain:**
```python
# Flight booking optimization
flight_nlu = SoniDU()
flight_nlu.load("optimizations/flights_v1.json")

# Hotel booking optimization
hotel_nlu = SoniDU()
hotel_nlu.load("optimizations/hotels_v1.json")

# Route based on detected domain
if current_domain == "flights":
    result = await flight_nlu.predict(...)
else:
    result = await hotel_nlu.predict(...)
```

2. **Or create unified optimization with domain-specific examples:**
```python
# Single NLU with examples from all domains
trainset = builder.build(
    patterns=["slot_value", "correction", ...],
    domains=["flight_booking", "hotel_booking"],  # All your domains
    contexts=["ongoing"],
    examples_per_combination=10,  # More examples per combination
)

optimized_nlu, metrics = optimize_soni_du(trainset, num_trials=100)
```

## API Reference

### `optimize_soni_du()`

```python
def optimize_soni_du(
    trainset: list[dspy.Example],
    optimizer_type: str = "MIPROv2",
    num_trials: int = 30,
    timeout_seconds: int = 1200,
    output_dir: Path | str | None = None,
    minibatch_size: int = 4,
) -> tuple[SoniDU, dict[str, Any]]:
    """Optimize SoniDU module with DSPy.

    Args:
        trainset: Training examples
        optimizer_type: "MIPROv2" (recommended), "BootstrapFewShot", etc.
        num_trials: Number of optimization trials (more = better, slower)
        timeout_seconds: Max time for optimization
        output_dir: Where to save optimized module (optional)
        minibatch_size: Validation minibatch size (use valset_size/4)

    Returns:
        (optimized_module, metrics) where metrics contains:
            - baseline_accuracy: Accuracy before optimization
            - optimized_accuracy: Accuracy after optimization
            - improvement: Absolute improvement
            - improvement_pct: Percentage improvement
            - num_trials: Number of trials completed
            - total_time: Total optimization time
    """
```

### `SoniDU.load()`

```python
def load(self, path: str) -> None:
    """Load optimized module from file.

    Args:
        path: Path to optimized module JSON file

    Example:
        nlu = SoniDU()
        nlu.load("optimizations/production_v1/optimized_nlu.json")
    """
```

## See Also

- [DSPy Optimization (Design)](../design/09-dspy-optimization.md)
- [NLU System Architecture](../design/06-nlu-system.md)
- [Dataset Package](../../src/soni/dataset/README.md)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
