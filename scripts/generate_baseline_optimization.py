#!/usr/bin/env python3
"""Generate baseline NLU optimization for Soni framework.

This script generates a baseline optimized NLU module that will be shipped
with the framework to provide reasonable out-of-the-box performance.

The baseline optimization:
- Uses the complete dataset (all patterns, domains, contexts)
- Runs MIPROv2 or GEPA optimization with conservative parameters
- Saves both the dataset and optimized module
- Can be regenerated when dataset or patterns change

Usage:
    # Default (MIPROv2):
    uv run python scripts/generate_baseline_optimization.py

    # Use GEPA optimizer:
    uv run python scripts/generate_baseline_optimization.py --optimizer GEPA

Output:
    - src/soni/du/optimized/baseline_v1.json (optimized module)
    - src/soni/du/datasets/baseline_v1.json (training dataset)
    - Optimization metrics printed to console
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import dspy

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from soni.dataset import DatasetBuilder, print_dataset_stats, validate_dataset
from soni.du.optimizers import optimize_soni_du


def save_dataset(examples: list[dspy.Example], output_path: Path) -> None:
    """Save dataset to JSON for reproducibility.

    Args:
        examples: List of dspy.Example instances
        output_path: Path to save dataset
    """
    # Convert examples to serializable format
    dataset_dict = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "total_examples": len(examples),
        "examples": [
            {
                "user_message": ex.user_message,
                "context": ex.context.model_dump()
                if hasattr(ex.context, "model_dump")
                else ex.context,
                "result": ex.result.model_dump() if hasattr(ex.result, "model_dump") else ex.result,
            }
            for ex in examples
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset_dict, f, indent=2, ensure_ascii=False)

    print(f"✅ Dataset saved to: {output_path}")


def main():
    """Generate baseline optimization."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate baseline NLU optimization for Soni framework"
    )
    parser.add_argument(
        "--optimizer",
        type=str,
        choices=["MIPROv2", "GEPA"],
        default="GEPA",  # GEPA is now the default (better performance)
        help="Optimizer to use (default: GEPA)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=50,
        help="Number of optimization trials (default: 50)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Soni Framework - Baseline NLU Optimization Generator")
    print("=" * 70)

    # Step 0: Load environment variables from .env
    print("\n🔑 Loading environment variables...")
    try:
        from dotenv import load_dotenv

        # Try to load .env from project root
        project_root = Path(__file__).parent.parent
        env_path = project_root / ".env"

        if env_path.exists():
            load_dotenv(env_path)
            print(f"   ✅ Loaded .env from {env_path}")
        else:
            load_dotenv()  # Try to load from default locations
            print("   ℹ️  No .env file found, using system environment")
    except ImportError:
        print("   ⚠️  python-dotenv not installed, using system environment only")
        print("   Install with: uv add python-dotenv")

    # Check if API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not found")
        print("   Please either:")
        print("   1. Add OPENAI_API_KEY='your-key' to .env file")
        print("   2. Or export OPENAI_API_KEY='your-key' in your shell")
        sys.exit(1)

    print("   ✅ OPENAI_API_KEY found")

    # Step 1: Generate dataset
    print("\n📊 Step 1: Generating training dataset...")
    builder = DatasetBuilder()

    # Show what we have
    stats = builder.get_stats()
    print(f"   - Patterns available: {stats['patterns']}")
    print(f"   - Domains available: {stats['domains']}")
    print(f"   - Contexts: {stats['contexts']}")
    print(f"   - Max combinations: {stats['max_combinations']}")

    # Generate complete dataset
    # Use 3 examples per combination for better coverage of edge cases
    trainset = builder.build_all(examples_per_combination=3)

    print(f"\n   Generated {len(trainset)} training examples")

    # Validate dataset
    print("\n   Validating dataset...")
    try:
        validate_dataset(trainset)
        print("   ✅ Dataset validated successfully")
    except ValueError as e:
        print(f"   ⚠️  Dataset validation warning: {e}")

    # Print stats
    print("\n   Dataset statistics:")
    print_dataset_stats(trainset)

    # Save dataset
    dataset_path = Path("src/soni/du/datasets/baseline_v1.json")
    save_dataset(trainset, dataset_path)

    # Step 2: Configure DSPy
    print("\n⚙️  Step 2: Configuring DSPy...")

    # Configure LM
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)
    print(f"   ✅ Configured LM: {lm.model}")

    # Step 3: Optimize
    print("\n🚀 Step 3: Running optimization...")
    print("   This may take 15-30 minutes depending on dataset size...")
    print(f"   Optimizer: {args.optimizer}")
    print(f"   Trials: {args.trials}")
    print(f"   Training examples: {len(trainset)}")

    output_dir = Path("src/soni/du/optimized")

    try:
        # Configure optimizer-specific parameters
        if args.optimizer == "GEPA":
            # GEPA uses reflective prompt evolution - simpler config
            _optimized_nlu, metrics = optimize_soni_du(
                trainset=trainset,
                optimizer_type="GEPA",
                num_trials=args.trials,
                timeout_seconds=1800,
                output_dir=output_dir,
            )
        else:  # MIPROv2
            _optimized_nlu, metrics = optimize_soni_du(
                trainset=trainset,
                optimizer_type="MIPROv2",
                num_trials=args.trials,
                timeout_seconds=1800,
                output_dir=output_dir,
                num_candidates=75,
                max_bootstrapped_demos=6,
                max_labeled_demos=8,
                minibatch_size=20,
                init_temperature=1.0,
            )

        print("\n" + "=" * 70)
        print("✅ Optimization Complete!")
        print("=" * 70)

        # Print metrics
        print("\n📈 Optimization Metrics:")
        print(f"   Baseline accuracy:  {metrics['baseline_accuracy']:.2%}")
        print(f"   Optimized accuracy: {metrics['optimized_accuracy']:.2%}")
        print(f"   Improvement:        {metrics['improvement_pct']:+.1f}%")
        print(f"   Total time:         {metrics['total_time']:.1f}s")

        # Rename to baseline_v1.json
        old_path = output_dir / "optimized_nlu.json"
        new_path = output_dir / "baseline_v1.json"
        if old_path.exists():
            old_path.rename(new_path)
            print(f"\n💾 Optimized module saved to: {new_path}")

        # Save metrics
        metrics_path = output_dir / "baseline_v1_metrics.json"
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"   Metrics saved to: {metrics_path}")

        # Create README
        readme_path = output_dir / "README.md"
        create_readme(readme_path, metrics, len(trainset))

        print("\n🎉 Baseline optimization generated successfully!")
        print("\n📖 Next steps:")
        print("   1. Review metrics to ensure quality")
        print("   2. Test the optimized module")
        print("   3. Commit to repository (this will be shipped with framework)")
        print("   4. Users can override with custom optimizations")

        return 0

    except Exception as e:
        print(f"\n❌ Optimization failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


def create_readme(path: Path, metrics: dict, dataset_size: int) -> None:
    """Create README documenting the baseline optimization.

    Args:
        path: Path to README file
        metrics: Optimization metrics
        dataset_size: Number of training examples
    """
    readme_content = f"""# Soni Framework - Pre-trained NLU Models

This directory contains pre-trained NLU modules that ship with the Soni framework.

## Baseline v1

**File:** `baseline_v1.json`
**Created:** {datetime.now().strftime("%Y-%m-%d")}
**Training examples:** {dataset_size}

### Optimization Metrics

- **Baseline accuracy:** {metrics["baseline_accuracy"]:.2%}
- **Optimized accuracy:** {metrics["optimized_accuracy"]:.2%}
- **Improvement:** {metrics["improvement_pct"]:+.1f}%
- **Optimizer:** MIPROv2
- **Trials:** {metrics["num_trials"]}
- **Training time:** {metrics["total_time"]:.1f}s

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

### v1 ({datetime.now().strftime("%Y-%m-%d")})
- Initial baseline optimization
- {dataset_size} training examples
- {metrics["optimized_accuracy"]:.2%} accuracy on training set
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
"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(readme_content)

    print(f"   README created: {path}")


if __name__ == "__main__":
    sys.exit(main())
