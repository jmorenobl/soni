"""Validate compilation success rate for v0.3.0 release."""

import asyncio
from pathlib import Path

from soni.compiler.builder import StepCompiler
from soni.compiler.parser import StepParser
from soni.core.config import SoniConfig


async def validate_compilation_success():
    """Validate compilation success rate >95%."""
    # List of valid YAML configs to test
    configs = [
        "examples/flight_booking/soni.yaml",
        "examples/advanced/retry_flow.yaml",
        "examples/advanced/branching_flow.yaml",
    ]

    success_count = 0
    total_count = 0

    for config_path in configs:
        config_file = Path(config_path)
        if not config_file.exists():
            print(f"⚠️  Config file not found: {config_path}, skipping")
            continue

        try:
            # Load config
            config = SoniConfig.from_yaml(str(config_file))

            # Test compilation for each flow
            parser = StepParser()
            compiler = StepCompiler(config=config)

            for flow_name, flow_config in config.flows.items():
                total_count += 1
                try:
                    # Check if flow has process section (new DSL) or steps (old DSL)
                    if hasattr(flow_config, "process") and flow_config.process:
                        # Parse steps
                        parsed_steps = parser.parse(flow_config.process)
                        # Compile to graph
                        compiler.compile(flow_name, parsed_steps)
                        success_count += 1
                        print(f"✅ Compiled flow '{flow_name}' from {config_path}")
                    elif hasattr(flow_config, "steps") and flow_config.steps:
                        # Old DSL format (backward compatible)
                        parsed_steps = parser.parse(flow_config.steps)
                        compiler.compile(flow_name, parsed_steps)
                        success_count += 1
                        print(f"✅ Compiled flow '{flow_name}' from {config_path} (old DSL)")
                    else:
                        print(f"⚠️  Flow '{flow_name}' has no steps or process, skipping")
                except Exception as e:
                    print(f"❌ Failed to compile flow '{flow_name}' from {config_path}: {e}")

        except Exception as e:
            print(f"❌ Failed to load config {config_path}: {e}")

    if total_count == 0:
        print("❌ No flows found to validate")
        return 1

    success_rate = (success_count / total_count) * 100
    print(f"\n📊 Compilation Success Rate: {success_rate:.1f}% ({success_count}/{total_count})")
    print("✅ Target: >95%")

    if success_rate >= 95:
        print("✅ PASSED: Compilation success rate meets target")
        return 0
    else:
        print("❌ FAILED: Compilation success rate below target")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(validate_compilation_success()))
