# Soni Framework - Development Guide

**Generated:** 2026-01-01

## Prerequisites

### Required Software

- **Python** 3.11 or higher
- **uv** package manager (recommended) or pip
- **Git** for version control
- **OpenAI API key** or compatible LLM provider

### Optional Tools

- **Docker** (for containerized deployment)
- **Make** (for using Makefile commands)

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/jmorenobl/soni.git
cd soni
```

### 2. Install Dependencies

#### Using uv (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

#### Using pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e ".[dev]"
```

### 3. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API key
export OPENAI_API_KEY="your-api-key-here"
```

**Required Environment Variables:**
- `OPENAI_API_KEY` - OpenAI API key for LLM calls

**Optional Environment Variables:**
- `SONI_LOG_LEVEL` - Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `SONI_HOST` - Server bind address (default: 127.0.0.1)
- `SONI_PORT` - Server port (default: 8000)

### 4. Install Pre-commit Hooks

```bash
uv run pre-commit install
```

This ensures code quality checks run automatically before each commit.

## Local Development Commands

### Running the Framework

#### Interactive Chat Mode

```bash
uv run soni chat --config examples/banking/domain --module examples.banking.handlers
```

**Options:**
- `--config PATH` - Path to YAML configuration directory
- `--module MODULE` - Python module with action handlers (dot notation)

#### API Server Mode

```bash
uv run soni server --config examples/banking/domain --module examples.banking.handlers
```

**Options:**
- `--host TEXT` - Bind address (default: 127.0.0.1)
- `--port INT` - Port number (default: 8000)
- `--reload` - Enable auto-reload on code changes (dev only)

**Testing the API:**
```bash
# Health check
curl http://localhost:8000/health

# Send message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user", "message": "I want to transfer money"}'
```

### Optimization

#### Run DSPy Optimization

```bash
uv run soni optimize run --config examples/banking/domain
```

This runs MIPROv2 optimization to improve NLU prompts using training data.

## Build Process

### Building Distribution

```bash
# Build wheel and source distribution
uv build

# Output: dist/soni-0.4.0-py3-none-any.whl
#         dist/soni-0.4.0.tar.gz
```

### Installing Built Package

```bash
pip install dist/soni-0.4.0-py3-none-any.whl
```

## Testing Approach

### Test Organization

| Directory | Purpose | Command |
|-----------|---------|---------|
| `tests/unit/` | Component-level tests | `uv run pytest tests/unit/` |
| `tests/integration/` | Cross-component tests | `uv run pytest tests/integration/` |
| `tests/e2e/` | End-to-end dialogue tests | `uv run pytest tests/e2e/` |

### Running Tests

#### All Tests

```bash
uv run pytest
```

#### Specific Test Suites

```bash
# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests
uv run pytest tests/integration/ -v

# E2E tests (requires OPENAI_API_KEY)
uv run pytest tests/e2e/ -v
```

#### Test Markers

```bash
# Skip slow tests
uv run pytest -m "not slow"

# Skip integration tests
uv run pytest -m "not integration"

# Run only E2E tests
uv run pytest -m e2e
```

#### Parallel Execution

```bash
# Run tests in parallel (4 workers)
uv run pytest -n 4
```

### Coverage Reports

```bash
# Run tests with coverage
uv run pytest --cov=soni --cov-report=html

# View HTML report
open htmlcov/index.html
```

**Coverage Targets:**
- Current minimum: 30%
- MVP goal: 60%

### Writing Tests

#### Unit Test Example

```python
# tests/unit/core/test_validation.py
import pytest
from soni.core.validation import validate_slot

@pytest.mark.asyncio
async def test_validate_slot_with_regex():
    slot_def = {"name": "email", "type": "string", "regex": r".+@.+\..+"}
    result = await validate_slot("user@example.com", slot_def)
    assert result.is_valid
```

#### Integration Test Example

```python
# tests/integration/test_flow_execution.py
import pytest
from soni.runtime import RuntimeLoop

