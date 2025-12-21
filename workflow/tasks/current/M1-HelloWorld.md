# Soni v2 - Milestone 1: Hello World (Say Only)

**Status**: Ready for Review  
**Date**: 2025-12-21  
**Type**: Design Document  
**Depends On**: M0

---

## 1. Objective

Create the minimal working system: a flow with a single `say` step that outputs a message.

**Features:**
- No NLU, no interrupt, no flow stack - just message in → response out
- **DSL versioning** for future compatibility

---

## 2. User Story

```
User: "hi"
Bot: "Hello, World!"
```

---

## 3. Architecture

```
RuntimeLoop.process_message("hi")
  → graph.ainvoke({user_message: "hi", ...})
    → execute_node(state)
      → subgraph.ainvoke(state)
        → say_node() → {response: "Hello, World!"}
      ← {response: "Hello, World!"}
  → return "Hello, World!"
```

---

## 4. Legacy Code Reference

### 4.1 Config Models (REUSE with simplification)

**Source**: `archive/v1/src/soni/config/models.py`, `archive/v1/src/soni/config/steps.py`

```python
# Keep: Pydantic discriminated unions
StepConfig = Annotated[
    SayStepConfig | CollectStepConfig | ...,
    Field(discriminator="type"),
]
```

**Simplify for M1**: Only `SayStepConfig` needed initially.

### 4.2 SayNodeFactory (REUSE with simplification)

**Source**: `archive/v1/src/soni/compiler/nodes/say.py`

```python
# Keep: Factory pattern
class SayNodeFactory:
    def create(self, step: SayStepConfig, ...) -> NodeFunction:
        async def say_node(state, runtime):
            # ...
            return {"response": content}
        return say_node
```

**Simplify for M1**: No idempotency, no pending_responses queue, no slot substitution.

---

## 5. New Files

### 5.1 core/types.py (Minimal)

```python
"""Core type definitions for Soni v2 M1."""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from langgraph.types import Command


# =============================================================================
# REDUCERS - Specialized for proper interrupt/resume handling
# =============================================================================

def _last_value_str(current: str | None, new: str | None) -> str | None:
    """Reducer: last value wins for strings."""
    return new


def _last_value_any(current: Any, new: Any) -> Any:
    """Reducer: last value wins (generic)."""
    return new


class DialogueState(TypedDict):
    """Minimal state for M1."""
    user_message: Annotated[str | None, _last_value_str]
    messages: Annotated[list[AnyMessage], add_messages]
    response: Annotated[str | None, _last_value_str]


# =============================================================================
# NODE FUNCTION TYPE - Supports both dict returns and Command
# =============================================================================

NodeFunction = Callable[..., Awaitable[dict[str, Any] | Command]]
```

### 5.2 core/state.py

```python
"""State factory functions."""

from soni.core.types import DialogueState


def create_empty_state() -> DialogueState:
    """Create an empty dialogue state."""
    return {
        "user_message": None,
        "messages": [],
        "response": None,
    }
```

### 5.3 config/models.py (Minimal)

```python
"""Configuration models for Soni v2 M1."""

from pydantic import BaseModel, Field

# DSL Version constants
SUPPORTED_VERSIONS = frozenset({"1.0"})
CURRENT_VERSION = "1.0"


class SayStepConfig(BaseModel):
    """Configuration for say steps."""
    step: str = Field(description="Step identifier")
    type: str = "say"
    message: str = Field(description="Message to display")


class FlowConfig(BaseModel):
    """Configuration for a flow."""
    description: str = ""
    steps: list[SayStepConfig] = Field(default_factory=list)


class SoniConfig(BaseModel):
    """Root configuration with DSL versioning."""
    version: str = Field(default=CURRENT_VERSION, description="DSL version")
    flows: dict[str, FlowConfig] = Field(default_factory=dict)
    
    def model_post_init(self, __context: object) -> None:
        """Validate DSL version after initialization."""
        if self.version not in SUPPORTED_VERSIONS:
            raise ValueError(
                f"Unsupported DSL version: {self.version}. "
                f"Supported: {', '.join(sorted(SUPPORTED_VERSIONS))}"
            )
```

### 5.4 compiler/nodes/base.py (NEW)

