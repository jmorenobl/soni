# Quickstart Guide - Soni Framework

This guide will help you get started with Soni Framework in 5 minutes.

## Installation

### Prerequisites

- Python 3.11 or higher
- OpenAI API key (or other supported LLM provider)

### Install Soni

```bash
# Clone the repository
git clone https://github.com/your-org/soni-framework.git
cd soni-framework

# Install dependencies
uv sync

# Install the package
uv pip install -e .
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
      intents:
        - greet
        - hello
    steps:
      - step: respond
        type: action
        call: greet_user

actions:
  greet_user:
    handler: my_handlers.greet
    inputs: []
    outputs:
      - message
```

### 2. Create Handlers

Create `my_handlers.py`:

```python
async def greet() -> dict:
    return {"message": "Hello! How can I help you?"}
```

### 3. Start the Server

```bash
uv run soni server --config my_dialogue.yaml
```

### 4. Test It

```bash
curl -X POST http://localhost:8000/chat/user-123 \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

## Next Steps

- See the [Flight Booking Example](../examples/flight_booking/README.md) for a complete example
- Read the [Architecture Guide](architecture.md) to understand how Soni works
- Check the [API Reference](../README.md#api-reference) for detailed documentation

## Troubleshooting

### Common Issues

**Issue:** `ModuleNotFoundError: No module named 'soni'`
- **Solution:** Make sure you've installed the package with `uv pip install -e .`

**Issue:** `OPENAI_API_KEY not set`
- **Solution:** Export your API key: `export OPENAI_API_KEY="your-key"`

**Issue:** `ConfigurationError: Invalid YAML`
- **Solution:** Validate your YAML with: `uv run python scripts/validate_config.py my_dialogue.yaml`
