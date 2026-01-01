# Soni Framework Documentation

**Generated:** 2026-01-01 (Updated from previous documentation)

Welcome to the comprehensive documentation for Soni Framework - an open-source conversational AI framework with automatic prompt optimization.

## 📊 Project Overview

- **Type:** Python Library/Framework (Monolithic)
- **Primary Language:** Python 3.11+
- **Architecture:** Hexagonal Architecture (Ports & Adapters)
- **Core Technologies:** DSPy + LangGraph
- **Status:** Alpha (v0.4.0 - Experimental)

## 🎯 Quick Reference

| Aspect | Details |
|--------|---------|
| **Tech Stack** | Python 3.11+, DSPy (NLU optimization), LangGraph (dialogue management), FastAPI (API), Typer (CLI) |
| **Entry Points** | `src/soni/cli/main.py` (CLI), `src/soni/server/main.py` (API Server) |
| **Architecture Pattern** | Hexagonal + Event-Driven + Declarative DSL |
| **Testing** | pytest + pytest-asyncio (>30% coverage, targeting >60%) |
| **Documentation Site** | MkDocs Material |

## 📚 Documentation Structure

The documentation is organized into four main sections:

### 🎓 [Tutorials](tutorials/quickstart.md)
Step-by-step lessons to get you started.
- **[Quickstart Guide](tutorials/quickstart.md)** - Get started in 5 minutes

### 🔧 [How-To Guides](how-to/index.md)
Recipes for solving specific problems.

### 📖 [Reference](reference/dsl-spec.md)
Technical descriptions and specifications.
- **[DSL Specification](reference/dsl-spec.md)** - YAML configuration reference

### 💡 [Explanation](explanation/architecture.md)
Background, concepts, and architectural decisions.
- **[Architecture Overview](explanation/architecture.md)** - High-level architecture concepts

## 🆕 Generated Brownfield Documentation

These documents were auto-generated from codebase analysis:

### Core Documentation

- **[Project Overview](project-overview.md)** - Technology stack summary and project metadata
- **[Architecture Documentation](architecture.md)** - Detailed architecture patterns, design principles, and component overview
- **[Source Tree Analysis](source-tree-analysis.md)** - Complete directory structure with annotations
- **[Development Guide](development-guide.md)** - Setup, testing, debugging, and deployment instructions

### Additional Documentation

- **[Architecture Overview (Original)](architecture_overview.md)** - Pre-existing architecture documentation
- **[AGENTS.md](../AGENTS.md)** - Agent instructions and implementation guidelines
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Contribution guidelines

## 📂 Existing Documentation

### Repository Documentation

- [README.md](../README.md) - Main project introduction
- [CHANGELOG.md](../CHANGELOG.md) - Version history and changes
- [CONTRIBUTING.md](../CONTRIBUTING.md) - How to contribute
- [AGENTS.md](../AGENTS.md) - Framework agent patterns

### Example Documentation

- [Banking Example README](../examples/banking/README.md) - Complete banking assistant example

### Test Documentation

- [E2E Test README](../tests/e2e/README.md) - End-to-end testing guide

### Wiki (Internal/Technical)

- [Wiki Home](../wiki/Home.md) - Internal wiki index
- [Roadmap](../wiki/Roadmap.md) - Product roadmap
- [Release Plan](../wiki/release-plan.md) - Release planning
- **Architecture Decision Records (ADRs):**
  - [ADR Template](../wiki/adr/000-template.md)
- **Product Requirements (PRDs):**
  - [PRD Template](../wiki/prd/000-template.md)
- **Strategic Planning:**
  - [Event Architecture Strategy](../wiki/strategy/01-event-architecture.md)
  - [CLI Evolution](../wiki/strategy/02-cli-evolution.md)
  - [Core & Stability](../wiki/strategy/03-core-and-stability.md)
  - [Enhanced Realism](../wiki/strategy/04-enhanced-realism.md)
  - [TUI Implementation](../wiki/strategy/05-tui-implementation.md)
  - [RAG Integration](../wiki/strategy/06-rag-integration.md)
  - [Optimization Pipeline](../wiki/strategy/07-optimization-pipeline.md)

## 🚀 Getting Started

### For Users

