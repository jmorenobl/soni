# Contributing to Soni Framework

Thank you for your interest in contributing to Soni! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/soni.git
cd soni

# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

## Development Workflow

1. **Create a branch** from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Run tests and linting**
   ```bash
   uv run pytest
   uv run ruff check .
   uv run mypy src/soni
   ```

4. **Commit your changes** (pre-commit hooks will run automatically)
   ```bash
   git commit -m "feat: add your feature"
   ```

5. **Push and create a Pull Request**

## Coding Standards

### Code Style

- Follow PEP 8 style guide
- Use `ruff` for linting and formatting
- Maximum line length: 100 characters
- Use type hints for all function signatures

### Type Hints

```python
from typing import Dict, List, Optional

def process_message(
    user_msg: str,
    user_id: str,
    context: Optional[Dict[str, any]] = None
) -> str:
    """Process a user message and return response."""
    ...
```

### Testing

- Write tests for all new features
- Aim for >60% code coverage (MVP target)
- Use `pytest` and `pytest-asyncio` for async tests
- Place tests in `tests/unit/` or `tests/integration/`

### Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Update README.md for user-facing changes
- Update ADR documents for architectural decisions

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Example:
```
feat: add streaming support to RuntimeLoop

- Implement process_message_stream method
- Add SSE endpoint in FastAPI server
- Add tests for streaming functionality
```

## Pull Request Process

1. Ensure all tests pass
2. Ensure linting passes (`ruff check`)
3. Ensure type checking passes (`mypy`)
4. Update documentation as needed
5. Add changelog entry if applicable
6. Request review from maintainers

## Questions?

Feel free to open an issue for questions or discussions!

---

Thank you for contributing to Soni! 🎉
