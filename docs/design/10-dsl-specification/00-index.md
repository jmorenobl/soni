# DSL Specification - Soni Framework v1.0

**Document Version**: 1.5
**Status**: Design Specification
**Last Updated**: 2024-12-05

---

## Overview

This specification defines the Domain Specific Language (DSL) for the Soni Framework. The DSL is designed to be **declarative**, **zero-leakage**, and **human-readable**, allowing the definition of complex conversational flows without exposing technical implementation details.

**Design Goals:**
- **Simplicity**: Business analysts can design flows without coding
- **Power**: Handle complex multi-turn, multi-flow conversations
- **Zero-Leakage**: No technical details (HTTP, regex, SQL) in YAML
- **Consistency**: Uniform syntax across all constructs

---

## Table of Contents

| # | Document | Description |
|---|----------|-------------|
| 1 | [Introduction](01-introduction.md) | Design principles, zero-leakage architecture, state management |
| 2 | [Configuration](02-configuration.md) | Settings, responses, i18n, rich UI components |
| 3 | [Data Model](03-data-model.md) | Slots (data definitions) and Actions (contracts) |
| 4 | [Flows](04-flows.md) | Flow structure, triggers, special flows, inputs/outputs |
| 5 | [Step Types](05-step-types.md) | All step types: collect, action, branch, say, confirm, generate, call_flow, set, handoff |
| 6 | [Patterns](06-patterns.md) | Runtime conversational patterns: corrections, digressions, interruptions |
| 7 | [Control & Errors](07-control-error.md) | Control flow, jumps, branching, loops, error handling |
| 8 | [Examples](08-examples.md) | Complete flight booking example |
| 9 | [Reference](09-reference.md) | Python implementation, appendices, future work |

---

## Quick Reference

### Configuration Structure

```yaml
version: "1.0"

settings:
  # Runtime configuration
  ...

responses:
  # System message templates
  ...

slots:
  # Data definitions
  ...

actions:
  # Action contracts
  ...

flows:
  # Conversation logic
  ...
```

### Step Types Summary

| Type | Purpose | Waits for User | Modifies State |
|------|---------|----------------|----------------|
| `collect` | Gather slot value | Yes | Yes (slot) |
| `action` | Execute business logic | No | Yes (outputs) |
| `branch` | Conditional routing | No | No |
| `say` | Send message | No | No |
| `confirm` | Request confirmation | Yes | Yes* |
| `generate` | LLM response | No | Optional |
| `call_flow` | Invoke sub-flow | Yes (indirect) | Yes (outputs) |
| `set` | Set variables | No | Yes |
| `handoff` | Transfer to human | Yes | No |

*`confirm` modifies state when user makes corrections during confirmation.

### Reserved Keywords

- `end` - End the flow normally
- `error` - End the flow with error state
- `continue` - Go to next sequential step
- `cancel_flow` - Cancel current flow and return to parent/idle

---

## See Also

- [Architecture Overview](../02-architecture.md)
- [State Machine](../04-state-machine.md)
- [Flow Management](../07-flow-management.md)
- [LangGraph Integration](../08-langgraph-integration.md)
