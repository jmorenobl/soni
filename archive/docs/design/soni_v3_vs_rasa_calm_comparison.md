# Soni v3.0 vs RASA CALM: Updated Analysis

> **Date**: 2025-12-15 (after v3.0 rewrite)
> **Previous Analysis**: [soni_vs_rasa_calm_analysis.md](file:///Users/jorge/Projects/Playground/soni/docs/design/soni_vs_rasa_calm_analysis.md)

## Executive Summary

**v3.0 addresses the most critical gaps identified in the original analysis.** The architecture is now much closer to RASA CALM's design philosophy.

| Gap | v2.0 Status | v3.0 Status | Change |
|-----|-------------|-------------|--------|
| **Command Abstraction** | ❌ Missing | ✅ Implemented | 🟢 Fixed |
| **Deterministic DM** | ❌ LLM-driven | ✅ Subgraph-based | 🟢 Fixed |
| **Conversation Patterns** | ❌ Ad-hoc | 🟡 Partial | 🟡 Improved |
| **Process Calling** | ❌ Implicit | ✅ Explicit steps | 🟢 Fixed |
| **Entity/Slot Separation** | ❌ Coupled | 🟡 Same | ⚪ Unchanged |

---

## Gap #1: Command Abstraction Layer ✅ FIXED

### Before (v2.0) ❌
```python
# LLM produced MessageType that controlled routing
class NLUOutput:
    message_type: MessageType  # LLM decides what DM does
```

### After (v3.0) ✅
```python
# NLU now produces explicit Commands
class Command(BaseModel):
    """Base command from DU to DM."""

class StartFlow(Command):
    flow_name: str
    slots: dict[str, Any] = {}

class SetSlot(Command):
    slot_name: str
    value: Any

class CancelFlow(Command): ...
class AffirmConfirmation(Command): ...
class DenyConfirmation(Command): ...
```

**Key improvement**: The LLM's role is now constrained to understanding → Commands. The DM executes Commands deterministically in `execute_node`.

---

## Gap #2: Deterministic Dialogue Manager ✅ FIXED

### Before (v2.0) ❌
```
Single monolithic graph with NLU-driven routing
→ Complex conditional edges
→ Message types controlling flow
→ State explosion
```

### After (v3.0) ✅
```
Orchestrator Graph + Flow Subgraphs
┌─────────────────────────────────────────────────────────┐
│  understand → execute → route → [flow_*] → respond      │
└────────────────────────────────────────────────────────┘
                             ↓
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
     ┌──────────┐      ┌──────────┐      ┌──────────┐
     │ flow_    │      │ flow_    │      │ flow_    │
     │ graph_1  │      │ graph_2  │      │ graph_3  │
     └──────────┘      └──────────┘      └──────────┘
```

**Key improvement**: Each flow is a compiled subgraph. Routing is deterministic based on flow stack state, not NLU classification.

---

## Gap #3: Conversation Patterns 🟡 PARTIAL

### Status
- Branch/conditionals: ✅ Implemented (`type: branch`)
- Loops: ✅ Implemented (`type: while`)
- Jump support: ✅ Implemented (`jump_to`)
- Correction pattern: 🟡 Via Command
- Clarification pattern: 🟡 Via Command
- Human handoff: ❌ Not yet

**Remaining work**: Declarative YAML pattern registry.

---

## Gap #4: Process Calling ✅ FIXED

### Before (v2.0) ❌
Actions could be called from any node, no explicit sequencing.

### After (v3.0) ✅
```yaml
process:
  - step: collect_origin
    type: collect
    slot: origin
  - step: search
    type: action        # Explicit position
    call: search_flights
  - step: check_results
    type: branch        # Conditionals
    input: result_count
    cases:
      "0": no_flights
```

Actions are now explicit steps in the flow with clear sequencing.

---

## Gap #5: Entity/Slot Separation ⚪ UNCHANGED

Still coupled in NLU. Low priority - works well for current use cases.

---

## Architecture Comparison

| Aspect | RASA CALM | Soni v2.0 | Soni v3.0 |
|--------|-----------|-----------|-----------|
| **LLM Role** | Understanding only | Understanding + routing | Understanding only ✅ |
| **Command Layer** | Explicit | Missing | Explicit ✅ |
| **DM Type** | State machine | LangGraph (uncontrolled) | Subgraph per flow ✅ |
| **Flow Definition** | YAML declarative | YAML simple | YAML + conditionals ✅ |
| **Loops/Branches** | Native | Missing | Implemented ✅ |
| **Code Complexity** | Large | ~5,000 lines | ~3,000 lines ✅ |

---

## Metrics

| Metric | v2.0 | v3.0 | Change |
|--------|------|------|--------|
| DM routing lines | 800+ | ~200 | -75% |
| Handler nodes | 10+ | 4 | -60% |
| State transitions | Complex | Linear | Simplified |
| Total deleted | - | 4,000+ lines | Major cleanup |

---

## Remaining Gaps (Minor)

1. **Declarative Conversation Patterns** - YAML registry for correction/clarification/handoff
2. **Slot Validation in Subgraphs** - Currently simple, could be enhanced
3. **Multi-command support** - Single command per turn currently
4. **Human Handoff** - Not implemented yet

---

## Conclusion

**Soni v3.0 is now architecturally comparable to RASA CALM** in the areas that matter most:

- ✅ **Constrained LLM role** - Understanding only, Commands as output
- ✅ **Deterministic DM** - Subgraph execution, not NLU classification
- ✅ **Explicit process calling** - Actions as steps in flows
- ✅ **Declarative DSL** - Branch, while, jump_to support

The main remaining gap is the **declarative conversation pattern registry** (correction, handoff, etc.), which is a nice-to-have rather than a fundamental architecture issue.

**Overall Score: 8/10** (up from 4/10 in v2.0)