@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_flow():
    loop = RuntimeLoop(config_path="examples/banking/domain")
    result = await loop.process_message("user-1", "transfer money")
    assert "who would you like" in result.lower()
```

## Common Development Tasks

### Code Quality Commands

#### Linting

```bash
# Check code style (read-only)
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check . --fix
```

#### Formatting

```bash
# Format code
uv run ruff format .
```

#### Type Checking

```bash
# Run mypy type checker
uv run mypy src/soni
```

### Using Makefile

```bash
# Run all quality checks
make lint

# Format code
make format

# Run tests
make test

# Run tests with coverage
make test-cov

# Clean build artifacts
make clean

# Install dependencies
make install
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. To run manually:

```bash
# Run on all files
uv run pre-commit run --all-files

# Run specific hook
uv run pre-commit run ruff --all-files
```

**Configured Hooks:**
- Ruff (linting & formatting)
- Mypy (type checking)
- Trailing whitespace removal
- YAML/TOML validation

## Debugging

### Enable Debug Logging

```bash
export SONI_LOG_LEVEL=DEBUG
uv run soni chat --config examples/banking/domain --module examples.banking.handlers
```

### Inspecting State

Use breakpoints in your IDE or `import pdb; pdb.set_trace()` in code.

### Viewing LangGraph Execution

LangGraph creates checkpoints in SQLite. Inspect the database:

```bash
sqlite3 banking_state.db
.tables
SELECT * FROM checkpoints LIMIT 5;
```

## Creating a New Example

### 1. Create Directory Structure

```bash
mkdir -p examples/my_domain/domain
touch examples/my_domain/handlers.py
touch examples/my_domain/domain/soni.yaml
```

### 2. Define YAML Configuration

```yaml
# examples/my_domain/domain/soni.yaml
flows:
  greet:
    description: "Greet the user"
    trigger:
      intents:
        - "hello"
        - "hi"
    steps:
      - step: greet_user
        type: say
        message: "Hello! How can I help you?"
```

### 3. Implement Action Handlers

```python
# examples/my_domain/handlers.py
from soni.runtime import RuntimeContext

async def custom_action(runtime_context: RuntimeContext) -> dict:
    """Custom action handler."""
    return {"result": "success"}
```

### 4. Run Your Example

```bash
uv run soni chat --config examples/my_domain/domain --module examples.my_domain.handlers
```

## Deployment

### Production Recommendations

1. **Use Uvicorn with multiple workers:**
   ```bash
   uv run uvicorn soni.server.main:app \
     --host 0.0.0.0 \
     --port 8000 \
     --workers 4
   ```

2. **Use a reverse proxy** (Nginx, Traefik)

3. **Set appropriate environment variables**

4. **Use persistent storage** for state database

### Docker Deployment

#### Example Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies (production only)
RUN uv sync --no-dev

# Expose port
EXPOSE 8000

# Run server
CMD ["uv", "run", "soni", "server", \
     "--config", "examples/banking/domain", \
     "--module", "examples.banking.handlers", \
     "--host", "0.0.0.0"]
```

#### Build and Run

```bash
# Build image
docker build -t soni-app .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  soni-app
```

## Troubleshooting

### Common Issues

#### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'soni'`

**Solution:**
```bash
# Reinstall in editable mode
uv sync
```

#### API Key Errors

**Problem:** `openai.error.AuthenticationError`

**Solution:**
```bash
# Check environment variable
echo $OPENAI_API_KEY

# Set it if missing
export OPENAI_API_KEY="your-key"
```

#### Test Failures

**Problem:** E2E tests fail with `RuntimeWarning: coroutine was never awaited`

**Solution:** Ensure OPENAI_API_KEY is set and valid

#### Port Already in Use

**Problem:** `OSError: [Errno 48] Address already in use`

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process or use a different port
uv run soni server --port 8001
```

## Getting Help

- **Documentation:** [docs/](index.md)
- **Issues:** https://github.com/jmorenobl/soni/issues
- **Contributing:** [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Changelog:** [CHANGELOG.md](../CHANGELOG.md)

---

**Happy coding with Soni! 🤖✨**
