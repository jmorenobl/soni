# Soni vs Rasa CALM (2025): Competitive Analysis

> **Disclaimer**: This analysis is exhaustive, honest, and non-complacent. It focuses on functional parity and differentiation, assuming an "LLM-native" goal.

## Executive Summary

**Soni** is an **LLM-Native Dialogue Framework** with recursive flow control and DSPy optimization.
**Rasa CALM** is the **Market Leader** with a mature ecosystem and hybrid NLU approach.

Soni has achieved **functional parity** with Rasa CALM's core dialogue management capabilities while offering a **lighter, more modern architecture**. The key differentiators are now in ecosystem maturity (Rasa's advantage) vs. LLM-native design (Soni's advantage).

---

## Feature Comparison

### 1. Orchestration Loop

| Aspect | Rasa CALM | Soni |
|--------|-----------|------|
| **Architecture** | Recursive Dialogue State Machine | Recursive LangGraph with Auto-Resume |
| **Flow Interruption** | Native stack-based | Native stack-based |
| **Auto-Resume** | Built-in | Built-in (`ResumeNode` + conditional routing) |
| **Implementation** | Proprietary engine | LangGraph (open standard) |

**Status**: **Parity**

Soni implements the same recursive loop pattern:
1. **User Turn**: `RuntimeLoop` processes message through NLU.
2. **Execution**: Graph runs `understand` -> `execute` -> flow subgraph -> `resume`.
3. **Auto-Evaluation**: `route_resume()` checks: "Is stack empty? Is system waiting for input?"
4. **Loop**: If stack has flows and not waiting, routes back to `execute`.
5. **Stop**: Only when `waiting_input` state or empty stack.

```python
# src/soni/dm/builder.py - Auto-Resume Loop
def route_resume(state: DialogueState) -> str:
    if state.get("flow_state") == "waiting_input":
        return "end"
    if state.get("flow_stack"):
        return "loop"  # Resume parent flow
    return "end"
```

**Verified by**: `tests/integration/test_auto_resume.py`

---

### 2. Conditional Business Logic

| Aspect | Rasa CALM | Soni |
|--------|-----------|------|
| **Branching** | `if/else` in YAML | `branch` step with slot-based routing |
| **Loops** | `while` conditions | `while` step with expression evaluation |
| **Expression Syntax** | Custom DSL | Python-like (`age > 18 AND status == 'approved'`) |
| **Visibility** | Declarative YAML | Declarative YAML |

**Status**: **Parity**

Soni supports declarative branching in YAML:

```yaml
# Branch based on slot value
- branch:
    slot: account_type
    cases:
      gold: vip_service_flow
      regular: standard_service_flow
    default: standard_service_flow

# While loop with condition
- while:
    condition: "retry_count < 3"
    do:
      - action: attempt_transaction
```

**Implementation**:
- `BranchNode`: `src/soni/compiler/nodes/branch.py`
- `WhileNode`: `src/soni/compiler/nodes/while_loop.py`
- Expression Evaluator: `src/soni/core/expression.py`

**Verified by**: `tests/unit/compiler/test_node_factories.py`

---

### 3. NLU Technology

| Aspect | Rasa CALM | Soni |
|--------|-----------|------|
| **Architecture** | Hybrid (Classifier + LLM fallback) | Pure LLM (DSPy) |
| **Intent Classification** | Trained classifiers | Zero-shot LLM |
| **Entity Extraction** | Duckling + CRF + LLM | LLM with Pydantic validation |
| **Optimization** | Manual tuning | **Automatic (DSPy optimizers)** |
| **Few-shot Learning** | Limited | Native DSPy support |

**Status**: **Soni Advantage** (Modern approach)

Soni's LLM-native NLU offers:
- **Zero training data required** for new intents
- **Automatic prompt optimization** via DSPy
- **Structured output validation** with Pydantic models
- **Contextual understanding** without feature engineering

```python
# src/soni/du/modules.py - DSPy-powered NLU
class SoniDU(dspy.Module):
    def __init__(self):
        self.understand = dspy.ChainOfThought(UnderstandSignature)

    def forward(self, context: DialogueContext) -> NLUOutput:
        return self.understand(context=context)
```

**Trade-off**: Rasa's Duckling provides robust date/currency extraction out-of-box. Soni relies on LLM capability (adequate for most cases, but less deterministic).

---

### 4. Scope & State Management

| Aspect | Rasa CALM | Soni |
|--------|-----------|------|
| **Flow Scope** | Variables die with flow | Variables scoped by `flow_id` |
| **Conversation Scope** | Persistent slots | `metadata`, `messages` persist |
| **Data Passing** | Explicit slot mapping | `outputs` dict + slot inheritance |
| **Isolation** | Built-in | Built-in via `flow_id` namespacing |

**Status**: **Parity**

Soni's scope architecture:

```python
# Flow-scoped: dies when flow is popped
state["flow_slots"][flow_id][slot_name] = value

# Conversation-scoped: persists across flows
state["metadata"]["user_id"] = "12345"
state["messages"]  # Full conversation history
```

**Implementation**: `src/soni/flow/manager.py` enforces scope via `flow_id`-based access.

---

### 5. Ecosystem & Tooling

| Aspect | Rasa CALM | Soni |
|--------|-----------|------|
| **Maturity** | 7+ years | Early stage |
| **Community** | Large, established | Growing |
| **Pre-built Integrations** | Extensive (Slack, Teams, etc.) | Basic (FastAPI server) |
| **Visual Editor** | Rasa X/Studio | None |
| **Enterprise Support** | Available | Not available |
| **Documentation** | Comprehensive | In progress |

**Status**: **Rasa Advantage** (Ecosystem maturity)

This is the primary gap. Rasa's ecosystem includes:
- Production-grade connectors for major platforms
- Visual flow editor (Rasa Studio)
- Enterprise support and SLAs
- Years of battle-tested deployments

---

## Architectural Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│                        RASA CALM                                │
├─────────────────────────────────────────────────────────────────┤
│  User Input → NLU Pipeline → Policy Engine → Action Server     │
│                    ↓              ↓                             │
│              Classifiers    Proprietary DM                      │
│              + LLM fallback  (closed source)                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          SONI                                   │
├─────────────────────────────────────────────────────────────────┤
│  User Input → SoniDU (DSPy) → LangGraph Orchestrator → Actions  │
│                    ↓                  ↓                         │
│              Pure LLM           Open Standard                   │
│              + Auto-optimize    (composable nodes)              │
└─────────────────────────────────────────────────────────────────┘
```

**Key Architectural Differences**:

1. **Open vs. Proprietary**: Soni uses LangGraph (open standard), Rasa uses proprietary DM.
2. **Training vs. Prompting**: Rasa requires training data, Soni uses zero-shot + optimization.
3. **Monolithic vs. Composable**: Soni's node-based architecture allows custom node injection.

---

## When to Choose Each

### Choose Rasa CALM when:
- You need enterprise support and SLAs
- You have existing Rasa infrastructure
- You require pre-built platform connectors
- You prefer visual flow editing
- You have large training datasets

### Choose Soni when:
- You want LLM-native, zero-training-data approach
- You need automatic prompt optimization (DSPy)
- You prefer open standards (LangGraph)
- You want lightweight, Python-native framework
- You're building new conversational AI from scratch

---

## Summary Table

| Feature | Rasa CALM | Soni | Winner |
|---------|-----------|------|--------|
| **Auto-Resume Loop** | Yes | Yes | Tie |
| **Conditional Logic** | Yes | Yes | Tie |
| **NLU Flexibility** | Hybrid | Pure LLM | **Soni** |
| **Prompt Optimization** | Manual | Automatic (DSPy) | **Soni** |
| **Entity Extraction** | Duckling + CRF | LLM + Pydantic | **Rasa** |
| **Scope Management** | Yes | Yes | Tie |
| **Ecosystem Maturity** | Extensive | Early | **Rasa** |
| **Open Architecture** | Partial | Full (LangGraph) | **Soni** |
| **Enterprise Ready** | Yes | Not yet | **Rasa** |

---

## Conclusion

Soni has closed the **functional gaps** that previously made it a "Linear Step Execution Engine." It now implements:

- **Recursive Auto-Resume Loop** (the critical differentiator)
- **Declarative Conditional Logic** (branch/while nodes)
- **Proper Scope Management** (flow_id isolation)

The competitive landscape is now:

- **Rasa CALM**: Market leader with ecosystem maturity and enterprise features
- **Soni**: Modern challenger with LLM-native design and automatic optimization

For teams building new conversational AI systems without legacy Rasa infrastructure, Soni offers a **lighter, more modern alternative** with equivalent dialogue management capabilities and superior NLU flexibility.

---

## Remaining Opportunities

1. **Domain-Specific Extractors**: Add structured extractors for dates, currencies, addresses (or integrate with existing libraries).

2. **Platform Connectors**: Build integrations for Slack, Teams, WhatsApp, etc.

3. **Visual Editor**: Consider a web-based flow editor for non-technical users.

4. **Production Hardening**: Add telemetry, monitoring, and deployment guides.

---

*Last Updated: December 2025*
*Based on: Soni commit `0413718` and Rasa CALM 3.x documentation*
