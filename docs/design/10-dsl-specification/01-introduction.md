# Introduction & Design Principles

[← Back to Index](00-index.md)

---

## 1. Introduction

This document specifies the Domain Specific Language (DSL) for the Soni Framework. The DSL is designed to be **declarative**, **zero-leakage**, and **human-readable**, allowing the definition of complex conversational flows without exposing technical implementation details.

**Design Goals:**
- **Simplicity**: Business analysts can design flows without coding
- **Power**: Handle complex multi-turn, multi-flow conversations
- **Zero-Leakage**: No technical details (HTTP, regex, SQL) in YAML
- **Consistency**: Uniform syntax across all constructs

---

## 2. Design Principles

### 2.1 Zero-Leakage Architecture

The DSL strictly separates **Conversation Logic** (YAML) from **Technical Implementation** (Python).

| Layer | Defines | Examples |
|-------|---------|----------|
| **YAML** | *What* happens | Collect `destination`, call `search_flights`, branch on `status` |
| **Python** | *How* it happens | HTTP calls, database queries, regex validation |
| **Binding** | Semantic names | `validator: city_name`, `call: search_flights` |

### 2.2 State-Driven Execution

All steps read from and write to a unified state object. The state has two scopes:
- **Session State**: Persists across the entire session (e.g., `user_name`, `user_id`)
- **Flow State**: Scoped to the current flow instance, isolated from other flows

**Accessing State Variables:**

| Syntax | Scope | Example |
|--------|-------|---------|
| `variable` | Flow state (default) | `origin`, `selected_flight` |
| `session.variable` | Session state | `session.user_name`, `session.language` |
| `flow.variable` | Explicit flow state | `flow.origin` (same as `origin`) |

Flow variables are isolated between flows. Session variables are shared.

**State Lifecycle:**

| Event | Session State | Flow State |
|-------|---------------|------------|
| Session starts | Created empty | - |
| Flow starts | Unchanged | Created empty |
| `call_flow` | Unchanged | New flow state (parent paused) |
| Flow completes | Unchanged | Cleared (outputs copied to parent) |
| Flow cancelled | Unchanged | **Cleared** (data lost) |
| Session timeout | **Cleared** | Cleared |

**Important:** When a flow is cancelled (via `on_no` or user cancellation), all flow state is lost. To preserve data across flow cancellation, store it in `session.*` variables.

```yaml
# Preserve important data in session
- step: save_progress
  type: set
  values:
    session.last_origin: "{origin}"
    session.last_destination: "{destination}"
```

### 2.3 Declarative with Escape Hatches

The DSL is declarative by default but provides explicit control flow (`jump_to`) when needed.

---

[Next: Configuration →](02-configuration.md)
