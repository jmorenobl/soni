#!/usr/bin/env python3
"""Quick baseline optimization using BootstrapFewShot with stratified pattern coverage."""

import logging
import sys
from collections import defaultdict
from pathlib import Path

import dspy
from dspy.teleprompt import BootstrapFewShot
from soni.dataset import DatasetBuilder
from soni.du.metrics import intent_accuracy_metric
from soni.du.modules import SoniDU

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def stratify_by_pattern(
    trainset: list[dspy.Example], examples_per_pattern: int = 3
) -> list[dspy.Example]:
    """Select examples ensuring all patterns are represented.

    Args:
        trainset: Full training dataset
        examples_per_pattern: Number of examples to select per pattern

    Returns:
        Stratified subset with guaranteed pattern coverage
    """
    # Group examples by pattern
    by_pattern = defaultdict(list)
    for ex in trainset:
        if hasattr(ex, "result") and hasattr(ex.result, "message_type"):
            pattern = str(ex.result.message_type)
            by_pattern[pattern].append(ex)

    # Select N examples from each pattern
    stratified = []
    for pattern, examples in by_pattern.items():
        selected = examples[:examples_per_pattern]
        stratified.extend(selected)
        logger.info(f"  Pattern {pattern}: selected {len(selected)} of {len(examples)}")

    logger.info(f"Total stratified examples: {len(stratified)}")
    return stratified


def main():
    print("🚀 Starting quick optimization with stratified pattern coverage...")

    # helper to load env
    from dotenv import load_dotenv

    load_dotenv()

    # Configure LM
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)

    # Build dataset
    print("📊 Building training dataset...")
    builder = DatasetBuilder()
    full_trainset = builder.build_all(examples_per_combination=5)
    print(f"   Generated {len(full_trainset)} total training examples")

    # Stratify by pattern to ensure all patterns are represented
    print("🎯 Stratifying by pattern...")
    trainset = stratify_by_pattern(full_trainset, examples_per_pattern=4)

    # Create module
    student = SoniDU(load_baseline=False)

    # Configure optimizer with more demos
    print("⚙️  Configuring BootstrapFewShot...")
    teleprompter = BootstrapFewShot(
        metric=intent_accuracy_metric,
        max_bootstrapped_demos=30,  # Higher to ensure coverage
        max_labeled_demos=30,
    )

    # Optimize
    print("Running optimization...")
    optimized_student = teleprompter.compile(student, trainset=trainset)

    # Save
    output_dir = Path("src/soni/du/optimized")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "baseline_v1.json"

    optimized_student.save(str(output_path))
    print(f"✅ Optimized module saved to: {output_path}")


if __name__ == "__main__":
    main()
