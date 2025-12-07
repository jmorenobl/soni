#!/usr/bin/env python3
"""Script to validate configuration system end-to-end"""

from pathlib import Path

from soni.core.config import ConfigLoader, SoniConfig


def main():
    """Validate configuration system"""
    print("🔍 Validating Soni Configuration System")
    print("=" * 60)

    # Path to example YAML
    yaml_path = Path("examples/flight_booking/soni.yaml")

    if not yaml_path.exists():
        print(f"❌ Example YAML not found: {yaml_path}")
        print("   Please ensure task 001 is completed")
        return 1

    print(f"\n1️⃣ Loading YAML: {yaml_path}")
    try:
        raw_config = ConfigLoader.load(yaml_path)
        print("   ✅ YAML loaded successfully")
        print(f"   - Version: {raw_config.get('version', 'N/A')}")
        print(f"   - Flows: {len(raw_config.get('flows', {}))}")
        print(f"   - Slots: {len(raw_config.get('slots', {}))}")
        print(f"   - Actions: {len(raw_config.get('actions', {}))}")
    except Exception as e:
        print(f"   ❌ Failed to load YAML: {e}")
        return 1

    print("\n2️⃣ Validating structure")
    try:
        errors = ConfigLoader.validate(raw_config)
        if errors:
            print(f"   ⚠️  Found {len(errors)} validation warnings:")
            for error in errors[:3]:  # Show first 3
                print(f"      - {error}")
        else:
            print("   ✅ No validation errors")
    except Exception as e:
        print(f"   ❌ Validation failed: {e}")
        return 1

    print("\n3️⃣ Loading with Pydantic models")
    try:
        config = SoniConfig.from_yaml(yaml_path)
        print("   ✅ Configuration loaded and validated with Pydantic")
        print(f"   - Version: {config.version}")
        print(f"   - NLU Provider: {config.settings.models.nlu.provider}")
        print(f"   - NLU Model: {config.settings.models.nlu.model}")
        print(f"   - Flows: {list(config.flows.keys())}")
        print(f"   - Slots: {list(config.slots.keys())}")
        print(f"   - Actions: {list(config.actions.keys())}")
    except Exception as e:
        print(f"   ❌ Failed to load with Pydantic: {e}")
        return 1

    print("\n4️⃣ Validating configuration access")
    try:
        # Test accessing nested configuration
        assert config.version == "0.1"
        assert config.settings.models.nlu.provider in ["openai", "anthropic"]
        assert len(config.flows) > 0

        # Test accessing flow steps
        first_flow_name = list(config.flows.keys())[0]
        first_flow = config.flows[first_flow_name]
        assert len(first_flow.steps) > 0
        print("   ✅ Configuration structure is accessible")
        print(f"   - First flow: {first_flow_name} ({len(first_flow.steps)} steps)")
    except Exception as e:
        print(f"   ❌ Configuration access failed: {e}")
        return 1

    print("\n" + "=" * 60)
    print("✅ Configuration system validation PASSED")
    return 0


if __name__ == "__main__":
    exit(main())
