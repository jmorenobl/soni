"""Example script to generate complete training dataset."""

from soni.dataset import DatasetBuilder, print_dataset_stats


def main():
    """Generate complete training dataset."""
    # Create builder with all patterns and domains
    builder = DatasetBuilder()

    # Show stats
    stats = builder.get_stats()
    print(f"Loaded {stats['patterns']} patterns, {stats['domains']} domains")
    print(f"Max combinations: {stats['max_combinations']}")

    # Build complete dataset
    print("\nGenerating dataset...")
    trainset = builder.build_all(examples_per_combination=2)

    # Validate and print stats
    print_dataset_stats(trainset)

    print(f"\n✅ Generated {len(trainset)} examples successfully!")

    return trainset


if __name__ == "__main__":
    trainset = main()
