#!/usr/bin/env python3
"""Generate baseline NLU optimization for Soni framework.

This script generates a baseline optimized NLU module that will be shipped
with the framework to provide reasonable out-of-the-box performance.

The baseline optimization:
- Uses the complete dataset (all patterns, domains, contexts)
- Runs MIPROv2 optimization with configurable parameters
- Saves both the dataset and optimized module
- Can be regenerated when dataset or patterns change

Usage:
    # Default (light optimization):
    uv run python scripts/generate_baseline_optimization.py

    # Medium optimization (more trials):
    uv run python scripts/generate_baseline_optimization.py --auto medium

    # Heavy optimization (maximum quality):
    uv run python scripts/generate_baseline_optimization.py --auto heavy

Output:
    - src/soni/du/optimized/baseline_v1.json (optimized module)
    - src/soni/du/datasets/baseline_v1.json (training dataset)
    - Optimization metrics printed to console
"""

import json
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import dspy  # noqa: E402

from soni.dataset import DatasetBuilder, print_dataset_stats, validate_dataset  # noqa: E402
from soni.du.metrics import create_granular_metric  # noqa: E402
from soni.du.optimizer import optimize_du  # noqa: E402


def load_environment() -> bool:
    """Load environment variables from .env file.

    Returns:
        True if API key is available, False otherwise.
    """
    print("\n[1/5] Loading environment variables...")
    try:
        from dotenv import load_dotenv

        project_root = Path(__file__).parent.parent
        env_path = project_root / ".env"

        if env_path.exists():
            load_dotenv(env_path)
            print(f"      Loaded .env from {env_path}")
        else:
            load_dotenv()
            print("      No .env file found, using system environment")
    except ImportError:
        print("      python-dotenv not installed, using system environment only")

    if not os.getenv("OPENAI_API_KEY"):
        print("\n      Error: OPENAI_API_KEY not found")
        print("      Please either:")
        print("      1. Add OPENAI_API_KEY='your-key' to .env file")
        print("      2. Or export OPENAI_API_KEY='your-key' in your shell")
        return False

    print("      OPENAI_API_KEY found")
    return True


def save_dataset(examples: list[dspy.Example], output_path: Path) -> None:
    """Save dataset to JSON for reproducibility.

    Args:
        examples: List of dspy.Example instances
        output_path: Path to save dataset
    """
    dataset_dict = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "total_examples": len(examples),
        "examples": [],
    }

    for ex in examples:
        example_data = {
            "user_message": ex.user_message,
            "history": (
                ex.history.model_dump()
                if hasattr(ex.history, "model_dump")
                else {"messages": getattr(ex.history, "messages", [])}
            ),
            "context": ex.context.model_dump() if hasattr(ex.context, "model_dump") else ex.context,
            "result": ex.result.model_dump() if hasattr(ex.result, "model_dump") else ex.result,
        }
        dataset_dict["examples"].append(example_data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset_dict, f, indent=2, ensure_ascii=False)

    print(f"      Dataset saved to: {output_path}")


def stratified_split(
    examples: list[dspy.Example],
    train_ratio: float = 0.9,
    seed: int = 42,
) -> tuple[list[dspy.Example], list[dspy.Example]]:
    """Split dataset ensuring all command types are represented in both sets.

    Args:
        examples: Full dataset
        train_ratio: Ratio for training set (default: 0.9)
        seed: Random seed for reproducibility

    Returns:
        Tuple of (train_set, val_set)
    """
    random.seed(seed)

    # Group by first command type
    by_command_type: dict[str, list[dspy.Example]] = defaultdict(list)
    for ex in examples:
        if hasattr(ex.result, "commands") and ex.result.commands:
            cmd_type = ex.result.commands[0].__class__.__name__
        else:
            cmd_type = "empty"
        by_command_type[cmd_type].append(ex)

    train_split: list[dspy.Example] = []
    val_split: list[dspy.Example] = []

    print("\n      Stratified split:")
    for cmd_type, cmd_examples in sorted(by_command_type.items()):
        random.shuffle(cmd_examples)
        split_idx = int(len(cmd_examples) * train_ratio)

        # Ensure at least 2 in val if possible for representation
        min_val = (
            min(2, len(cmd_examples) - 1)
            if len(cmd_examples) > 2
            else (1 if len(cmd_examples) > 1 else 0)
        )
        if len(cmd_examples) - split_idx < min_val:
            split_idx = len(cmd_examples) - min_val

        train_split.extend(cmd_examples[:split_idx])
        val_split.extend(cmd_examples[split_idx:])
        print(f"        {cmd_type}: {split_idx} train, {len(cmd_examples) - split_idx} val")

    # Final shuffle
    random.shuffle(train_split)
    random.shuffle(val_split)

    return train_split, val_split


