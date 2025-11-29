#!/usr/bin/env python3
"""Benchmark script for Soni Framework performance"""

import asyncio
import json
import statistics
import time
from pathlib import Path

from soni.runtime import RuntimeLoop


async def benchmark_latency(runtime: RuntimeLoop, num_requests: int = 10) -> dict[str, float]:
    """Benchmark latency metrics"""
    print(f"Benchmarking latency with {num_requests} requests...")
    latencies = []

    for i in range(num_requests):
        start_time = time.time()
        await runtime.process_message(
            user_msg="I want to book a flight",
            user_id=f"benchmark-latency-{i}",
        )
        elapsed = time.time() - start_time
        latencies.append(elapsed)
        print(f"  Request {i + 1}/{num_requests}: {elapsed:.3f}s")

    latencies_sorted = sorted(latencies)
    p95_index = int(0.95 * len(latencies_sorted))
    p99_index = int(0.99 * len(latencies_sorted))

    return {
        "mean": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "p95": latencies_sorted[p95_index]
        if p95_index < len(latencies_sorted)
        else latencies_sorted[-1],
        "p99": latencies_sorted[p99_index]
        if p99_index < len(latencies_sorted)
        else latencies_sorted[-1],
    }


async def benchmark_throughput(runtime: RuntimeLoop, num_concurrent: int = 10) -> dict[str, float]:
    """Benchmark throughput"""
    print(f"Benchmarking throughput with {num_concurrent} concurrent requests...")

    async def process_message(user_id: str) -> float:
        start_time = time.time()
        await runtime.process_message(
            user_msg="Hello",
            user_id=user_id,
        )
        return time.time() - start_time

    start_time = time.time()
    tasks = [process_message(f"benchmark-throughput-{i}") for i in range(num_concurrent)]
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time

    throughput = num_concurrent / total_time

    return {
        "throughput_msg_per_sec": throughput,
        "total_time": total_time,
        "avg_latency": statistics.mean(results),
    }


async def benchmark_streaming(runtime: RuntimeLoop, num_requests: int = 5) -> dict[str, float]:
    """Benchmark streaming first token latency"""
    print(f"Benchmarking streaming with {num_requests} requests...")
    first_token_latencies = []

    for i in range(num_requests):
        start_time = time.time()
        first_token = None
        async for token in runtime.process_message_stream(
            user_msg="I want to book a flight",
            user_id=f"benchmark-streaming-{i}",
        ):
            if first_token is None:
                first_token = token
                first_token_latency = time.time() - start_time
                first_token_latencies.append(first_token_latency)
                break
        print(f"  Request {i + 1}/{num_requests}: {first_token_latency:.3f}s")

    return {
        "mean_first_token_latency": statistics.mean(first_token_latencies),
        "median_first_token_latency": statistics.median(first_token_latencies),
        "min_first_token_latency": min(first_token_latencies),
        "max_first_token_latency": max(first_token_latencies),
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
        print(f"Latency (p95): {results['latency']['p95']:.3f}s")
        print(f"Throughput: {results['throughput']['throughput_msg_per_sec']:.2f} msg/s")
        print(
            f"First Token Latency (mean): {results['streaming']['mean_first_token_latency']:.3f}s"
        )

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