1. **Start Here:** [Quickstart Guide](tutorials/quickstart.md)
2. **Understand the Framework:** [Architecture Documentation](architecture.md)
3. **Explore Examples:** [Banking Example](../examples/banking/README.md)
4. **API Reference:** [DSL Specification](reference/dsl-spec.md)

### For Developers

1. **Setup:** [Development Guide](development-guide.md) - Environment setup and local development
2. **Architecture:** [Architecture Documentation](architecture.md) - Design patterns and component overview
3. **Source Code:** [Source Tree Analysis](source-tree-analysis.md) - Navigate the codebase
4. **Contributing:** [CONTRIBUTING.md](../CONTRIBUTING.md) - Code style and PR process
5. **Testing:** [Development Guide - Testing](development-guide.md#testing-approach)

### For Contributors

1. **Contribution Guide:** [CONTRIBUTING.md](../CONTRIBUTING.md)
2. **Code Standards:** [Development Guide - Code Quality](development-guide.md#code-quality-commands)

3. **Architecture Guidelines:** [Agent Instructions](../AGENTS.md)
4. **Strategic Planning:** [Wiki Strategies](../wiki/strategy/)

## 🔍 Quick Navigation

### By Task

| What do you want to do? | Go here |
|--------------------------|---------|
| Install and run Soni | [Quickstart Guide](tutorials/quickstart.md) |
| Understand the architecture | [Architecture Documentation](architecture.md) |
| Set up development environment | [Development Guide](development-guide.md) |
| Navigate the source code | [Source Tree Analysis](source-tree-analysis.md) |
| Run tests | [Development Guide - Testing](development-guide.md#testing-approach) |
| Configure YAML flows | [DSL Specification](reference/dsl-spec.md) |
| Deploy to production | [Development Guide - Deployment](development-guide.md#deployment) |
| Optimize prompts | [Development Guide - Optimization](development-guide.md#optimization) |
| Contribute code | [CONTRIBUTING.md](../CONTRIBUTING.md) |

### By Role

**End Users:** Start with [Quickstart](tutorials/quickstart.md) → [DSL Spec](reference/dsl-spec.md)
**Developers:** Start with [Development Guide](development-guide.md) → [Architecture](architecture.md) → [Source Tree](source-tree-analysis.md)
**Contributors:** Start with [CONTRIBUTING.md](../CONTRIBUTING.md) → [AGENTS.md](../AGENTS.md)
**Architects:** Start with [Architecture](architecture.md) → [Wiki Strategies](../wiki/strategy/)

## 🎯 AI-Assisted Development Guide

This documentation was specifically designed for brownfield PRD workflows with AI assistants:

### When Planning New Features

1. **Review Architecture:** [Architecture Documentation](architecture.md) to understand design patterns
2. **Check Components:** [Source Tree Analysis](source-tree-analysis.md) to identify reusable components
3. **Review Constraints:** [AGENTS.md](../AGENTS.md) for framework design principles
4. **Check Roadmap:** [Wiki Strategies](../wiki/strategy/) for alignment with future plans

### When Implementing

1. **Follow Setup:** [Development Guide](development-guide.md) for environment setup
2. **Use Patterns:** [Architecture](architecture.md) for consistent design patterns
3. **Write Tests:** [Development Guide - Testing](development-guide.md#testing-approach)
4. **Check Quality:** [CONTRIBUTING.md](../CONTRIBUTING.md) for code standards

### When Debugging

1. **Enable Debug Logging:** [Development Guide - Debugging](development-guide.md#debugging)
2. **Review State:** Inspect DialogueState and FlowContext
3. **Check Tests:** Run relevant test suites
4. **Review Architecture:** Ensure alignment with hexagonal architecture

## 📞 Getting Help

- **Documentation Issues:** Open issue on [GitHub](https://github.com/jmorenobl/soni/issues)
- **Feature Requests:** Check [Roadmap](../wiki/Roadmap.md) first, then open issue
- **Bug Reports:** Use GitHub Issues with detailed reproduction steps
- **Questions:** Check existing docs, then open a discussion

---

> 🛠️ **Contributors**: Check the [project wiki](../wiki/) for roadmaps, ADRs, and architectural decisions.

**Last Updated:** 2026-01-01
**Documentation Version:** 1.0 (Brownfield Analysis + Original Docs)
