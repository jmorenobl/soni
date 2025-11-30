#!/usr/bin/env python3
"""Comprehensive E2E benchmark for Soni Framework v0.5.0"""

import asyncio
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

import dspy

try:
    from dotenv import load_dotenv

    # Load .env file if it exists
    load_dotenv()
except ImportError:
    pass  # dotenv not available, skip loading

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore

from soni.runtime import RuntimeLoop

# Configure DSPy with OpenAI LM if API key is available
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
    dspy.configure(lm=lm)
    print("✅ DSPy configured with OpenAI LM (gpt-4o-mini)")
else:
    print("⚠️  OPENAI_API_KEY not found - benchmarks may fail")

# Complete conversation flows for E2E testing
# Messages are more explicit to improve slot extraction success rate
CONVERSATION_FLOWS = [
    # Flow 1: Explicit booking request with all details
    [
        "I want to book a flight from Madrid to Barcelona on March 15th, 2024",
        # Fallback messages if first message doesn't extract all slots
        "The origin city is Madrid",
        "The destination is Barcelona",
        "The departure date is March 15th, 2024",
    ],
    # Flow 2: Booking with different cities, more explicit
    [
        "I need to book a flight from Paris to London on April 20th, 2024",
        "Origin: Paris",
        "Destination: London",
        "Date: April 20th, 2024",
    ],
    # Flow 3: Another booking with explicit format
    [
        "Book a flight from New York to Los Angeles on May 10th, 2024",
        "My origin is New York",
        "My destination is Los Angeles",
        "I want to depart on May 10th, 2024",
    ],
    # Flow 4: Step-by-step with very explicit messages
    [
        "I want to book a flight",
        "I am departing from Madrid",
        "I want to go to Barcelona",
        "I want to travel on March 15th, 2024",
    ],
]


async def run_conversation_flow(
    runtime: RuntimeLoop,
    user_id: str,
    messages: list[str],
) -> tuple[float, list[float], bool, str | None]:
    """
    Run a complete conversation flow and measure latency with error handling.

    Args:
        runtime: RuntimeLoop instance
        user_id: Unique user identifier
        messages: List of messages in the conversation

    Returns:
        Tuple of (total_latency, per_message_latencies, success, error_message)
    """
    from soni.core.errors import NLUError, SoniError, ValidationError

    total_start = time.time()
    per_message_latencies = []
    success = True
    error_message = None

    for i, message in enumerate(messages):
        msg_start = time.time()
        try:
            await runtime.process_message(user_msg=message, user_id=user_id)
            msg_latency = time.time() - msg_start
            per_message_latencies.append(msg_latency)
        except (ValueError, SoniError, ValidationError, NLUError) as e:
            # Expected errors (missing slots, validation errors, etc.)
            msg_latency = time.time() - msg_start
            per_message_latencies.append(msg_latency)
            success = False
            error_message = (
                f"Message {i + 1} ({message[:30]}...): {type(e).__name__}: {str(e)[:100]}"
            )
            # Continue to measure total latency even after failure
        except Exception as e:
            # Unexpected errors
            msg_latency = time.time() - msg_start
            per_message_latencies.append(msg_latency)
            success = False
            error_message = f"Message {i + 1} ({message[:30]}...): Unexpected {type(e).__name__}: {str(e)[:100]}"
            # Log but continue

    total_latency = time.time() - total_start
    return total_latency, per_message_latencies, success, error_message


