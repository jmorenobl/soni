# 🤖 Soni Framework

**Open Source Conversational AI Framework with Prompt Optimization**

Soni is a modern framework for building task-oriented dialogue systems that combines the power of DSPy for prompt optimization with LangGraph for robust dialogue management.

> [!WARNING]
> **Experimental Project**: This project is in an early stage of development and is currently experimental.


## The Three Laws of Soni

1. **Declarative First**: Define behavior, not implementation
2. **Optimizable**: Learn from data through DSPy optimization
3. **No Black Boxes**: Full transparency and explainability

*Inspired by Asimov's vision of intelligent, helpful AI*

## Features

- 🤖 **Prompt Optimization** - Uses DSPy's MIPROv2 to optimize NLU prompts
- 🔄 **Stateful Dialogue Management** - Built on LangGraph for reliable conversation flows
- 📝 **YAML-Based Configuration** - Declarative DSL for defining dialogue flows
- ⚡ **Async-First Architecture** - High-performance async/await throughout
- 🎯 **Zero-Leakage Design** - Technical details don't leak into configuration
- 📊 **Streaming Support** - Real-time token streaming with Server-Sent Events (SSE)
- 🎯 **Dynamic Scoping** - Context-aware action filtering reduces tokens by 39.5%
- 🔧 **Slot Normalization** - Automatic normalization improves validation by 11.11%
- ⚡ **Performance Optimizations** - Caching, connection pooling, and async checkpointing

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/jmorenobl/soni.git
cd soni

# Install dependencies
uv sync

# Install the package
uv pip install -e .

# Set API key
export OPENAI_API_KEY="your-api-key-here"
```

### Start the Server

```bash
# Run the example
uv run soni chat --config examples/banking/domain --module examples.banking.handlers
```

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# Start a conversation
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-123", "message": "I want to transfer money to my friend"}'
```

See [Quickstart Guide](docs/quickstart.md) for detailed instructions.

## Example

The banking example demonstrates a complete dialogue system:

```yaml
flows:
  transfer_funds:
    description: "Transfer money to another account"
    trigger:
      intents:
        - "I want to transfer money"
        - "Send {amount} to {beneficiary_name}"
    steps:
      - step: collect_beneficiary
        type: collect
        slot: beneficiary_name
        message: "Who would you like to send the money to?"

      - step: collect_amount
        type: collect
        slot: amount
        message: "How much would you like to transfer?"

      - step: confirm_transfer
        type: confirm
        slot: transfer_confirmed
        message: "Ready to send {amount} to {beneficiary_name}?"

      - step: execute_transfer
        type: action
        call: execute_transfer
```

See [Banking Example](examples/banking/README.md) for a complete example.

## Documentation

- [Quickstart Guide](docs/tutorials/quickstart.md) - Get started in 5 minutes
- [Architecture Overview](docs/architecture_overview.md) - Understand how Soni works

## Requirements

- Python 3.11+
- OpenAI API key (or other supported LLM provider)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Why "Soni"?

The name **Soni** is inspired by **Sonny**, the remarkable robot from Isaac Asimov's classic story collection "I, Robot". Like Sonny, who was special among robots—capable of learning, reasoning, and continuously optimizing his behavior—Soni represents a framework that learns and improves itself through automatic prompt optimization.

Just as Sonny questioned and refined his own programming, Soni uses DSPy to optimize conversational AI systems through manual optimization runs, making them smarter with each optimization cycle. The framework embodies Asimov's vision of intelligent, helpful AI that can be improved to better serve its purpose.

*"The Three Laws of Robotics are built into the very foundation of Soni's architecture: to assist, to optimize, and to improve—all while maintaining transparency and control."*

## Acknowledgments

- [DSPy](https://github.com/stanfordnlp/dspy) - For prompt optimization
- [LangGraph](https://github.com/langchain-ai/langgraph) - For dialogue management
- [FastAPI](https://fastapi.tiangolo.com/) - For the API framework
- [Typer](https://typer.tiangolo.com/) - For the CLI interface

---

**Built with ❤️ by the Soni Framework Contributors**
