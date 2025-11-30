# Soni Framework - Agent Instructions

This document defines the rules and conventions for developing the Soni framework, a conversational dialogue system with automatic prompt optimization.

## Architecture and Fundamental Principles

### Zero-Leakage Architecture (Hexagonal)

- **Separation of Concerns**: YAML (core) only describes WHAT should happen, not HOW. Technical details (HTTP, regex, SQL) live in Python code.
- **Action Registry**: Actions are defined as semantic contracts in YAML and implemented in Python with `@ActionRegistry.register`.
- **Validator Registry**: Validators are referenced by semantic name in YAML and implemented in Python with `@ValidatorRegistry.register`.
- **Output Mapping**: Use `map_outputs` in action steps to decouple technical data structures from flat flow variables.

### SOLID Principles

- **Abstract Interfaces**: Use Python `Protocol` to define contracts (see `core/interfaces.py`).
- **Dependency Inversion**: Depend on abstractions (`INLUProvider`, `IDialogueManager`, `IActionHandler`, `IScopeManager`, `INormalizer`), not concrete implementations. All constructors accept Protocols as optional parameters.
- **Single Responsibility**: Each module has a single, well-defined responsibility. God Objects have been eliminated through refactoring.
- **Decoupling**: Code must be testable through interface mocking. Use `RuntimeContext` to pass dependencies to nodes, not `state.config`.

### Async-First Architecture

- **Everything is async**: All I/O operations, LLM calls, and dialogue processing must be `async def`.
- **No sync versions**: The framework is exclusively asynchronous. Do not create sync-to-async wrappers.
- **Native streaming**: Use `AsyncGenerator` for token and response streaming.
- **Async I/O**: Use `aiosqlite`, `asyncpg`, `aioredis` for persistence. Never use sync versions.

## Code Conventions

### Style and Formatting

- **PEP 8**: Strictly follow PEP 8.
- **Ruff**: Use `ruff` for linting and formatting. Configuration in `pyproject.toml`.
- **Max line length**: 100 characters (configured in `pyproject.toml`).
- **Quotes**: Use double quotes for strings (ruff configuration).
- **Imports**: Automatically ordered with `ruff` (isort).

### Type Hints

- **Mandatory**: All public functions and methods must have complete type hints.
- **Modern `typing` usage**: Prefer modern `typing` types:
  - `list[str]` instead of `List[str]` (Python 3.9+)
  - `dict[str, Any]` instead of `Dict[str, Any]`
  - `str | None` instead of `Optional[str]` (Python 3.10+)
- **Protocols**: Use `Protocol` for interfaces (see `core/interfaces.py`).
- **Type checking**: Run `mypy src/soni` before committing.

### Docstrings

- **Google style**: Use Google-style docstrings for all public functions and classes.
- **Structure**:
  ```python
  def function_name(param1: str, param2: int) -> dict[str, Any]:
      """
      Brief one-line description.

      More detailed description if necessary.

      Args:
          param1: Description of parameter 1
          param2: Description of parameter 2

      Returns:
          Description of return value

      Raises:
          ValidationError: When parameter is invalid
      """
  ```

### Naming Conventions