def create_readme(
    path: Path,
    metrics: dict,
    dataset_size: int,
    auto_setting: str,
) -> None:
    """Create README documenting the baseline optimization.

    Args:
        path: Path to README file
        metrics: Optimization metrics
        dataset_size: Number of training examples
        auto_setting: MIPROv2 auto setting used
    """
    readme_content = f"""# Soni Framework - Pre-trained NLU Models

This directory contains pre-trained NLU modules that ship with the Soni framework.

## Baseline v1

**File:** `baseline_v1.json`
**Created:** {datetime.now().strftime("%Y-%m-%d")}
**Training examples:** {dataset_size}

### Optimization Metrics

- **Baseline accuracy:** {metrics.get("baseline_accuracy", "N/A")}
- **Optimized accuracy:** {metrics.get("optimized_accuracy", "N/A")}
- **Optimizer:** MIPROv2 (auto={auto_setting})
- **Training time:** {metrics.get("total_time", "N/A")}s

### Dataset Coverage

The baseline optimization covers:
- **8 conversational patterns**: SLOT_VALUE, CORRECTION, MODIFICATION, INTERRUPTION,
  DIGRESSION, CLARIFICATION, CANCELLATION, CONFIRMATION
- **5 business domains**: flight_booking, hotel_booking, restaurant, ecommerce, banking
- **2 conversation contexts**: cold_start (no history), ongoing (with history)

### Usage

This module is automatically loaded by `CommandGenerator()` if available:

```python
from soni.du import CommandGenerator

# Default - uses baseline if available
nlu = CommandGenerator()
```

To use a custom optimization:

```python
nlu = CommandGenerator()
nlu.load("path/to/custom_optimized.json")
```

### Regenerating Baseline

To regenerate the baseline optimization:

```bash
uv run python scripts/generate_baseline_optimization.py
```

**Note:** Requires `OPENAI_API_KEY` environment variable.

## Version History

### v1 ({datetime.now().strftime("%Y-%m-%d")})
- Initial baseline optimization
- {dataset_size} training examples
"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(readme_content)

    print(f"      README created: {path}")


def main(
    auto: str = "medium", examples_per_combination: int = 5, optimizer: str = "miprov2"
) -> int:
    """Generate baseline optimization.

    Args:
        auto: Optimization intensity ("light", "medium", "heavy")
        examples_per_combination: Examples per (pattern x domain x context), default 5
        optimizer: Optimization algorithm ("miprov2", "gepa")

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("=" * 70)
    print("Soni Framework - Baseline NLU Optimization Generator")
    print("=" * 70)

    # Step 1: Load environment
    if not load_environment():
        return 1

    # Step 2: Generate dataset
    print("\n[2/5] Generating training dataset...")
    builder = DatasetBuilder()

    stats = builder.get_stats()
    print(f"      Patterns available: {stats['patterns']}")
    print(f"      Domains available: {stats['domains']}")
    print(f"      Contexts: {stats['contexts']}")
    print(f"      Max combinations: {stats['max_combinations']}")

    trainset = builder.build_all(
        examples_per_combination=examples_per_combination,
        include_edge_cases=True,
    )
    print(f"\n      Generated {len(trainset)} training examples")

    # Validate dataset
    print("\n      Validating dataset...")
    try:
        validate_dataset(trainset)
        print("      Dataset validated successfully")
    except ValueError as e:
        print(f"      Warning: {e}")

    # Print stats
    print_dataset_stats(trainset)

    # Save full dataset
    dataset_dir = Path("src/soni/du/datasets")
    dataset_path = dataset_dir / "baseline_v1.json"
    save_dataset(trainset, dataset_path)

    # Step 3: Split dataset
    print("\n[3/5] Splitting dataset...")
    train_split, val_split = stratified_split(trainset, train_ratio=0.9)
    print(f"\n      Training set: {len(train_split)} examples")
    print(f"      Validation set: {len(val_split)} examples")

    # Step 4: Configure DSPy and optimize
    print("\n[4/5] Configuring DSPy and running optimization...")
    print("      Model: openai/gpt-4o-mini")
    print(f"      Optimizer: {optimizer.upper()}")
    print(f"      Auto setting: {auto}")
    print("      This may take several minutes...")

    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)

    # Configure teacher/reflection model
    if optimizer == "gepa":
        print("      Using openai/gpt-4o for reflection (GEPA)")
        # Higher temperature for creative reflection
        teacher_model = dspy.LM("openai/gpt-4o", temperature=0.7)
    else:
        teacher_model = lm

    metric = create_granular_metric()  # Granular scoring with partial credit

    start_time = time.time()

    try:
        optimized = optimize_du(
            trainset=train_split,
            valset=val_split,
            metric=metric,
            auto=auto,
            optimizer_type=optimizer,
            teacher_model=teacher_model,
        )

        total_time = time.time() - start_time

        # Step 4b: Optimize Slot Extractor
        generate_and_optimize_slots(
            auto=auto,
            output_dir=Path("src/soni/du/optimized"),
            optimizer=optimizer,
            teacher_model=teacher_model,
        )

        # Step 5: Save results
        print("\n[5/5] Saving optimized module...")
        output_dir = Path("src/soni/du/optimized")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"baseline_v1_{optimizer}.json"
        optimized.save(str(output_path))
        print(f"      Optimized module saved to: {output_path}")

        # Save metrics
        metrics = {
            "baseline_accuracy": "N/A",  # Would need evaluation to compute
            "optimized_accuracy": "N/A",
            "optimizer": optimizer,
            "auto_setting": auto,
            "total_time": round(total_time, 1),
            "train_examples": len(train_split),
            "val_examples": len(val_split),
            "created_at": datetime.now().isoformat(),
        }

        metrics_path = output_dir / "baseline_v1_metrics.json"
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"      Metrics saved to: {metrics_path}")

        # Create README
        create_readme(output_dir / "README.md", metrics, len(trainset), auto)

        print("\n" + "=" * 70)
        print("Optimization Complete!")
        print("=" * 70)
        print(f"\n  Total time: {total_time:.1f}s")
        print(f"  Output: {output_path}")
        print("\n  Next steps:")
        print("    1. Test the optimized module")
        print("    2. Commit to repository")
        print("    3. Users will get this baseline automatically")

        return 0

    except Exception as e:
        print(f"\n      Optimization failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


def generate_and_optimize_slots(
    auto: str,
    output_dir: Path,
    optimizer: str,
    teacher_model: dspy.LM,
) -> None:
    """Run SlotExtractor optimization pipeline."""
    from soni.dataset.domains import ALL_DOMAINS
    from soni.dataset.slot_extraction import SlotExtractionDatasetBuilder
    from soni.du.metrics import create_slot_extraction_metric
    from soni.du.optimizer import optimize_slot_extractor

    print("\n[6/5] Optimizing SlotExtractor...")

    # 1. Generate Datasets
    builder = SlotExtractionDatasetBuilder()
    all_examples = []

    print("      Generating slot extraction examples...")
    for domain_name, domain_config in ALL_DOMAINS.items():
        templates = builder.build(domain_config)
        examples = [t.to_dspy_example() for t in templates]
        all_examples.extend(examples)
        print(f"        {domain_name}: {len(examples)} examples")

    print(f"      Total slot examples: {len(all_examples)}")

    if not all_examples:
        print("      No slot examples generated. Skipping slot optimization.")
        return

    # 2. Split (Simple random split as stratified is harder with slots)
    random.shuffle(all_examples)
    split_idx = int(len(all_examples) * 0.9)
    train_split = all_examples[:split_idx]
    val_split = all_examples[split_idx:]

    print(f"      Training set: {len(train_split)}")
    print(f"      Validation set: {len(val_split)}")

    # 3. Optimize
    # Use "light" auto setting by default for extraction as it's simpler
    # unless heavy is requested
    slot_auto = "light" if auto == "light" else "medium"

    print(f"      Optimizing with {optimizer.upper()} (auto={slot_auto})...")

    try:
        optimized = optimize_slot_extractor(
            trainset=train_split,
            valset=val_split,
            metric=create_slot_extraction_metric(),
            auto=slot_auto,
            optimizer_type=optimizer,
            teacher_model=teacher_model,
        )

        # 4. Save
        output_path = output_dir / f"baseline_v1_slots_{optimizer}.json"
        # SlotExtractor needs save method to be explicit? It inherits from dspy.Module so save() works.
        optimized.save(str(output_path))
        print(f"      Optimized SlotExtractor saved to: {output_path}")

        # Save dataset too
        dataset_path = Path("src/soni/du/datasets/baseline_v1_slots.json")
        save_dataset(all_examples, dataset_path)

    except Exception as e:
        print(f"      Slot optimization failed: {e}")
        # Don't fail the whole script for this optional component


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate baseline NLU optimization for Soni framework"
    )
    parser.add_argument(
        "--auto",
        type=str,
        choices=["light", "medium", "heavy"],
        default="medium",
        help="MIPROv2 auto setting (default: medium)",
    )
    parser.add_argument(
        "--examples",
        type=int,
        default=5,
        help="Examples per combination (default: 5)",
    )
    parser.add_argument(
        "--optimizer",
        type=str.lower,
        choices=["miprov2", "gepa"],
        default="miprov2",
        help="Optimization algorithm (default: miprov2)",
    )
    args = parser.parse_args()

    sys.exit(main(auto=args.auto, examples_per_combination=args.examples, optimizer=args.optimizer))
