# Soni Framework

**Open Source Conversational AI Framework with Auto-Optimization**

Soni is a modern framework for building task-oriented dialogue systems that combines the power of DSPy for automatic prompt optimization with LangGraph for robust dialogue management.

## Features

- 🤖 **Automatic Prompt Optimization** - Uses DSPy's MIPROv2 to optimize NLU prompts automatically
- 🔄 **Stateful Dialogue Management** - Built on LangGraph for reliable conversation flows
- 📝 **YAML-Based Configuration** - Declarative DSL for defining dialogue flows
- ⚡ **Async-First Architecture** - High-performance async/await throughout
- 🎯 **Zero-Leakage Design** - Technical details don't leak into configuration
- 📊 **Streaming Support** - Real-time token streaming with Server-Sent Events

## Quick Start

> **Note:** Soni is currently in early development (v0.0.1). This quickstart will be updated as the framework matures.

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/soni.git
cd soni

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Basic Usage

```python
from soni import RuntimeLoop

# Initialize runtime with configuration
runtime = RuntimeLoop(config_path="examples/flight_booking/soni.yaml")

# Process a message
response = await runtime.process_message(
    user_msg="I want to book a flight to Paris",
    user_id="user-123"
)

print(response)
```

## Documentation

- [Quickstart Guide](docs/quickstart.md) - Get started in 10 minutes
- [Architecture Overview](docs/architecture.md) - Understand Soni's design
- [ADR-001: Framework Architecture](docs/adr/ADR-001-Soni-Framework-Architecture.md) - Detailed architecture decisions
- [Implementation Strategy](docs/strategy/Implementation-Strategy.md) - Development roadmap

## Project Status

**Current Version:** 0.0.1 (Pre-Alpha)

**Status:** 🟢 Ready for Hito 4 (Optimization Pipeline)

**Completed Milestones:**
- ✅ **Hito 0:** Technical validation (DSPy, LangGraph, Persistence)
- ✅ **Hito 1:** Project setup and architecture
- ✅ **Hito 2:** Core interfaces and state management
- ✅ **Hito 3:** SoniDU - DSPy module base

**Next Up:**
- 🚧 **Hito 4:** DSPy optimization pipeline (MIPROv2)

See [Implementation Strategy](docs/strategy/Implementation-Strategy.md) for detailed roadmap.

## Code Quality

- **Coverage:** 98% (exceeds 85% target) 🎯
- **Linting:** ✅ Ruff passes
- **Type Checking:** ✅ Mypy passes
- **Tests:** 28/28 passing

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- [DSPy](https://github.com/stanfordnlp/dspy) - For automatic prompt optimization
- [LangGraph](https://github.com/langchain-ai/langgraph) - For dialogue management
- [FastAPI](https://fastapi.tiangolo.com/) - For the API framework

---

**Built with ❤️ by the Soni Framework Contributors**