```python
"""Base protocol for node factories."""

from typing import Protocol

from soni.config.models import StepConfig
from soni.core.types import NodeFunction


class NodeFactory(Protocol):
    """Protocol for step type node factories (OCP: Open for extension)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node function for the given step config."""
        ...
```

### 5.5 compiler/nodes/say.py

```python
"""SayNodeFactory for M1."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import SayStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction, RuntimeContext


class SayNodeFactory:
    """Factory for say step nodes (SRP: single responsibility)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node that returns a static response."""
        if not isinstance(step, SayStepConfig):
            raise ValueError(f"SayNodeFactory received wrong step type: {type(step).__name__}")
        
        message = step.message
        
        async def say_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Return the message as response."""
            return {"response": message}
        
        say_node.__name__ = f"say_{step.step}"
        return say_node
```

### 5.6 compiler/factory.py (NEW - Registry Pattern)

```python
"""Node factory registry (OCP: extensible without modification)."""

from soni.compiler.nodes.base import NodeFactory
from soni.compiler.nodes.say import SayNodeFactory
from soni.core.errors import GraphBuildError


class NodeFactoryRegistry:
    """Registry for node factories."""

    _factories: dict[str, NodeFactory] = {}

    @classmethod
    def register(cls, step_type: str, factory: NodeFactory) -> None:
        """Register a new node factory."""
        cls._factories[step_type] = factory

    @classmethod
    def get(cls, step_type: str) -> NodeFactory:
        """Get factory for step type."""
        factory = cls._factories.get(step_type)
        if not factory:
            raise GraphBuildError(
                f"Unknown step type: '{step_type}'. Available: {list(cls._factories.keys())}"
            )
        return factory


# Initialize default factories
NodeFactoryRegistry.register("say", SayNodeFactory())


def get_factory_for_step(step_type: str) -> NodeFactory:
    """Get the appropriate factory for a step type."""
    return NodeFactoryRegistry.get(step_type)
```

### 5.7 compiler/subgraph.py

```python
"""Subgraph builder for M1."""

from langgraph.graph import StateGraph, END

from soni.compiler.factory import get_factory_for_step
from soni.config.models import FlowConfig
from soni.core.types import DialogueState


def build_flow_subgraph(flow: FlowConfig):
    """Build a compiled subgraph for a flow."""
    builder = StateGraph(DialogueState)
    
    prev_step = None
    for i, step in enumerate(flow.steps):
        factory = get_factory_for_step(step.type)
        node_fn = factory.create(step, flow.steps, i)
        builder.add_node(step.step, node_fn)
        
        if i == 0:
            builder.set_entry_point(step.step)
        
        if prev_step:
            builder.add_edge(prev_step, step.step)
        
        prev_step = step.step
    
    # Last step -> END
    if prev_step:
        builder.add_edge(prev_step, END)
    
    return builder.compile()
```

### 5.6 dm/nodes/execute.py

```python
"""Execute node for M1."""

from typing import Any

from langgraph.runtime import Runtime

from soni.core.types import DialogueState, RuntimeContext


async def execute_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Execute the active flow's subgraph."""
    subgraph = runtime.context.subgraph
    result = await subgraph.ainvoke(state)
    return {"response": result.get("response")}
```

### 5.7 dm/builder.py

```python
"""Orchestrator builder for M1."""

from langgraph.graph import StateGraph, END

from soni.dm.nodes.execute import execute_node
from soni.core.types import DialogueState


def build_orchestrator():
    """Build the main orchestrator graph."""
    builder = StateGraph(DialogueState)
    
    builder.add_node("execute", execute_node)
    builder.set_entry_point("execute")
    builder.add_edge("execute", END)
    
    return builder.compile()
```

### 5.8 runtime/context.py

```python
\"\"\"RuntimeContext for M1.\"\"\"

from dataclasses import dataclass
from typing import Any

from soni.config.models import SoniConfig


@dataclass
class RuntimeContext:
    \"\"\"Context passed to nodes via runtime.context.
    
    This is the typed context accessible in nodes via `runtime.context`.
    \"\"\"
    subgraph: Any  # CompiledStateGraph
    config: SoniConfig
```

### 5.9 runtime/loop.py

