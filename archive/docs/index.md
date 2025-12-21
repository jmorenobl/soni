# 🤖 Soni Framework Documentation

Welcome to the Soni Framework documentation! Soni is an open-source conversational AI framework that combines the power of DSPy for prompt optimization with LangGraph for robust dialogue management.

## What is Soni?

Soni is a modern framework for building task-oriented dialogue systems. It provides:

- **Declarative Configuration** - Define dialogue flows in YAML without writing code
- **Automatic Optimization** - Use DSPy to optimize NLU prompts with your data
- **Stateful Conversations** - Built on LangGraph for reliable, persistent dialogue management
- **Production Ready** - Async-first architecture with streaming support

## The Three Laws of Soni

1. **Declarative First**: Define behavior, not implementation
2. **Optimizable**: Learn from data through DSPy optimization
3. **No Black Boxes**: Full transparency and explainability

*Inspired by Asimov's vision of intelligent, helpful AI*

## Quick Start

Get started with Soni in 5 minutes:

```bash
# Install dependencies
uv sync

# Install the package
uv pip install -e .

# Set API key
export OPENAI_API_KEY="your-api-key-here"

# Run the example
uv run soni server --config examples/flight_booking/soni.yaml
```

See the [Quickstart Guide](quickstart.md) for detailed instructions.

## Documentation Structure

### Getting Started
- [Quickstart Guide](quickstart.md) - Get up and running in 5 minutes
- [Architecture Overview](architecture.md) - Understand how Soni works
- [Publishing to TestPyPI](publishing.md) - How to publish the package to TestPyPI

### Architecture & Design
- [Architecture Guide](architecture.md) - System architecture and components
- [ADR-001: Framework Architecture](adr/ADR-001-Soni-Framework-Architecture.md) - Detailed architecture decisions
- [ADR-001: Viability Analysis](adr/ADR-001-Viability-Analysis.md) - Framework viability assessment
- [ADR-002: Technical Validation](adr/ADR-002-Technical-Validation-Results.md) - Validation results

### Examples
- [Flight Booking Example](../examples/flight_booking/README.md) - Complete example application

### Releases
- [v0.1.0 Release Notes](releases/v0.1.0-release-notes.md) - Initial release

### Validation Reports
- [E2E Validation Report](validation/e2e-validation-report.md) - End-to-end validation
- [Runtime Validation](validation/runtime-validation.md) - Runtime system validation
- [Runtime API Validation](validation/runtime-api-validation.md) - API validation
- [Final Validation Report](validation/final-validation-report.md) - Comprehensive validation

## Key Features

- 🤖 **Prompt Optimization** - Uses DSPy's MIPROv2 to optimize NLU prompts
- 🔄 **Stateful Dialogue Management** - Built on LangGraph for reliable conversation flows
- 📝 **YAML-Based Configuration** - Declarative DSL for defining dialogue flows
- ⚡ **Async-First Architecture** - High-performance async/await throughout
- 🎯 **Zero-Leakage Design** - Technical details don't leak into configuration
- 📊 **Streaming Support** - Real-time token streaming with Server-Sent Events

## Requirements

- Python 3.11+
- OpenAI API key (or other supported LLM provider)

## Why "Soni"?

The name **Soni** is inspired by **Sonny**, the remarkable robot from Isaac Asimov's classic story collection "I, Robot". Like Sonny, who was special among robots—capable of learning, reasoning, and continuously optimizing his behavior—Soni represents a framework that learns and improves itself through prompt optimization.

Just as Sonny questioned and refined his own programming, Soni uses DSPy to optimize conversational AI systems through manual optimization runs, making them smarter with each optimization cycle. The framework embodies Asimov's vision of intelligent, helpful AI that can be improved to better serve its purpose.

*"The Three Laws of Robotics are built into the very foundation of Soni's architecture: to assist, to optimize, and to improve—all while maintaining transparency and control."*

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](../LICENSE) file for details.

---

**Built with ❤️ by the Soni Framework Contributors**
