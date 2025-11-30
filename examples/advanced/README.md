# Advanced Examples - Soni Framework v0.3.0

This directory contains advanced examples demonstrating the procedural DSL features introduced in v0.3.0, including branches and jumps.

## Examples

### retry_flow.yaml

Demonstrates a retry loop using `jump_to` to loop back to an earlier step.

**Features:**
- Collects user input
- Validates the input
- Uses a branch to check validation result
- Jumps back to collect step if validation fails (retry loop)
- Processes input if validation succeeds

**Key Concepts:**
- `jump_to`: Explicit control flow to jump back to `collect_input` step
- `branch`: Conditional routing based on `validation_result`
- Retry pattern: Loop back to collection step on validation failure

**Flow:**
```
collect_input → validate → check_validation
                                    ↓
                            ┌───────┴───────┐
                            │               │
                        valid          invalid
                            │               │
                            ↓               ↓
                    process_input    retry_collection
                                            ↓
                                    (jump_to: collect_input)
```

### branching_flow.yaml

Demonstrates complex branching logic with multiple paths and error handling.

**Features:**
- Collects destination
- Verifies route availability
- Branches based on route status:
  - `available`: Collect dates and end flow
  - `unavailable`: Suggest alternatives
  - `error`: Jump to error handler
- Uses `jump_to: __end__` to end flow early

**Key Concepts:**
- `branch`: Multiple conditional paths based on `route_status`
- `jump_to: __end__`: Early termination of flow
- `map_outputs`: Maps action output to state variable
- Error handling: Dedicated error handler step

**Flow:**
```
collect_destination → verify_route → decide_path
                                          ↓
                              ┌───────────┼───────────┐
                              │           │           │
                          available    unavailable   error
                              │           │           │
                              ↓           ↓           ↓
                        collect_dates  suggest_   error_handler
                        (jump_to:      alternatives
                         __end__)
```

## Running the Examples

### Prerequisites

1. Install Soni Framework:
   ```bash
   uv sync
   uv pip install -e .
   ```

2. Set OpenAI API key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

### Validate Configuration

```bash
# Validate retry flow
uv run python scripts/validate_config.py examples/advanced/retry_flow.yaml

# Validate branching flow
uv run python scripts/validate_config.py examples/advanced/branching_flow.yaml
```

### Run Server

```bash
# Run with retry flow
uv run soni server --config examples/advanced/retry_flow.yaml

# Run with branching flow
uv run soni server --config examples/advanced/branching_flow.yaml
```

### Test API

```bash
# Health check
curl http://localhost:8000/health

# Start conversation (retry flow)
curl -X POST http://localhost:8000/chat/user-123 \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to enter some data"}'
```

## Implementation Notes

### Action Handlers

These examples define action contracts in YAML but don't include Python handlers. To make them fully functional, you would need to:

1. Create a `handlers.py` file similar to `examples/flight_booking/handlers.py`
2. Register actions using `@ActionRegistry.register("action_name")`
3. Implement the action logic

Example handler structure:

```python
from soni.actions import ActionRegistry

@ActionRegistry.register("validate_input")
async def validate_input(user_input: str) -> dict[str, Any]:
    """Validate user input."""
    is_valid = len(user_input) > 0
    return {"validation_result": "valid" if is_valid else "invalid"}

@ActionRegistry.register("request_correction")
async def request_correction(user_input: str) -> dict[str, Any]:
    """Request user to correct input."""
    # Send message to user
    return {}
```

### Testing

To test these flows, you can:

1. Use the validation scripts to ensure YAML is correct
2. Create integration tests similar to `tests/integration/test_conditional_compiler.py`
3. Test manually using the API endpoints

## Related Documentation

- [DSL Guide](../../docs/dsl-guide.md) - Complete DSL syntax and examples
- [Architecture Guide](../../docs/architecture.md) - Framework architecture
- [Quickstart Guide](../../docs/quickstart.md) - Getting started
