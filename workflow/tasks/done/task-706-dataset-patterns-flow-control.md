## Task: 706 - Dataset Patterns: Flow Control (INTERRUPTION, CANCELLATION, CONTINUATION)

**ID de tarea:** 706
**Hito:** Dataset Creation for NLU Optimization
**Dependencias:** Task 705
**Duración estimada:** 3-4 horas

### Objetivo

Implement flow control patterns: INTERRUPTION (switching to new task), CANCELLATION (abandoning task), and CONTINUATION (general continuation).

### Contexto

Flow control patterns manage conversation flow:

- **INTERRUPTION**: User starts new task mid-conversation
  - "Actually, check hotel prices first"
  - Can happen cold_start or ongoing

- **CANCELLATION**: User abandons current task
  - "Cancel", "Never mind", "Forget it"
  - Only ongoing (requires active flow)

- **CONTINUATION**: General continuation signals
  - "Continue", "Go ahead", "Next"
  - Only ongoing

**Reference:** docs/design/10-dsl-specification/06-patterns.md

### Entregables

- [ ] `interruption.py`, `cancellation.py`, `continuation.py` implemented
- [ ] All three generators working across domains
- [ ] Unit tests extended
- [ ] Target: ~20 examples

### Implementación Detallada

#### Generators Structure

All three follow the same structure as previous patterns:

**interruption.py**:
```python
class InterruptionGenerator(PatternGenerator):
    @property
    def message_type(self) -> MessageType:
        return MessageType.INTERRUPTION

    # Both cold_start (new conversation) and ongoing (interrupting flow)
```

**cancellation.py**:
```python
class CancellationGenerator(PatternGenerator):
    @property
    def message_type(self) -> MessageType:
        return MessageType.CANCELLATION

    # Ongoing only - need active flow to cancel
```

**continuation.py**:
```python
class ContinuationGenerator(PatternGenerator):
    @property
    def message_type(self) -> MessageType:
        return MessageType.CONTINUATION

    # Ongoing only - need context to continue
```

### TDD Cycle

**Tests:**
```python
def test_interruption_cold_start_and_ongoing():
    """Test INTERRUPTION works in both contexts."""
    gen = InterruptionGenerator()
    cold = gen.generate_examples(FLIGHT_BOOKING, "cold_start", 1)
    ongoing = gen.generate_examples(FLIGHT_BOOKING, "ongoing", 1)
    assert len(cold) >= 1
    assert len(ongoing) >= 1


def test_cancellation_ongoing_only():
    """Test CANCELLATION only in ongoing."""
    gen = CancellationGenerator()
    cold = gen.generate_examples(FLIGHT_BOOKING, "cold_start", 3)
    ongoing = gen.generate_examples(FLIGHT_BOOKING, "ongoing", 3)
    assert len(cold) == 0  # No cold start
    assert len(ongoing) >= 1


def test_continuation_ongoing_only():
    """Test CONTINUATION only in ongoing."""
    gen = ContinuationGenerator()
    cold = gen.generate_examples(FLIGHT_BOOKING, "cold_start", 3)
    ongoing = gen.generate_examples(FLIGHT_BOOKING, "ongoing", 3)
    assert len(cold) == 0
    assert len(ongoing) >= 1
```

### Criterios de Éxito

- [ ] All three generators implemented
- [ ] INTERRUPTION works in both contexts
- [ ] CANCELLATION and CONTINUATION ongoing only
- [ ] Examples across all domains
- [ ] Tests pass

### Validación

```bash
uv run pytest tests/unit/test_dataset_patterns.py -v -k "interruption or cancellation or continuation"
```

### Notas

- INTERRUPTION is special: works in both cold_start and ongoing
- Use domain-specific utterances for variety
- Cancellation signals: "cancel", "stop", "forget it", "never mind"
