# Soni v2 - Milestone 4: CommandGenerator (NLU)

**Status**: Ready for Review  
**Date**: 2025-12-21  
**Type**: Design Document  
**Depends On**: M0, M1, M2, M3
**Reference**: `archive/v1/src/soni/du/modules.py`, `archive/v1/src/soni/du/base.py`

---

## 1. Objective

Add NLU (Natural Language Understanding) via DSPy:
- Intent detection → `StartFlow` command
- Slot extraction → `SetSlot` command
- Two-pass architecture for efficiency

---

## 2. User Story

```
User: "I want to check my balance"
→ SoniDU detects: StartFlow("check_balance")
→ Flow starts automatically
Bot: "Your balance is $1,234.56"
```

---

## 3. Key Concepts

### 3.1 SoniDU (DSPy Module)

```python
class SoniDU(dspy.Module):
    """Dialogue Understanding module."""
    
    def __init__(self):
        self.predictor = dspy.Predict(DUSignature)
    
    def forward(self, message: str, context: DialogueContext) -> NLUOutput:
        result = self.predictor(message=message, context=context)
        return NLUOutput(commands=parse_commands(result.commands))
```

### 3.2 Two-Pass Architecture

1. **Pass 1**: Intent detection (SoniDU)
   - Input: message + available flows
   - Output: StartFlow, ChitChat, Cancel, etc.

2. **Pass 2**: Slot extraction (SlotExtractor)
   - Only if StartFlow detected
   - Input: message + flow slot definitions
   - Output: SetSlot commands

### 3.3 Flow Retrieval (Context Optimization)

Only include relevant flows in LLM context:
- Active flow always included
- Related flows based on embedding similarity (future)
- Limit to top N flows for token efficiency

---

## 4. Legacy Code Reference

### 4.1 OptimizableDSPyModule (REUSE)

**Source**: `archive/v1/src/soni/du/base.py`

> [!IMPORTANT]
> MUST preserve auto-loading pattern for `scripts/generate_baseline_optimization.py` compatibility:
> - `optimized_files` class variable with priority list
> - `create_with_best_model()` class method
> - `_load_best_optimization()` to search `du/optimized/` directory

```python
# Key patterns to preserve:
class OptimizableDSPyModule(dspy.Module):
    optimized_files: ClassVar[list[str]] = []
    
    @classmethod
    def create_with_best_model(cls) -> Self:
        instance = cls()
        instance._load_best_optimization()
        return instance
    
    def _load_best_optimization(self) -> bool:
        base_path = Path(__file__).parent / "optimized"
        for filename in self.optimized_files:
            if (base_path / filename).exists():
                self.load(str(base_path / filename))
                return True
        return False
```

### 4.2 NLUService (ADAPT)

**Source**: `archive/v1/src/soni/du/service.py`

```python
# Keep: Two-pass pattern
# Keep: Command parsing
```

### 4.3 Commands (REUSE)

**Source**: `archive/v1/src/soni/core/commands.py`

```python
# Keep: Pydantic command models
# Keep: StartFlow, SetSlot, ChitChat, CancelFlow
```

---

## 5. New Files

### 5.1 core/commands.py

```python
"""Command types from NLU."""

from pydantic import BaseModel


class StartFlow(BaseModel):
    """Start a new flow."""
    type: str = "start_flow"
    flow_name: str
    confidence: float = 1.0


class SetSlot(BaseModel):
    """Set a slot value."""
    type: str = "set_slot"
    slot: str
    value: Any
    confidence: float = 1.0


class ChitChat(BaseModel):
    """Off-topic message."""
    type: str = "chitchat"
    message: str


class CancelFlow(BaseModel):
    """Cancel current flow."""
    type: str = "cancel_flow"


Command = StartFlow | SetSlot | ChitChat | CancelFlow
```

### 5.2 du/signatures.py

```python
"""DSPy signatures for NLU."""

import dspy
from soni.du.models import DialogueContext, NLUOutput


class ExtractCommands(dspy.Signature):
    """Extract intent commands from user message in conversation context."""
    
    user_message: str = dspy.InputField(desc="User message")
    context: DialogueContext = dspy.InputField(desc="Conversation context")
    history: dspy.History = dspy.InputField(desc="Conversation history")
    
    result: NLUOutput = dspy.OutputField(desc="Extracted commands with confidence")
```

### 5.3 du/modules.py (SoniDU)

