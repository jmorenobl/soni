.PHONY: help build clean check test lint type-check format publish-testpypi publish-pypi install-testpypi verify docs docs-serve docs-build docs-clean

# Load environment variables from .env file
ifneq (,$(wildcard .env))
include .env
export
endif

# Default target
help:
	@echo "Available targets:"
	@echo "  make build              - Build the package"
	@echo "  make clean              - Clean build artifacts"
	@echo "  make check              - Run all checks (test, lint, type-check)"
	@echo ""
	@echo "Testing:"
	@echo "  make test               - Run unit tests in parallel (default, fast)"
	@echo "  make test-all           - Run all tests in parallel"
	@echo "  make test-integration   - Run integration tests (sequential)"
	@echo "  make test-performance   - Run performance tests (sequential)"
	@echo "  make test-ci            - Run unit + integration in parallel (for CI)"
	@echo "  make test-sequential    - Run unit tests sequentially (for debugging)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint               - Run linting"
	@echo "  make type-check         - Run type checking"
	@echo "  make format             - Format code"
	@echo ""
	@echo "Publishing:"
	@echo "  make publish-testpypi   - Publish to TestPyPI"
	@echo "  make publish-pypi       - Publish to PyPI"
	@echo "  make install-testpypi   - Install from TestPyPI (for testing)"
	@echo "  make verify             - Verify package contents"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs               - Build documentation"
	@echo "  make docs-serve         - Serve documentation locally (dev server)"
	@echo "  make docs-build         - Build documentation to site/"
	@echo "  make docs-clean         - Clean documentation build artifacts"

# Build the package
build:
	@echo "Building package..."
	@rm -rf dist/
	uv build
	@echo "Build complete! Files in dist/"

# Clean build artifacts
clean: docs-clean
	@echo "Cleaning build artifacts..."
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	@echo "Clean complete!"

# Documentation targets
docs: docs-build
	@echo "Documentation built successfully!"

# Serve documentation locally (development server)
docs-serve:
	@echo "Starting MkDocs development server..."
	@echo "Documentation will be available at http://127.0.0.1:8000"
	uv run mkdocs serve

# Build documentation to site/
docs-build:
	@echo "Building documentation..."
	uv run mkdocs build
	@echo "Documentation built in site/"

# Clean documentation build artifacts
docs-clean:
	@echo "Cleaning documentation build artifacts..."
	rm -rf site/
	@echo "Documentation build artifacts cleaned!"

# Run all checks
check: test lint type-check
	@echo "All checks passed!"

# Run tests (unit tests only by default)
test:
	@echo "Running unit tests in parallel..."
	uv run pytest -m "not integration and not performance" -n auto

# Run all tests (unit + integration + performance)
test-all:
	@echo "Running all tests..."
	uv run pytest -n auto

# Run integration tests only
test-integration:
	@echo "Running integration tests..."
	uv run pytest -m integration

# Run performance tests only
test-performance:
	@echo "Running performance tests..."
	uv run pytest -m performance

# Run unit + integration tests (no performance)
test-ci:
	@echo "Running unit and integration tests..."
	uv run pytest -m "not performance" -n auto

# Run tests without parallelization (useful for debugging)
test-sequential:
	@echo "Running unit tests sequentially..."
	uv run pytest -m "not integration and not performance"

# Run linting
lint:
	@echo "Running linting..."
	uv run ruff check .
	uv run ruff format --check .

# Run type checking
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
		echo "Please copy .env.example to .env and add your credentials"; \
		exit 1; \
	fi
	@bash -c 'export UV_PUBLISH_USERNAME="$(UV_PUBLISH_TESTPYPI_USERNAME)" && \
		export UV_PUBLISH_PASSWORD="$(UV_PUBLISH_TESTPYPI_PASSWORD)" && \
		uv publish --publish-url https://test.pypi.org/legacy/ dist/*'
	@echo "Published to TestPyPI successfully!"

# Publish to PyPI
publish-pypi: check build
	@echo "Publishing to PyPI..."
	@if [ -z "$(UV_PUBLISH_USERNAME)" ] || [ -z "$(UV_PUBLISH_PASSWORD)" ]; then \
		echo "Error: PyPI credentials not found in .env file"; \
		echo "Please copy .env.example to .env and add your credentials"; \
		exit 1; \
	fi
	@bash -c 'export UV_PUBLISH_USERNAME="$(UV_PUBLISH_USERNAME)" && \
		export UV_PUBLISH_PASSWORD="$(UV_PUBLISH_PASSWORD)" && \
		uv publish dist/*'
	@echo "Published to PyPI successfully!"

# Install from TestPyPI (for testing)
install-testpypi:
	@echo "Installing from TestPyPI..."
	uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ soni
	@echo "Installation complete!"

# Verify package contents
verify:
	@echo "Verifying package contents..."
	@if [ ! -d "dist" ]; then \
		echo "Error: dist/ directory not found. Run 'make build' first."; \
		exit 1; \
	fi
	@if command -v twine > /dev/null 2>&1 || uv run twine --version > /dev/null 2>&1; then \
		uv run twine check dist/* || true; \
	else \
		echo "Note: twine not installed, skipping twine check"; \
	fi
	@tar -tzf dist/soni-*.tar.gz | head -20
