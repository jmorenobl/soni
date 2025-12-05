# Testing Guide

## Quick Start

```bash
# Run unit tests (fast, ~1 minute)
make test

# Run all tests (slow, ~5 minutes)
make test-all

# Run specific test categories
make test-integration   # Integration tests only
make test-performance   # Performance tests only
make test-ci           # Unit + Integration (for CI/CD)
```

## Test Organization

### 🚀 Unit Tests (512 tests)
- **Location**: `tests/unit/`
- **Speed**: Fast (~52 seconds)
- **Coverage**: 85%+
- **When**: Every commit, before pushing
- **Command**: `make test`

**Characteristics**:
- No external dependencies (LLM, network)
- Mocked dependencies
- Fast execution
- Deterministic results

### 🔗 Integration Tests (~32 tests)
- **Location**: `tests/integration/` + some streaming tests
- **Speed**: Moderate-Slow (depends on LLM API)
- **When**: Before merging PRs, nightly builds
- **Command**: `make test-integration`

**Characteristics**:
- Test component integration
- May use real LLM calls (requires `OPENAI_API_KEY`)
- Can be flaky due to LLM non-determinism
- Marked with `@pytest.mark.integration`

**Files**:
- `test_e2e.py` - End-to-end dialogue flows
- `test_output_mapping.py` - Action output mapping
- `test_conditional_compiler.py` - Conditional flow compilation
- `test_linear_compiler.py` - Linear flow compilation
- `test_scoping_integration.py` - Action scoping
- `test_dialogue_flow.py` - Complete dialogue flows
- `test_streaming_endpoint.py` - Streaming responses
- And more...

### ⚡ Performance Tests (~13 tests)
- **Location**: `tests/performance/`
- **Speed**: Slow (benchmarking)
- **When**: Before releases, performance investigations
- **Command**: `make test-performance`

**Characteristics**:
- Measure latency, throughput, memory, CPU
- Strict thresholds (may fail in different environments)
- Resource-intensive
- Marked with `@pytest.mark.performance`

**Files**:
- `test_e2e_performance.py` - E2E latency and throughput
- `test_streaming.py` - Streaming performance
- `test_throughput.py` - Concurrent throughput
- `test_latency.py` - Response latency

## Running Tests

### Command Reference

```bash
# Unit tests only (default, fast)
make test
# Equivalent to: pytest -m "not integration and not performance"

# All tests
make test-all
# Equivalent to: pytest

# Integration tests only
make test-integration
# Equivalent to: pytest -m integration

# Performance tests only
make test-performance
# Equivalent to: pytest -m performance

# Unit + Integration (no performance)
make test-ci
# Equivalent to: pytest -m "not performance"
```

### Direct pytest Usage

```bash
# Run specific test file
uv run pytest tests/unit/test_state.py

# Run specific test
uv run pytest tests/unit/test_state.py::test_create_empty_state

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov=soni --cov-report=html

# Run tests matching pattern
uv run pytest -k "state"

# Run failed tests only
uv run pytest --lf

# Stop on first failure
uv run pytest -x
```

## CI/CD Recommendations

### Fast Feedback (every commit)
```bash
make test
```
- ✅ Fast (~1 minute)
- ✅ 512 unit tests
- ✅ High coverage (85%+)
- ✅ Deterministic

### Pre-merge (Pull Requests)
```bash
make test-ci
```
- ✅ Comprehensive (unit + integration)
- ✅ Moderate speed (~3-5 minutes)
- ⚠️ Requires `OPENAI_API_KEY`
- ⚠️ May have flaky tests

### Nightly / Release
```bash
make test-all
```
- ✅ Complete coverage
- ⚠️ Slow (~5+ minutes)
- ⚠️ Performance tests may fail on resource-constrained systems

## Configuration

### Environment Variables

```bash
# Required for integration tests
export OPENAI_API_KEY="sk-..."

# Optional: Control test verbosity
export PYTEST_ADDOPTS="-v"
```

### pyproject.toml

```toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration tests",
    "performance: marks tests as performance tests",
]
```

## Writing Tests

### Unit Test Example

```python
# tests/unit/test_myfeature.py
import pytest

def test_my_feature():
    """Unit test - fast, no external dependencies"""
    result = my_function("input")
    assert result == "expected"
```

### Integration Test Example

```python
# tests/integration/test_myfeature_integration.py
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_my_feature_integration(skip_without_api_key):
    """Integration test - may use real LLM"""
    runtime = RuntimeLoop("config.yaml")
    result = await runtime.process_message("test", "user-id")
    assert isinstance(result, str)
```

### Performance Test Example

```python
# tests/performance/test_myfeature_perf.py
import pytest
import time

@pytest.mark.performance
@pytest.mark.asyncio
async def test_my_feature_latency():
    """Performance test - measures latency"""
    start = time.time()
    result = await expensive_operation()
    latency = time.time() - start
    assert latency < 0.5  # 500ms threshold
```

## Troubleshooting

### Integration Tests Failing

**Problem**: E2E tests fail with LLM errors

**Solutions**:
1. Check `OPENAI_API_KEY` is set: `echo $OPENAI_API_KEY`
2. Check `.env` file exists and contains the key
3. Tests may be flaky - retry or mark as flaky:
   ```python
   @pytest.mark.flaky(reruns=3, reruns_delay=2)
   ```

### Performance Tests Failing

**Problem**: Performance tests fail with timeout or threshold errors

**Solutions**:
1. Adjust thresholds in test files for your environment
2. Skip performance tests in CI: `make test-ci`
3. Run on more powerful hardware

### Coverage Too Low

**Problem**: Coverage below 80% threshold

**Solutions**:
1. Add tests for uncovered code
2. Remove dead code
3. Adjust threshold in `pyproject.toml` if justified

## Test Metrics

### Current Status (after migration)

| Category | Tests | Status | Time |
|----------|-------|--------|------|
| Unit | 512 | ✅ 100% pass | ~52s |
| Integration | ~32 | ⚠️ Some flaky | Variable |
| Performance | ~13 | ⚠️ Environment-dependent | Variable |
| **TOTAL** | **~557** | **✅ 97.7% pass** | **Varies** |

### Quality Metrics

- ✅ **mypy**: 0 errors
- ✅ **ruff**: 0 errors
- ✅ **Coverage**: 85%+
- ✅ **No `# type: ignore` comments**

## Best Practices

1. **Write unit tests first** - Fast feedback
2. **Add integration tests for critical paths** - Ensure components work together
3. **Use performance tests sparingly** - Only for critical performance requirements
4. **Mock external dependencies in unit tests** - Keep them fast
5. **Mark tests appropriately** - Use `@pytest.mark.integration` and `@pytest.mark.performance`
6. **Keep tests deterministic** - Avoid randomness, time dependencies
7. **Clean up resources** - Use fixtures for setup/teardown
8. **Test edge cases** - Don't just test happy paths

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