```python
"""SoniDU - Dialogue Understanding module.

Follows DSPy pattern:
- aforward(): Async runtime implementation
- forward(): Sync implementation for optimization
- module.acall(): Runtime invocation
- module(): Optimization invocation
"""

import dspy
from soni.du.base import OptimizableDSPyModule, safe_extract_result
from soni.du.models import DialogueContext, NLUOutput
from soni.du.signatures import ExtractCommands


class SoniDU(OptimizableDSPyModule):
    """DSPy module for intent detection.
    
    Usage:
        # Runtime (async)
        result = await du.acall(message, context, history)
        
        # Optimization (sync)
        result = du(message, context, history)
    """
    
    # Priority-ordered optimization files
    optimized_files = ["baseline_v1_miprov2.json", "baseline_v1.json"]
    default_use_cot = True
    
    def _create_extractor(self, use_cot: bool) -> dspy.Module:
        if use_cot:
            return dspy.ChainOfThought(ExtractCommands)
        return dspy.Predict(ExtractCommands)
    
    async def aforward(
        self,
        user_message: str,
        context: DialogueContext,
        history: list[dict[str, str]] | None = None,
    ) -> NLUOutput:
        """Async runtime implementation."""
        history_obj = dspy.History(messages=history or [])
        
        result = await self.extractor.acall(
            user_message=user_message,
            context=context,
            history=history_obj,
        )
        return safe_extract_result(
            result.result, NLUOutput,
            default_factory=lambda: NLUOutput(commands=[], confidence=0.0),
            context="NLU extraction",
        )
    
    def forward(
        self,
        user_message: str,
        context: DialogueContext,
        history: list[dict[str, str]] | None = None,
    ) -> NLUOutput:
        """Sync version for DSPy optimization."""
        history_obj = dspy.History(messages=history or [])
        result = self.extractor(
            user_message=user_message,
            context=context,
            history=history_obj,
        )
        return safe_extract_result(
            result.result, NLUOutput,
            default_factory=lambda: NLUOutput(commands=[], confidence=0.0),
            context="NLU forward pass",
        )
```

### 5.4 dm/nodes/understand.py

```python
"""Understand node for NLU processing."""

async def understand_node(state, runtime):
    """Process user message through NLU."""
    du = runtime.context.du
    config = runtime.context.config
    
    # Build context
    context = {
        "available_flows": _format_flows(config.flows),
        "active_flow": _get_active_flow(state),
        "expected_slot": state.get("waiting_for_slot"),
    }
    
    # Get commands
    commands = await du.acall(state["user_message"], context)
    
    # Serialize for state
    serialized = [c.model_dump() for c in commands]
    
    return {"commands": serialized}
```

### 5.5 dm/builder.py (Update)

```python
def build_orchestrator():
    builder = StateGraph(DialogueState)
    
    builder.add_node("understand", understand_node)  # NEW
    builder.add_node("execute", execute_node)
    builder.add_node("respond", respond_node)
    
    builder.set_entry_point("understand")
    builder.add_edge("understand", "execute")
    builder.add_edge("execute", "respond")
    builder.add_edge("respond", END)
    
    return builder.compile()
```

---

## 6. TDD Tests (AAA Format)

### 6.1 Integration Test

```python
# tests/integration/test_m4_nlu.py
@pytest.mark.asyncio
async def test_nlu_triggers_flow():
    """NLU detects intent and starts flow."""
    # Arrange
    config = SoniConfig(
        flows={
            "check_balance": FlowConfig(
                description="Check account balance",
                steps=[SayStepConfig(step="show", message="Your balance is $100")]
            )
        }
    )
    
    # Act
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("what's my balance?")
    
    # Assert
    assert "balance" in response.lower()
```

### 6.2 Unit Tests (AAA Format)

```python
# tests/unit/du/test_soni_du.py
@pytest.mark.asyncio
async def test_du_returns_start_flow():
    """DU returns StartFlow command for matching intent."""
    # Arrange
    du = SoniDU(use_cot=False)  # Faster for tests
    context = DialogueContext(
        available_flows="check_balance: Check account balance",
        active_flow="",
        expected_slot="",
    )
    
    # Act
    result = await du.acall("what's my balance?", context)
    
    # Assert
    assert len(result.commands) > 0
    assert result.commands[0].type == "start_flow"

@pytest.mark.asyncio
async def test_du_returns_chitchat_for_offtopic():
    """DU returns ChitChat for off-topic messages."""
    ...
```

---

## 7. DSPy Configuration

```python
# In runtime/loop.py or config
import dspy

# Configure LM (user provides API key)
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)
```

---

## 8. Success Criteria

- [ ] NLU detects `StartFlow` from user message
- [ ] Flow triggers automatically
- [ ] DSPy module works with async
- [ ] Off-topic messages return ChitChat

---

## 9. Implementation Order

1. Write tests with mocked LM (RED)
2. Create `core/commands.py`
3. Create `du/signatures.py`
4. Create `du/base.py` (SoniDU)
5. Create `dm/nodes/understand.py`
6. Update `dm/builder.py`
7. Update `runtime/loop.py` with DSPy config
8. Run tests (GREEN)

---

## Next: M5 (Action + Validation)
