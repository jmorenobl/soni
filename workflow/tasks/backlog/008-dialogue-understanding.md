## Task: 008 - Dialogue Understanding (DSPy)

**ID de tarea:** 008
**Hito:** 5 - Dialogue Understanding
**Dependencias:** 002, 007
**Duración estimada:** 6 horas

### Objetivo

Implement the NLU module using DSPy to extract Commands from user messages.

### Entregables

- [ ] `du/signatures.py` - DSPy signatures
- [ ] `du/modules.py` - SoniDU module
- [ ] `du/optimizer.py` - MIPROv2 wrapper (optional)
- [ ] Command extraction tests
- [ ] Mock LM for testing

### Implementación Detallada

**Archivo:** `src/soni/du/signatures.py`

```python
"""DSPy signatures for dialogue understanding."""
import dspy


class ExtractCommands(dspy.Signature):
    """Extract structured commands from user message.
    
    Given a user message and conversation context, produce a list of
    commands that represent the user's intent.
    """
    
    user_message: str = dspy.InputField(desc="The user's message")
    available_flows: list[str] = dspy.InputField(desc="Available flow names")
    active_flow: str = dspy.InputField(desc="Currently active flow, or 'none'")
    waiting_for_slot: str = dspy.InputField(desc="Slot being collected, or 'none'")
    
    commands: list[dict] = dspy.OutputField(desc="List of command dicts with 'type' and params")
    reasoning: str = dspy.OutputField(desc="Brief explanation of interpretation")
```

**Archivo:** `src/soni/du/modules.py`

```python
"""DSPy modules for dialogue understanding.

IMPORTANT: Async-first design using dspy.asyncify.
All public methods are async.
"""
import dspy
from soni.core.commands import parse_command, Command
from soni.du.signatures import ExtractCommands


class SoniDU(dspy.Module):
    """Dialogue Understanding module using DSPy.
    
    Async-first design:
    - Uses dspy.asyncify for async LM calls
    - ChainOfThought for reasoning
    - MIPROv2 optimization support
    - Save/load for persistence
    """
    
    def __init__(self):
        super().__init__()
        self.extractor = dspy.ChainOfThought(ExtractCommands)
        # Wrap for async support
        self._async_extractor = dspy.asyncify(self.extractor)
    
    async def forward(
        self,
        user_message: str,
        available_flows: list[str],
        active_flow: str = "none",
        waiting_for_slot: str = "none",
    ) -> list[Command]:
        """Extract commands from user message (async).
        
        All I/O operations use async patterns.
        """
        result = await self._async_extractor(
            user_message=user_message,
            available_flows=available_flows,
            active_flow=active_flow,
            waiting_for_slot=waiting_for_slot,
        )
        
        commands = []
        for cmd_dict in result.commands:
            try:
                cmd = parse_command(cmd_dict)
                commands.append(cmd)
            except Exception:
                continue
        
        return commands
    
    def save(self, path: str) -> None:
        """Save optimized module to file."""
        super().save(path)
    
    def load(self, path: str) -> None:
        """Load optimized module from file."""
        super().load(path)
        # Re-wrap for async after loading
        self._async_extractor = dspy.asyncify(self.extractor)
```

**Archivo:** `src/soni/du/optimizer.py`

```python
"""MIPROv2 optimizer wrapper for SoniDU.

Uses DSPy's latest MIPROv2 for prompt optimization.
"""
from dspy.teleprompt import MIPROv2
from soni.du.modules import SoniDU


async def optimize_du(
    trainset: list,
    metric: callable,
    auto: str = "light",  # "light", "medium", "heavy"
) -> SoniDU:
    """Optimize SoniDU with MIPROv2.
    
    Args:
        trainset: Training examples
        metric: Evaluation metric function
        auto: Optimization intensity
    
    Returns:
        Optimized SoniDU module
    """
    teleprompter = MIPROv2(
        metric=metric,
        auto=auto,
    )
    
    program = SoniDU()
    optimized = teleprompter.compile(
        program.deepcopy(),
        trainset=trainset,
        max_bootstrapped_demos=3,
        max_labeled_demos=4,
    )
    
    return optimized
```

### TDD Cycle

```python
# tests/unit/du/test_modules.py
class TestSoniDU:
    def test_extract_start_flow_command(self):
        """
        GIVEN a message "I want to book a flight"
        WHEN processed by SoniDU
        THEN returns StartFlow command
        """
        # Arrange - use mock LM
        dspy.configure(lm=MockLM(responses=[{
            "commands": [{"type": "start_flow", "flow_name": "book_flight"}],
            "reasoning": "User wants to book a flight"
        }]))
        
        du = SoniDU()
        
        # Act
        commands = du.forward(
            user_message="I want to book a flight",
            available_flows=["book_flight", "cancel_booking"],
        )
        
        # Assert
        assert len(commands) == 1
        assert commands[0].command_type == "start_flow"

    def test_extract_set_slot_when_waiting(self):
        # Arrange
        dspy.configure(lm=MockLM(responses=[{
            "commands": [{"type": "set_slot", "slot_name": "origin", "value": "Madrid"}],
            "reasoning": "User provided origin value"
        }]))
        
        du = SoniDU()
        
        # Act
        commands = du.forward(
            user_message="Madrid",
            available_flows=["book_flight"],
            active_flow="book_flight",
            waiting_for_slot="origin",
        )
        
        # Assert
        assert commands[0].command_type == "set_slot"
        assert commands[0].value == "Madrid"
```

### Criterios de Éxito

- [ ] Commands extracted correctly
- [ ] Works with mock LM for testing
- [ ] Handles multiple commands
- [ ] Error handling for malformed output
