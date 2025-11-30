# API Reference

Welcome to the Soni Framework API Reference. This documentation is automatically generated from the source code docstrings.

## Quick Navigation

- [Core Modules](core/interfaces.md) - Interfaces, state, configuration, errors, scope, security
- [Dialogue Understanding](du.md) - DSPy-based NLU
- [Dialogue Management](dm.md) - LangGraph integration
- [Compiler](compiler.md) - YAML to Graph compilation
- [Actions](actions.md) - Action registry system
- [Validation](validation.md) - Validator registry system
- [Runtime](runtime.md) - Runtime loop and message processing
- [Server](server.md) - FastAPI endpoints
- [CLI](cli.md) - Command-line interface
- [Utils](utils.md) - Utility functions

## Getting Started

Start with [RuntimeLoop](runtime.md#soni.runtime.runtime.RuntimeLoop) for the main entry point.

## Documentation Style

All API documentation is automatically generated from Google-style docstrings in the source code. This ensures that the documentation stays synchronized with the codebase.

## Module Organization

The API is organized into the following main modules:

### Core (`soni.core`)
Core interfaces, state management, configuration, and error handling.

### Dialogue Understanding (`soni.du`)
DSPy-based modules for natural language understanding, including intent recognition and slot extraction.

### Dialogue Management (`soni.dm`)
LangGraph-based dialogue management, including graph construction, node factories, and persistence.

### Compiler (`soni.compiler`)
YAML to Graph compiler that transforms declarative flow definitions into executable state graphs.

### Actions (`soni.actions`)
Action registry system for registering and executing custom actions.

### Validation (`soni.validation`)
Validator registry system for slot and entity validation.

### Runtime (`soni.runtime`)
Main runtime loop for processing conversations, managing state, and handling streaming.

### Server (`soni.server`)
FastAPI endpoints for HTTP and WebSocket communication.

### CLI (`soni.cli`)
Command-line interface for running the server and optimizing modules.

### Utils (`soni.utils`)
Utility functions for hashing and other common operations.