- **Classes**: PascalCase (`DialogueState`, `SoniDU`)
- **Functions and variables**: snake_case (`process_message`, `user_id`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private modules**: Prefix `_` for internal functions/modules (`_create_node`, `_internal_utils.py`)
- **Type variables**: PascalCase (`T`, `K`, `V`)

## Project Structure

### Module Organization

```
src/soni/
├── core/          # Interfaces, state, errors (framework core)
├── du/            # Dialogue Understanding (DSPy modules)
├── dm/            # Dialogue Management (LangGraph integration)
├── compiler/      # YAML to Graph compilation
├── actions/       # Action Registry and base actions
├── validation/    # Validator Registry and base validators
├── server/        # FastAPI endpoints and WebSocket
└── cli/           # CLI commands
```

### Import Rules

- **Absolute imports**: Use absolute imports from `soni.`:
  ```python
  from soni.core.state import DialogueState
  from soni.core.interfaces import INLUProvider
  ```
- **Avoid circular imports**: Use `from __future__ import annotations` and strings for type hints when necessary.
- **Type imports**: Separate type imports:
  ```python
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from soni.core.state import DialogueState
  ```

## Error Handling

### Exception Hierarchy

- **Base**: `SoniError` (in `core/errors.py`)
- **Specific**: `NLUError`, `ValidationError`, `ActionNotFoundError`, `CompilationError`, `ConfigurationError`, `PersistenceError`
- **Context**: Always include relevant context in exceptions:
  ```python
  raise ValidationError(
      "Invalid slot value",
      field="destination",
      value=raw_value,
      context={"flow": current_flow}
  )
  ```

### Validation and Sanitization

- **Validate inputs**: All external inputs must be validated before processing.
- **Sanitize**: Sanitize user inputs to prevent injections.
- **Clear messages**: Error messages must be clear and useful for debugging.

## Testing

### Test Structure

- **Unit tests**: `tests/unit/` - Isolated tests for individual functions/classes
- **Integration tests**: `tests/integration/` - Integration tests between components
- **Naming**: `test_*.py` for files, `test_*` for functions
- **Coverage**: Minimum target 80% (configured in `pyproject.toml`)

### Testing Conventions

- **AAA Pattern**: All tests must follow the Arrange-Act-Assert (AAA) pattern:
  ```python
  def test_function_name():
      """Test description explaining what is being tested"""
      # Arrange - Set up test data and conditions
      user = User(name="John", age=30)

      # Act - Execute the function being tested
      result = user.get_greeting()

      # Assert - Verify the expected outcome
      assert result == "Hello, John!"
  ```
  - **Arrange**: Set up all test preconditions and inputs
  - **Act**: Execute the function or method being tested
  - **Assert**: Verify the outcome matches expectations
  - Use `# Arrange`, `# Act`, `# Assert` comments to clearly separate phases
  - For simple tests, combine phases: `# Arrange & Act` or `# Act & Assert`

- **Async tests**: Use `pytest-asyncio` for async tests:
  ```python
  import pytest

  @pytest.mark.asyncio
  async def test_async_function():
      # Arrange
      input_data = "test"

      # Act
      result = await async_function(input_data)

      # Assert
      assert result == expected
  ```

- **Cleanup**: For tests with mocks or resources, use try/finally:
  ```python
  def test_with_mock():
      """Test with cleanup section"""
      # Arrange
      original_function = module.function
      module.function = mock_function

      try:
          # Act
          result = perform_operation()

          # Assert
          assert result == expected
      finally:
          # Cleanup
          module.function = original_function
  ```

- **Fixtures**: Use pytest fixtures for common setup.
- **Mocks**: Use `unittest.mock` or `pytest-mock` to mock interfaces.
- **Descriptive docstrings**: Each test must have a clear docstring explaining what it validates.

### Relaxed Test Rules

- Tests can use more relaxed rules (see `pyproject.toml`):
  - `B008`: Allow function calls in default arguments (common in fixtures)
  - `B006`: Allow mutable default arguments (common in fixtures)
  - `S101`: Allow `assert` (tests use assertions)
  - `ARG`: Allow unused arguments (common in fixtures)

## DSPy Integration

### DSPy Modules

- **Inheritance**: DU modules must inherit from `dspy.Module`:
  ```python
  class SoniDU(dspy.Module):
      def __init__(self):
          super().__init__()  # CRITICAL: Call super().__init__()
  ```
- **Async methods**: Implement `aforward()` for async runtime and `forward()` for sync optimizers.
- **Signatures**: Define DSPy Signatures in `du/signatures.py` with clear fields and descriptions.

### Optimization

- **Optimizers**: MIPROv2, SIMBA, GEPA, BootstrapFewShot
- **Metrics**: Define business metrics (`intent_accuracy`, `slot_f1`)
- **Serialization**: Use `.save()` and `.load()` for optimized modules.

## LangGraph Integration

### Graph Building

- **Async nodes**: All nodes must be `async def`.
- **StateGraph**: Use LangGraph's `StateGraph` with `DialogueState`.
- **Checkpointers**: Use async checkpointers (`SqliteSaver`, `PostgresSaver`, `RedisSaver`).
- **Streaming**: Use `astream()` for event streaming.

### Step Compiler

- **Procedural DSL**: The compiler translates procedural steps (`steps`) to `StateGraph`.
- **Implicit next**: Steps connect sequentially by default.
- **Explicit jumps**: Use `jump_to` to break sequentiality when necessary.
- **Branches**: Implement branching logic with `add_conditional_edges`.

## YAML DSL

### DSL Principles

- **Pure semantic**: YAML only describes WHAT, not HOW.
- **Readability**: Must be readable for business analysts, not just developers.
- **No technical details**: Do not include URLs, HTTP methods, regex, JSONPath in YAML.
- **Contracts**: Define action contracts (inputs/outputs) instead of implementations.

### YAML Structure

- **Declarative flows**: For simple slot-filling, use declarative syntax.
- **Procedural flows**: For complex logic, use `process` with `steps`.
- **Entities**: Define entities globally with normalization and semantic validators.
- **Actions**: Define actions as contracts (inputs/outputs), not implementations.

### Procedural Flow Example

```yaml
flows:
  modify_booking:
    process:
      - step: request_id
        type: collect
        slot: booking_ref

      - step: verify_status
        type: action
        call: check_booking_rules
        map_outputs:
          status: api_status
          rejection_reason: reason

      - step: decide_path
        type: branch
        input: api_status
        cases:
          modifiable: continue
          not_modifiable: jump_to_explain
```

## Registries and Decorators

### Action Registry

- **Registration**: Use `@ActionRegistry.register("action_name")` to register actions.
- **Async implementation**: All actions must be `async def`.
- **Contracts**: Actions must comply with contracts defined in YAML (inputs/outputs).

### Validator Registry

- **Registration**: Use `@ValidatorRegistry.register("validator_name")` to register validators.
- **Implementation**: Can be sync or async as needed.
- **Semantic names**: Use descriptive names (`booking_ref_format`, `future_date_only`).

## Persistence and State

### DialogueState

- **Prefer immutability**: Prefer creating new states instead of mutating existing ones.
- **Serialization**: Use `to_dict()` and `from_dict()` for serialization.
- **Messages**: Store messages as `list[dict[str, str]]` with `role` and `content`.

### Checkpointers

- **Backends**: SQLite (development), PostgreSQL/Redis (production).
- **Async**: Always use async checkpointers.
- **Configuration**: Configuration in YAML under `settings.persistence`.

## Logging and Tracing

### Logging

- **Structured**: Use structured logging for debugging and auditing.
- **Levels**: DEBUG, INFO, WARNING, ERROR as appropriate.
- **Context**: Include relevant context (user_id, flow, turn_count) in logs.

### Tracing

- **Complete trace**: Record each turn with NLU result, policy decision, and state snapshot.
- **Audit**: Enable `audit_log` in configuration for compliance.
- **Performance**: Record latency and resource usage metrics.

## Security

### Guardrails

- **Action validation**: Validate that only allowed actions are executed.
- **Intent validation**: Block disallowed intents.
- **Confidence thresholds**: Validate confidence levels for critical actions.
- **Dynamic scoping**: Filter available actions based on context (reduces hallucinations).

### Input Sanitization

- **Sanitize everything**: All user inputs must be sanitized.
- **Strict validation**: Validate types, formats, and ranges before processing.
- **Prevent injections**: Prevent SQL injection, XSS, and other attacks.

## Documentation

### Code Documentation

- **Docstrings**: All public functions and classes must have docstrings.
- **Examples**: Include usage examples in docstrings when useful.
- **Type hints**: Type hints are documentation, use them consistently.

### Project Documentation

- **ADRs**: Document important architectural decisions in `docs/adr/`.
- **README**: Keep README.md updated with setup and basic usage.
- **Examples**: Provide complete examples in `examples/`.

## Git and Commits

### Conventional Commits

- **Format**: `type: description`
- **Types**: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`
- **Body**: Include details in commit body when necessary.
- **Example**:
  ```
  feat: add streaming support to RuntimeLoop

  - Implement process_message_stream method
  - Add SSE endpoint in FastAPI server
  - Add tests for streaming functionality
  ```

### Pre-commit Hooks

- **Automatic**: Hooks run automatically on commit.
- **Ruff**: Automatic linting and formatting.
- **Mypy**: Type checking (excludes experiments/).
- **Tests**: Run relevant tests before commit.

### Task Implementation Workflow

The process for implementing tasks from the backlog (`docs/tasks/backlog/`) follows this workflow:

1. **Start with the first task**: Move the first task from `docs/tasks/backlog/` to `docs/tasks/current/`.
2. **Implement the task**: Execute the implementation according to the task specifications.
3. **Quality checks and commit**: When all checks pass:
   - `ruff check .` and `ruff format .` must pass
   - `mypy src/soni` must pass
   - All relevant tests must pass
   - Make a commit following the conventional commits format
4. **Move to done**: Move the completed task from `docs/tasks/current/` to `docs/tasks/done/`.
5. **Repeat**: Start again with the next task from the backlog.
6. **Continue**: Repeat this process until all tasks in the backlog are completed.

This workflow ensures:
- **Incremental progress**: One task at a time, fully completed before moving to the next
- **Quality gates**: Code quality checks (ruff, mypy) and tests must pass before committing
- **Clear tracking**: Tasks move through backlog → current → done, providing clear visibility of progress
- **Atomic commits**: Each task results in a single, well-tested commit

## Performance and Optimization

### Latency

- **Differentiated models**: Use fast models (`gpt-4o-mini`) for NLU, powerful models for generation.
- **Streaming**: Use streaming to reduce perceived latency.
- **Caching**: Implement aggressive caching when appropriate.
- **Scoping**: Reduce context using dynamic scoping.

### Resources

- **Async I/O**: Use async I/O for maximum throughput.
- **Batching**: Group operations when possible.
- **Lazy loading**: Load resources only when needed.

## Dependencies

### Version Management

- **Ranges**: Use compatible version ranges (e.g., `>=3.0.4,<4.0.0`).
- **Updates**: Allow patch and minor updates, prevent major breaking changes.
- **Python**: Requires Python 3.11+ (improved async, modern type hints).

### Main Dependencies

- **DSPy**: `>=3.0.4,<4.0.0` - Automatic prompt optimization
- **LangGraph**: `>=1.0.4,<2.0.0` - Dialogue management
- **FastAPI**: `>=0.122.0,<1.0.0` - Async web API
- **Pydantic**: `>=2.12.5,<3.0.0` - Data validation

### Reference Code

- **`ref/` directory**: Contains the source code of the main libraries (DSPy and LangGraph) for reference purposes only. This code is available for consultation when implementing integrations or understanding library internals, but should not be modified or imported directly.

## Using `uv` Package Manager

This project uses [`uv`](https://github.com/astral-sh/uv) as the package manager. `uv` is a fast Python package installer and resolver written in Rust.

### Installation

If `uv` is not installed, install it with:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or with pip:

```bash
pip install uv
```

### Common Commands

#### Adding Dependencies

- **Add a runtime dependency**:
  ```bash
  uv add package-name
  ```

- **Add a development dependency**:
  ```bash
  uv add --dev package-name
  ```

- **Add with version constraint**:
  ```bash
  uv add "package-name>=1.0.0,<2.0.0"
  ```

- **Add to a dependency group**:
  ```bash
  uv add --group dev package-name
  ```

#### Removing Dependencies

- **Remove a package**:
  ```bash
  uv remove package-name
  ```

- **Remove from a dependency group**:
  ```bash
  uv remove --group dev package-name
  ```

#### Running Commands

- **Run a command in the project environment**:
  ```bash
  uv run command
  ```

- **Run Python scripts**:
  ```bash
  uv run python script.py
  ```

- **Run with arguments**:
  ```bash
  uv run pytest tests/
  uv run ruff check .
  uv run mypy src/soni
  ```

#### Synchronizing Dependencies

- **Sync dependencies** (install/update all packages from `pyproject.toml`):
  ```bash
  uv sync
  ```

- **Sync with specific groups**:
  ```bash
  uv sync --group dev
  ```

- **Sync without installing the project itself**:
  ```bash
  uv sync --no-install-project
  ```

#### Other Useful Commands

- **Show installed packages**:
  ```bash
  uv pip list
  ```

- **Update all dependencies**:
  ```bash
  uv sync --upgrade
  ```

- **Lock dependencies** (update `uv.lock`):
  ```bash
  uv lock
  ```

- **Create a virtual environment**:
  ```bash
  uv venv
  ```

- **Activate virtual environment** (if created separately):
  ```bash
  source .venv/bin/activate  # Linux/macOS
  .venv\Scripts\activate      # Windows
  ```

### Workflow Examples

**Initial setup**:
```bash
# Clone repository
git clone <repo-url>
cd soni

# Install all dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

**Adding a new dependency**:
```bash
# Add runtime dependency
uv add httpx

# Add dev dependency
uv add --dev pytest-cov

# Sync to install
uv sync
```

**Running tests**:
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=soni

# Run specific test file
uv run pytest tests/unit/test_state.py
```

**Code quality checks**:
```bash
# Lint and format
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy src/soni
```

**Validation scripts**:
```bash
# Validate configuration
uv run python scripts/validate_config.py

# Validate runtime (end-to-end)
uv run python scripts/validate_runtime.py
```

### Notes

- `uv` automatically manages the virtual environment in `.venv/`
- Dependencies are defined in `pyproject.toml` under `[project.dependencies]` and `[dependency-groups]`
- The lock file `uv.lock` ensures reproducible installs
- Always use `uv run` to execute commands in the project environment
- Never manually activate `.venv` - `uv run` handles it automatically

## Validation Scripts

The project includes validation scripts in the `scripts/` directory for testing and validating different components of the framework.

### Available Scripts

#### `scripts/validate_config.py`

Validates YAML configuration files to ensure they conform to the Soni configuration schema.

**Usage:**
```bash
# Validate the example configuration
uv run python scripts/validate_config.py examples/flight_booking/soni.yaml

# Validate any configuration file
uv run python scripts/validate_config.py path/to/config.yaml
```

**What it validates:**
- Configuration schema compliance
- Required fields presence
- Type validation
- Flow, slot, and action definitions

#### `scripts/validate_runtime.py`

Validates the LangGraph runtime end-to-end, including graph construction, state management, and checkpointing integration.

**Usage:**
```bash
# Run full runtime validation
uv run python scripts/validate_runtime.py
```

**What it validates:**
- Configuration loading from YAML
- Graph construction from flow definitions
- Checkpointer (SQLite) integration
- State serialization/deserialization
- Graph structure and node connectivity

**Output:**
- Detailed logging of each validation step
- Success/failure status for each component
- Summary report at the end
- Exit code 0 on success, 1 on failure

### When to Use Validation Scripts

- **After configuration changes**: Run `validate_config.py` to ensure YAML changes are valid
- **After runtime changes**: Run `validate_runtime.py` to verify the runtime still works end-to-end
- **Before committing**: Use validation scripts as part of pre-commit checks
- **During development**: Use to quickly test changes without running full test suite
- **Debugging**: Use to isolate issues in specific components

### Adding New Validation Scripts

When adding new validation scripts:

1. **Place in `scripts/` directory**: All validation scripts should be in `scripts/`
2. **Follow naming convention**: Use `validate_<component>.py` format
3. **Include logging**: Use structured logging with clear success/failure messages
4. **Return exit codes**: Return 0 on success, 1 on failure for CI/CD integration
5. **Document in AGENTS.md**: Add script description to this section

## Examples and Templates

### New Action

```python
from soni.actions import ActionRegistry

@ActionRegistry.register("my_action")
async def my_action(param1: str, param2: int) -> dict[str, Any]:
    """
    Action description.

    Args:
        param1: Parameter description
        param2: Parameter description

    Returns:
        Dictionary with outputs according to YAML contract
    """
    # Implementation here
    return {"output1": value1, "output2": value2}
```

### New Validator

```python
from soni.validation.registry import ValidatorRegistry

@ValidatorRegistry.register("my_validator")
def validate_my_field(value: str) -> bool:
    """
    Validates the field format.

    Args:
        value: Value to validate

    Returns:
        True if valid, False otherwise
    """
    # Validation logic
    return bool(re.match(r"^pattern$", value))
```

**Note:** Import the module containing your validators in your application entry point to auto-register them.

### New DSPy Module

```python
import dspy
from soni.du.signatures import MySignature

class MyModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(MySignature)

    async def aforward(self, input: str) -> dspy.Prediction:
        """Async runtime."""
        return await self.predictor.acall(input=input)

    def forward(self, input: str) -> dspy.Prediction:
        """For sync optimizers."""
        return self.predictor(input=input)
```

## Important Reminders

1. **Async-first**: Everything must be async. Do not create sync versions.
2. **Type hints**: Mandatory for all public functions.
3. **Docstrings**: Mandatory for all public functions and classes.
4. **Tests**: Write tests for new functionality following AAA pattern.
5. **AAA Pattern**: All tests must use Arrange-Act-Assert structure with clear comments.
6. **Semantic YAML**: YAML must not contain technical details.
7. **Interfaces**: Use Protocols for decoupling.
8. **Error handling**: Use appropriate exception hierarchy.
9. **Logging**: Include relevant context in logs.
10. **Conventional Commits**: Follow commit format.
11. **Pre-commit**: Ensure hooks pass before committing.

---

**Last updated**: Based on ADR-001 v1.3 and current project structure.
