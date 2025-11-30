#!/usr/bin/env python3
"""Benchmark script for Soni Framework performance"""

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

from soni.runtime import RuntimeLoop

# Configure DSPy with OpenAI LM if API key is available
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
    dspy.configure(lm=lm)
    print("✅ DSPy configured with OpenAI LM (gpt-4o-mini)")
else:
    print("⚠️  OPENAI_API_KEY not found - benchmarks may fail")


async def benchmark_latency(runtime: RuntimeLoop, num_requests: int = 10) -> dict[str, Any]:
    """Benchmark latency metrics with error handling"""
    from soni.core.errors import NLUError, SoniError, ValidationError

    print(f"Benchmarking latency with {num_requests} requests...")
    latencies = []
    successful_latencies = []
    failed_latencies = []
    success_count = 0
    failure_count = 0

    for i in range(num_requests):
        start_time = time.time()
        try:
            await runtime.process_message(
                user_msg="I want to book a flight from Madrid to Barcelona on March 15th, 2024",
                user_id=f"benchmark-latency-{i}",
            )
            elapsed = time.time() - start_time
            latencies.append(elapsed)
            successful_latencies.append(elapsed)
            success_count += 1
            print(f"  Request {i + 1}/{num_requests}: {elapsed:.3f}s ✓")
        except (ValueError, SoniError, ValidationError, NLUError) as e:
            # Expected errors - still measure latency
            elapsed = time.time() - start_time
            latencies.append(elapsed)
            failed_latencies.append(elapsed)
            failure_count += 1
            print(f"  Request {i + 1}/{num_requests}: {elapsed:.3f}s ✗ ({type(e).__name__})")
        except Exception as e:
            # Unexpected errors
            elapsed = time.time() - start_time
            latencies.append(elapsed)
            failed_latencies.append(elapsed)
            failure_count += 1
            print(
                f"  Request {i + 1}/{num_requests}: {elapsed:.3f}s ✗ (Unexpected: {type(e).__name__})"
            )

    latencies_sorted = sorted(latencies)
    p95_index = int(0.95 * len(latencies_sorted))
    p99_index = int(0.99 * len(latencies_sorted))

    return {
        "mean": statistics.mean(latencies) if latencies else 0.0,
        "median": statistics.median(latencies) if latencies else 0.0,
        "min": min(latencies) if latencies else 0.0,
        "max": max(latencies) if latencies else 0.0,
        "p95": latencies_sorted[p95_index]
        if p95_index < len(latencies_sorted)
        else latencies_sorted[-1]
        if latencies_sorted
        else 0.0,
        "p99": latencies_sorted[p99_index]
        if p99_index < len(latencies_sorted)
        else latencies_sorted[-1]
        if latencies_sorted
        else 0.0,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": (success_count / num_requests * 100) if num_requests > 0 else 0.0,
        "successful_latencies": {
            "mean": statistics.mean(successful_latencies) if successful_latencies else 0.0,
            "median": statistics.median(successful_latencies) if successful_latencies else 0.0,
        },
        "failed_latencies": {
            "mean": statistics.mean(failed_latencies) if failed_latencies else 0.0,
            "median": statistics.median(failed_latencies) if failed_latencies else 0.0,
        },
    }


