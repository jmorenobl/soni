.PHONY: help build clean check test lint type-check format publish-testpypi publish-pypi install-testpypi verify docs docs-serve docs-build docs-clean install optimize

# Load environment variables from .env file
ifneq (,$(wildcard .env))
include .env
export
endif

# Default target
help:
	@echo "Available targets:"
	@echo "  make install            - Install dependencies using uv sync"
	@echo "  make build              - Build the package"
	@echo "  make clean              - Clean build artifacts and caches"
	@echo "  make check              - Run all checks (test, lint, type-check)"
	@echo ""
	@echo "Testing:"
	@echo "  make test               - Run fast unit tests (tests/unit, no slow/integration)"
	@echo "  make test-unit          - Run all unit tests (tests/unit) including slow"
	@echo "  make test-integration   - Run integration tests (tests/integration)"
	@echo "  make test-e2e           - Run E2E tests (tests/e2e)"
	@echo "  make test-all           - Run all tests (unit + integration + e2e)"
	@echo "  make test-ci            - Run unit + integration in parallel (for CI)"
	@echo ""
	@echo "Development:"
	@echo "  make chat               - Run banking example (CLI)"
	@echo "  make optimize           - Run quick baseline optimization"
	@echo "  make lint               - Run linting (ruff)"
	@echo "  make type-check         - Run type checking (mypy)"
	@echo "  make format             - Format code (ruff)"
	@echo ""
	@echo "Publishing:"
	@echo "  make publish-testpypi   - Publish to TestPyPI"
	@echo "  make publish-pypi       - Publish to PyPI"
	@echo "  make verify             - Verify package contents"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs               - Build documentation"
	@echo "  make docs-serve         - Serve documentation locally"

# Install dependencies
install:
	@echo "Installing dependencies..."
	uv sync

# Build the package
build:
	@echo "Building package..."
	@rm -rf dist/
	uv build
	@echo "Build complete! Files in dist/"

# Clean build artifacts
clean: docs-clean
	@echo "Cleaning artifacts..."
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Clean complete!"

# Documentation targets
docs: docs-build
docs-serve:
	uv run mkdocs serve
docs-build:
	uv run mkdocs build
docs-clean:
	rm -rf site/

# Run all checks
check: test lint type-check
	@echo "All checks passed!"

# Optimization
optimize:
	@echo "Running quick baseline optimization..."
	# uv run python scripts/quick_optimize.py
	@echo "Skipping optimization: src/soni/dataset module is missing."

# Run chat CLI with banking example
chat:
	@echo "Running Soni Chat (Banking Example)..."
	uv run soni chat --config examples/banking/domain --module examples.banking.handlers

# Tests
# Fast unit tests (parallel, exclude slow/integration)
test:
	@echo "Running fast unit tests..."
	uv run pytest tests/unit -m "not slow" -n auto

# All unit tests (parallel, include slow)
test-unit:
	@echo "Running all unit tests..."
	uv run pytest tests/unit -n auto

# Integration tests
test-integration:
	@echo "Running integration tests..."
	uv run pytest tests/integration

# E2E tests
test-e2e:
	@echo "Running E2E tests..."
	uv run pytest tests/e2e

# All tests
test-all:
	@echo "Running all tests..."
	uv run pytest tests -n auto

# CI target
test-ci:
	@echo "Running unit and integration tests..."
	uv run pytest tests -n auto

# Linting
lint:
	@echo "Running linting..."
	uv run ruff check .
	uv run ruff format --check .

# Type checking
type-check:
	@echo "Running type checking..."
	uv run mypy src/soni

# Format code
format:
	@echo "Formatting code..."
	uv run ruff format .

# Publish to TestPyPI
publish-testpypi: check build
	@echo "Publishing to TestPyPI..."
	@if [ -z "$(UV_PUBLISH_TESTPYPI_USERNAME)" ] || [ -z "$(UV_PUBLISH_TESTPYPI_PASSWORD)" ]; then \
		echo "Error: TestPyPI credentials not found in .env file"; \
		exit 1; \
	fi
	@bash -c 'export UV_PUBLISH_USERNAME="$(UV_PUBLISH_TESTPYPI_USERNAME)" && \
		export UV_PUBLISH_PASSWORD="$(UV_PUBLISH_TESTPYPI_PASSWORD)" && \
		uv publish --publish-url https://test.pypi.org/legacy/ dist/*'

# Publish to PyPI
publish-pypi: check build
	@echo "Publishing to PyPI..."
	@if [ -z "$(UV_PUBLISH_USERNAME)" ] || [ -z "$(UV_PUBLISH_PASSWORD)" ]; then \
		echo "Error: PyPI credentials not found in .env file"; \
		exit 1; \
	fi
	@bash -c 'export UV_PUBLISH_USERNAME="$(UV_PUBLISH_USERNAME)" && \
		export UV_PUBLISH_PASSWORD="$(UV_PUBLISH_PASSWORD)" && \
		uv publish dist/*'

# Verify package
verify:
	@echo "Verifying package contents..."
	@if [ ! -d "dist" ]; then echo "Error: dist/ not found"; exit 1; fi
	uv run twine check dist/*
	@tar -tzf dist/soni-*.tar.gz | head -20
