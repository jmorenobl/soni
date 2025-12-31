# Quickstart Guide - Soni Framework

This guide will help you get started with Soni Framework in 5 minutes.

## Installation

### Prerequisites

- Python 3.11 or higher
- OpenAI API key (or other supported LLM provider)

### Install Soni

```bash
# Clone the repository
git clone https://github.com/jmorenobl/soni.git
cd soni

# Install dependencies
uv sync
```

### Set Up API Key

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Your First Dialogue System

### 1. Create Configuration

Create a file `my_dialogue.yaml`:

```yaml
version: "0.1"

settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
      temperature: 0.1
  persistence:
    backend: sqlite
    path: ./my_dialogue.db

flows:
  greet:
    trigger:
      # Natural language phrase examples that trigger this flow
      # Used for NLU optimization - the LLM learns to map these phrases to the flow name
      intents:
        - "Hello"
        - "Hi there"
        - "Good morning"
    steps:
      - step: respond
        type: action
        call: greet_user

actions:
  greet_user:
    description: "Greet the user"
    # No handler path needed - registered via @ActionRegistry.register()
    inputs: []
    outputs:
      - message
```

### 2. Create Handlers

Create `my_handlers.py` in the same directory as your YAML file:

```python
from soni.actions.registry import ActionRegistry

@ActionRegistry.register("greet_user")
async def greet() -> dict:
    """Greet the user with a friendly message."""
    return {"message": "Hello! How can I help you?"}
```

**Note:** The runtime automatically discovers and imports `my_handlers.py` from the config directory, so actions are registered automatically when the server starts.

### 3. Start the Server

```bash
uv run soni server --config my_dialogue.yaml
```

### 4. Test It

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-123", "message": "Hello"}'
```

## Next Steps

- See the [Banking Example](../../examples/banking/README.md) for a complete example
- Read the [Architecture Guide](../explanation/architecture.md) to understand how Soni works
- Check the [DSL Specification](../reference/dsl-spec.md) for detailed documentation

## Troubleshooting

### Common Issues

**Issue:** `ModuleNotFoundError: No module named 'soni'`
- **Solution:** Make sure you've installed the package with `uv sync`

**Issue:** `OPENAI_API_KEY not set`
- **Solution:** Export your API key: `export OPENAI_API_KEY="your-key"`

**Issue:** `ConfigurationError: Invalid YAML`
- **Solution:** Validate your YAML with: `uv run python scripts/validate_config.py my_dialogue.yaml`