async def benchmark_e2e_latency(
    runtime: RuntimeLoop,
    num_conversations: int = 100,
) -> dict[str, Any]:
    """
    Benchmark end-to-end latency for complete conversations with success/failure tracking.

    Args:
        runtime: RuntimeLoop instance
        num_conversations: Number of conversations to run

    Returns:
        Dictionary with latency metrics including success/failure rates
    """
    print(f"Benchmarking E2E latency with {num_conversations} conversations...")
    total_latencies = []
    successful_latencies = []
    failed_latencies = []
    per_message_latencies = []
    success_count = 0
    failure_count = 0
    error_types: dict[str, int] = {}

    for i in range(num_conversations):
        # Cycle through conversation flows
        flow = CONVERSATION_FLOWS[i % len(CONVERSATION_FLOWS)]
        user_id = f"benchmark-e2e-{i}"

        total_latency, msg_latencies, success, error_msg = await run_conversation_flow(
            runtime,
            user_id,
            flow,
        )
        total_latencies.append(total_latency)
        per_message_latencies.extend(msg_latencies)

        if success:
            successful_latencies.append(total_latency)
            success_count += 1
        else:
            failed_latencies.append(total_latency)
            failure_count += 1
            # Extract error type from error message
            if error_msg:
                error_type = error_msg.split(":")[0] if ":" in error_msg else "Unknown"
                error_types[error_type] = error_types.get(error_type, 0) + 1

        if (i + 1) % 10 == 0:
            success_rate = (success_count / (i + 1)) * 100
            print(
                f"  Completed {i + 1}/{num_conversations} conversations "
                f"(Success: {success_count}, Failed: {failure_count}, "
                f"Rate: {success_rate:.1f}%)"
            )

    # Calculate percentiles
    def percentile(data: list[float], p: float) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(p * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    total_sorted = sorted(total_latencies)
    msg_sorted = sorted(per_message_latencies)
    successful_sorted = sorted(successful_latencies) if successful_latencies else []
    failed_sorted = sorted(failed_latencies) if failed_latencies else []

    return {
        "total_conversations": num_conversations,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": (success_count / num_conversations * 100) if num_conversations > 0 else 0.0,
        "error_types": error_types,
        "total_latency": {
            "all": {
                "mean": statistics.mean(total_latencies) if total_latencies else 0.0,
                "median": statistics.median(total_latencies) if total_latencies else 0.0,
                "min": min(total_latencies) if total_latencies else 0.0,
                "max": max(total_latencies) if total_latencies else 0.0,
                "p50": percentile(total_sorted, 0.50),
                "p95": percentile(total_sorted, 0.95),
                "p99": percentile(total_sorted, 0.99),
            },
            "successful": {
                "mean": statistics.mean(successful_latencies) if successful_latencies else 0.0,
                "median": statistics.median(successful_latencies) if successful_latencies else 0.0,
                "min": min(successful_latencies) if successful_latencies else 0.0,
                "max": max(successful_latencies) if successful_latencies else 0.0,
                "p50": percentile(successful_sorted, 0.50),
                "p95": percentile(successful_sorted, 0.95),
                "p99": percentile(successful_sorted, 0.99),
            },
            "failed": {
                "mean": statistics.mean(failed_latencies) if failed_latencies else 0.0,
                "median": statistics.median(failed_latencies) if failed_latencies else 0.0,
                "min": min(failed_latencies) if failed_latencies else 0.0,
                "max": max(failed_latencies) if failed_latencies else 0.0,
                "p50": percentile(failed_sorted, 0.50),
                "p95": percentile(failed_sorted, 0.95),
                "p99": percentile(failed_sorted, 0.99),
            },
        },
        "per_message_latency": {
            "mean": statistics.mean(msg_latencies) if msg_latencies else 0.0,
            "median": statistics.median(msg_latencies) if msg_latencies else 0.0,
            "min": min(msg_latencies) if msg_latencies else 0.0,
            "max": max(msg_latencies) if msg_latencies else 0.0,
            "p50": percentile(msg_sorted, 0.50),
            "p95": percentile(msg_sorted, 0.95),
            "p99": percentile(msg_sorted, 0.99),
        },
    }


async def benchmark_e2e_throughput(
    runtime: RuntimeLoop,
    num_concurrent: int = 10,
    conversations_per_user: int = 1,
) -> dict[str, Any]:
    """
    Benchmark end-to-end throughput with concurrent users.

    Args:
        runtime: RuntimeLoop instance
        num_concurrent: Number of concurrent users
        conversations_per_user: Number of conversations per user

    Returns:
        Dictionary with throughput metrics
    """
    print(
        f"Benchmarking E2E throughput with {num_concurrent} concurrent users "
        f"({conversations_per_user} conversations each)..."
    )

    async def process_user_conversations(user_id: str) -> tuple[int, float, int]:
        """Process conversations for a single user."""
        total_messages = 0
        successful_conversations = 0
        start_time = time.time()

        for i in range(conversations_per_user):
            flow = CONVERSATION_FLOWS[i % len(CONVERSATION_FLOWS)]
            _, _, success, _ = await run_conversation_flow(runtime, f"{user_id}-{i}", flow)
            total_messages += len(flow)
            if success:
                successful_conversations += 1

        elapsed = time.time() - start_time
        return total_messages, elapsed, successful_conversations

    start_time = time.time()
    tasks = [process_user_conversations(f"throughput-user-{i}") for i in range(num_concurrent)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_time = time.time() - start_time

    # Filter out exceptions
    successful_results = [
        r for r in results if not isinstance(r, Exception) and isinstance(r, tuple) and len(r) == 3
    ]

    total_messages = sum(msg for msg, _, _ in successful_results)
    total_conversations = len(successful_results) * conversations_per_user
    successful_conversations = sum(success for _, _, success in successful_results)

    throughput_conv_per_sec = total_conversations / total_time if total_time > 0 else 0.0
    throughput_msg_per_sec = total_messages / total_time if total_time > 0 else 0.0
    success_rate = (
        (successful_conversations / total_conversations * 100) if total_conversations > 0 else 0.0
    )

    return {
        "num_concurrent_users": num_concurrent,
        "conversations_per_user": conversations_per_user,
        "total_conversations": total_conversations,
        "successful_conversations": successful_conversations,
        "failed_conversations": total_conversations - successful_conversations,
        "success_rate": success_rate,
        "total_messages": total_messages,
        "total_time": total_time,
        "throughput_conv_per_sec": throughput_conv_per_sec,
        "throughput_msg_per_sec": throughput_msg_per_sec,
        "successful_users": len(successful_results),
        "failed_users": num_concurrent - len(successful_results),
    }


def get_memory_usage() -> dict[str, float]:
    """
    Get current memory usage.

    Returns:
        Dictionary with memory metrics in MB
    """
    if psutil is None:
        return {"error": "psutil not available"}

    process = psutil.Process()
    memory_info = process.memory_info()

    return {
        "rss_mb": memory_info.rss / (1024 * 1024),  # Resident Set Size
        "vms_mb": memory_info.vms / (1024 * 1024),  # Virtual Memory Size
    }


def get_cpu_usage(duration: float = 1.0) -> dict[str, float]:
    """
    Get CPU usage over a duration.

    Args:
        duration: Duration to measure CPU usage (seconds)

    Returns:
        Dictionary with CPU metrics
    """
    if psutil is None:
        return {"error": "psutil not available"}

    process = psutil.Process()
    cpu_percent = process.cpu_percent(interval=duration)

    return {
        "cpu_percent": cpu_percent,
        "num_threads": process.num_threads(),
    }


async def benchmark_memory_usage(
    runtime: RuntimeLoop,
    num_conversations: int = 50,
) -> dict[str, Any]:
    """
    Benchmark memory usage during conversations.

    Args:
        runtime: RuntimeLoop instance
        num_conversations: Number of conversations to run

    Returns:
        Dictionary with memory metrics
    """
    if psutil is None:
        return {"error": "psutil not available"}

    print(f"Benchmarking memory usage with {num_conversations} conversations...")

    # Initial memory
    initial_memory = get_memory_usage()

    # Run conversations
    for i in range(num_conversations):
        flow = CONVERSATION_FLOWS[i % len(CONVERSATION_FLOWS)]
        user_id = f"memory-benchmark-{i}"
        _, _, _, _ = await run_conversation_flow(runtime, user_id, flow)

        if (i + 1) % 10 == 0:
            current_memory = get_memory_usage()
            print(f"  After {i + 1} conversations: RSS={current_memory.get('rss_mb', 0):.1f}MB")

    # Final memory
    final_memory = get_memory_usage()

    return {
        "initial_memory_mb": initial_memory.get("rss_mb", 0.0),
        "final_memory_mb": final_memory.get("rss_mb", 0.0),
        "memory_increase_mb": final_memory.get("rss_mb", 0.0) - initial_memory.get("rss_mb", 0.0),
        "num_conversations": num_conversations,
    }


async def benchmark_cpu_usage(
    runtime: RuntimeLoop,
    num_conversations: int = 50,
) -> dict[str, Any]:
    """
    Benchmark CPU usage during conversations.

    Args:
        runtime: RuntimeLoop instance
        num_conversations: Number of conversations to run

    Returns:
        Dictionary with CPU metrics
    """
    if psutil is None:
        return {"error": "psutil not available"}

    print(f"Benchmarking CPU usage with {num_conversations} conversations...")

    cpu_samples = []

    # Run conversations and sample CPU
    for i in range(num_conversations):
        flow = CONVERSATION_FLOWS[i % len(CONVERSATION_FLOWS)]
        user_id = f"cpu-benchmark-{i}"

        # Measure CPU during conversation
        cpu_before = get_cpu_usage(0.1)
        _, _, _, _ = await run_conversation_flow(runtime, user_id, flow)
        cpu_after = get_cpu_usage(0.1)

        cpu_samples.append(
            {
                "before": cpu_before.get("cpu_percent", 0.0),
                "after": cpu_after.get("cpu_percent", 0.0),
            }
        )

        if (i + 1) % 10 == 0:
            print(f"  Completed {i + 1}/{num_conversations} conversations")

    cpu_percentages = [s["after"] for s in cpu_samples]

    return {
        "num_conversations": num_conversations,
        "cpu_percent": {
            "mean": statistics.mean(cpu_percentages) if cpu_percentages else 0.0,
            "median": statistics.median(cpu_percentages) if cpu_percentages else 0.0,
            "min": min(cpu_percentages) if cpu_percentages else 0.0,
            "max": max(cpu_percentages) if cpu_percentages else 0.0,
        },
        "num_threads": cpu_samples[0].get("after", {}).get("num_threads", 0) if cpu_samples else 0,
    }


async def main() -> None:
    """Run all E2E benchmarks."""
    print("=" * 70)
    print("Soni Framework E2E Performance Benchmark - v0.5.0")
    print("=" * 70)

    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)

    try:
        results: dict[str, Any] = {
            "version": "0.5.0",
            "timestamp": time.time(),
        }

        # E2E Latency benchmark (reduced for faster testing)
        print("\n" + "-" * 70)
        results["e2e_latency"] = await benchmark_e2e_latency(
            runtime,
            num_conversations=20,  # Reduced from 100 for faster execution
        )

        # E2E Throughput benchmark
        print("\n" + "-" * 70)
        results["e2e_throughput"] = await benchmark_e2e_throughput(
            runtime, num_concurrent=10, conversations_per_user=1
        )

        # Memory usage benchmark (reduced for faster testing)
        if psutil:
            print("\n" + "-" * 70)
            results["memory_usage"] = await benchmark_memory_usage(
                runtime,
                num_conversations=10,  # Reduced from 50 for faster execution
            )

        # CPU usage benchmark (reduced for faster testing)
        if psutil:
            print("\n" + "-" * 70)
            results["cpu_usage"] = await benchmark_cpu_usage(
                runtime,
                num_conversations=10,  # Reduced from 50 for faster execution
            )

        # Print summary
        print("\n" + "=" * 70)
        print("E2E Benchmark Results Summary")
        print("=" * 70)

        if "e2e_latency" in results:
            latency_data = results["e2e_latency"]
            latency = latency_data["total_latency"]
            print("\nLatency (Total Conversation):")
            print(f"  Success Rate: {latency_data['success_rate']:.1f}%")
            print(
                f"  Successful: {latency_data['success_count']}/{latency_data['total_conversations']}"
            )
            print(
                f"  Failed: {latency_data['failure_count']}/{latency_data['total_conversations']}"
            )
            if latency_data.get("error_types"):
                print(f"  Error Types: {latency_data['error_types']}")
            print("\n  All Conversations:")
            print(f"    p50: {latency['all']['p50']:.3f}s")
            print(f"    p95: {latency['all']['p95']:.3f}s")
            print(f"    p99: {latency['all']['p99']:.3f}s")
            print(f"    Mean: {latency['all']['mean']:.3f}s")
            if latency_data["success_count"] > 0:
                print("\n  Successful Conversations:")
                print(f"    p50: {latency['successful']['p50']:.3f}s")
                print(f"    p95: {latency['successful']['p95']:.3f}s")
                print(f"    p99: {latency['successful']['p99']:.3f}s")
                print(f"    Mean: {latency['successful']['mean']:.3f}s")
            if latency_data["failure_count"] > 0:
                print("\n  Failed Conversations:")
                print(f"    p50: {latency['failed']['p50']:.3f}s")
                print(f"    p95: {latency['failed']['p95']:.3f}s")
                print(f"    Mean: {latency['failed']['mean']:.3f}s")

        if "e2e_throughput" in results:
            throughput = results["e2e_throughput"]
            print("\nThroughput:")
            print(f"  Success Rate: {throughput['success_rate']:.1f}%")
            print(
                f"  Successful: {throughput['successful_conversations']}/{throughput['total_conversations']}"
            )
            print(f"  Conversations/sec: {throughput['throughput_conv_per_sec']:.2f}")
            print(f"  Messages/sec: {throughput['throughput_msg_per_sec']:.2f}")

        if "memory_usage" in results and "error" not in results["memory_usage"]:
            memory = results["memory_usage"]
            print("\nMemory Usage:")
            print(f"  Initial: {memory['initial_memory_mb']:.1f}MB")
            print(f"  Final: {memory['final_memory_mb']:.1f}MB")
            print(f"  Increase: {memory['memory_increase_mb']:.1f}MB")

        if "cpu_usage" in results and "error" not in results["cpu_usage"]:
            cpu = results["cpu_usage"]["cpu_percent"]
            print("\nCPU Usage:")
            print(f"  Mean: {cpu['mean']:.1f}%")
            print(f"  Max: {cpu['max']:.1f}%")

        # Save results
        results_file = Path("experiments/results/benchmark_e2e_v0.5.0.json")
        results_file.parent.mkdir(parents=True, exist_ok=True)
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {results_file}")

    finally:
        await runtime.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