```python
\"\"\"RuntimeLoop for M1.\"\"\"

from typing import Any

from langgraph.graph.state import CompiledStateGraph

from soni.compiler.subgraph import build_flow_subgraph
from soni.config.models import SoniConfig
from soni.core.state import create_empty_state
from soni.dm.builder import build_orchestrator
from soni.runtime.context import RuntimeContext


class RuntimeLoop:
    \"\"\"Simple runtime loop for M1.\"\"\"
    
    def __init__(self, config: SoniConfig) -> None:
        self.config = config
        self._graph: CompiledStateGraph | None = None
        self._context: RuntimeContext | None = None
    
    async def __aenter__(self) -> \"RuntimeLoop\":
        \"\"\"Initialize graphs.\"\"\"
        # Build subgraph for first flow
        flow_name = next(iter(self.config.flows.keys()))
        flow = self.config.flows[flow_name]
        subgraph = build_flow_subgraph(flow)
        
        # Create context
        self._context = RuntimeContext(subgraph=subgraph, config=self.config)
        
        # Build orchestrator
        self._graph = build_orchestrator()
        return self
    
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        \"\"\"Cleanup.\"\"\"
        pass
    
    async def process_message(self, message: str) -> str:
        \"\"\"Process a message and return response.\"\"\"
        if self._graph is None or self._context is None:
            raise RuntimeError(\"RuntimeLoop not initialized. Use 'async with' context.\")
        
        state = create_empty_state()
        state[\"user_message\"] = message
        
        # Pass context via configurable
        config = {\"configurable\": {\"context\": self._context}}
        
        result = await self._graph.ainvoke(state, config)
        return result.get(\"response\", \"\")
```

---

## 6. TDD Test

### 6.1 First Test (Write Before Implementation)

```python
# tests/integration/test_m1_hello_world.py
"""M1: Hello World integration test."""

import pytest

from soni.config.models import SoniConfig, FlowConfig, SayStepConfig
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_hello_world():
    """A flow with a single say step returns the message."""
    # Arrange
    config = SoniConfig(
        flows={
            "greet": FlowConfig(
                steps=[SayStepConfig(step="hello", message="Hello, World!")]
            )
        }
    )
    
    # Act
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("hi")
    
    # Assert
    assert response == "Hello, World!"


@pytest.mark.asyncio
async def test_multi_step_say():
    """A flow with multiple say steps returns the last message."""
    # Arrange
    config = SoniConfig(
        flows={
            "greet": FlowConfig(
                steps=[
                    SayStepConfig(step="hello", message="Hello!"),
                    SayStepConfig(step="welcome", message="Welcome to Soni!"),
                ]
            )
        }
    )
    
    # Act
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("hi")
    
    # Assert
    assert response == "Welcome to Soni!"
```

### 6.2 Unit Tests

```python
# tests/unit/compiler/test_say_node.py
"""Unit tests for SayNodeFactory."""

import pytest

from soni.compiler.nodes.say import create_say_node
from soni.config.models import SayStepConfig


@pytest.mark.asyncio
async def test_say_node_returns_message():
    """Say node returns the configured message."""
    step = SayStepConfig(step="test", message="Test message")
    node = create_say_node(step)
    
    result = await node({}, None)
    
    assert result["response"] == "Test message"


def test_say_node_has_correct_name():
    """Say node function has descriptive name."""
    step = SayStepConfig(step="greet", message="Hello")
    node = create_say_node(step)
    
    assert node.__name__ == "say_greet"
```

---

## 7. Success Criteria

- [ ] `uv run pytest tests/integration/test_m1_hello_world.py` passes
- [ ] `uv run pytest tests/unit/compiler/test_say_node.py` passes
- [ ] No unused imports or dead code
- [ ] Type hints on all public functions

---

## 8. Implementation Order

1. **Write tests first** (RED)
2. `config/models.py` - Models
3. `core/types.py` - DialogueState
4. `core/state.py` - Factory
5. `compiler/nodes/say.py` - Node
6. `compiler/subgraph.py` - Builder
7. `dm/nodes/execute.py` - Execute
8. `dm/builder.py` - Orchestrator
9. `runtime/loop.py` - Loop
10. **Run tests** (GREEN)

---

## Next: M2 (Collect + Interrupt)