async def benchmark_throughput(runtime: RuntimeLoop, num_concurrent: int = 10) -> dict[str, Any]:
    """Benchmark throughput with error handling"""
    from soni.core.errors import NLUError, SoniError, ValidationError

    print(f"Benchmarking throughput with {num_concurrent} concurrent requests...")

    async def process_message(user_id: str) -> tuple[float, bool]:
        start_time = time.time()
        try:
            await runtime.process_message(
                user_msg="I want to book a flight from Madrid to Barcelona on March 15th, 2024",
                user_id=user_id,
            )
            elapsed = time.time() - start_time
            return elapsed, True
        except (ValueError, SoniError, ValidationError, NLUError):
            # Expected errors - still measure latency
            elapsed = time.time() - start_time
            return elapsed, False
        except Exception:
            # Unexpected errors
            elapsed = time.time() - start_time
            return elapsed, False

    start_time = time.time()
    tasks = [process_message(f"benchmark-throughput-{i}") for i in range(num_concurrent)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time

    # Filter out exceptions and separate successful/failed
    successful_results = [
        r for r in results if not isinstance(r, Exception) and isinstance(r, tuple)
    ]
    latencies = [lat for lat, _ in successful_results]
    success_count = sum(1 for _, success in successful_results if success)
    failure_count = len(successful_results) - success_count

    throughput = len(successful_results) / total_time if total_time > 0 else 0.0

    return {
        "throughput_msg_per_sec": throughput,
        "total_time": total_time,
        "avg_latency": statistics.mean(latencies) if latencies else 0.0,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": (success_count / len(successful_results) * 100)
        if successful_results
        else 0.0,
    }


async def benchmark_streaming(runtime: RuntimeLoop, num_requests: int = 5) -> dict[str, Any]:
    """Benchmark streaming first token latency with error handling"""
    from soni.core.errors import NLUError, SoniError, ValidationError

    print(f"Benchmarking streaming with {num_requests} requests...")
    first_token_latencies = []
    success_count = 0
    failure_count = 0

    for i in range(num_requests):
        start_time = time.time()
        first_token = None
        first_token_latency = None
        try:
            async for token in runtime.process_message_stream(
                user_msg="I want to book a flight from Madrid to Barcelona on March 15th, 2024",
                user_id=f"benchmark-streaming-{i}",
            ):
                if first_token is None:
                    first_token = token
                    first_token_latency = time.time() - start_time
                    first_token_latencies.append(first_token_latency)
                    success_count += 1
                    break
            if first_token_latency is None:
                # Stream completed without tokens (unlikely but possible)
                first_token_latency = time.time() - start_time
                first_token_latencies.append(first_token_latency)
                failure_count += 1
            print(f"  Request {i + 1}/{num_requests}: {first_token_latency:.3f}s ✓")
        except (ValueError, SoniError, ValidationError, NLUError) as e:
            # Expected errors - measure latency to first error
            first_token_latency = time.time() - start_time
            first_token_latencies.append(first_token_latency)
            failure_count += 1
            print(
                f"  Request {i + 1}/{num_requests}: {first_token_latency:.3f}s ✗ ({type(e).__name__})"
            )
        except Exception:
            # Unexpected errors
            first_token_latency = time.time() - start_time
            first_token_latencies.append(first_token_latency)
            failure_count += 1
            print(f"  Request {i + 1}/{num_requests}: {first_token_latency:.3f}s ✗ (Unexpected)")

    return {
        "mean_first_token_latency": statistics.mean(first_token_latencies)
        if first_token_latencies
        else 0.0,
        "median_first_token_latency": statistics.median(first_token_latencies)
        if first_token_latencies
        else 0.0,
        "min_first_token_latency": min(first_token_latencies) if first_token_latencies else 0.0,
        "max_first_token_latency": max(first_token_latencies) if first_token_latencies else 0.0,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": (success_count / num_requests * 100) if num_requests > 0 else 0.0,
    }


async def main():
    """Run all benchmarks"""
    print("=" * 60)
    print("Soni Framework Performance Benchmark")
    print("=" * 60)

    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)

    try:
        results = {}

        # Latency benchmark
        results["latency"] = await benchmark_latency(runtime, num_requests=5)

        # Throughput benchmark
        results["throughput"] = await benchmark_throughput(runtime, num_concurrent=5)

        # Streaming benchmark
        results["streaming"] = await benchmark_streaming(runtime, num_requests=3)

        # Print summary
        print("\n" + "=" * 60)
        print("Benchmark Results Summary")
        print("=" * 60)
        if "latency" in results:
            latency = results["latency"]
            total_requests = latency["success_count"] + latency["failure_count"]
            print("\nLatency:")
            print(f"  p95: {latency['p95']:.3f}s")
            print(f"  Success Rate: {latency['success_rate']:.1f}%")
            print(f"  Successful: {latency['success_count']}/{total_requests}")
            if latency["successful_latencies"]["mean"] > 0:
                print(f"  Successful avg: {latency['successful_latencies']['mean']:.3f}s")
            if latency["failed_latencies"]["mean"] > 0:
                print(f"  Failed avg: {latency['failed_latencies']['mean']:.3f}s")
        if "throughput" in results:
            throughput = results["throughput"]
            print("\nThroughput:")
            print(f"  Messages/sec: {throughput['throughput_msg_per_sec']:.2f}")
            print(f"  Success Rate: {throughput['success_rate']:.1f}%")
        if "streaming" in results:
            streaming = results["streaming"]
            print("\nStreaming:")
            print(f"  First Token Latency (mean): {streaming['mean_first_token_latency']:.3f}s")
            print(f"  Success Rate: {streaming['success_rate']:.1f}%")

        # Save results
        results_file = Path("experiments/results/performance_benchmark_results.json")
        results_file.parent.mkdir(parents=True, exist_ok=True)
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {results_file}")

    finally:
        await runtime.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
