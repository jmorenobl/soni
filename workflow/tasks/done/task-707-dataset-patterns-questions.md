## Task: 707 - Dataset Patterns: Questions (DIGRESSION, CLARIFICATION, CONFIRMATION)

**ID de tarea:** 707
**Hito:** Dataset Creation for NLU Optimization
**Dependencias:** Task 706
**Duración estimada:** 3-4 horas

### Objetivo

Implement question patterns: DIGRESSION (off-topic question), CLARIFICATION (asking why), and CONFIRMATION (yes/no).

### Contexto

Question patterns:

- **DIGRESSION**: Off-topic question without flow change
  - "What airlines fly that route?"
  - "Do you have direct flights?"
  - Ongoing only

- **CLARIFICATION**: Asking why info is needed
  - "Why do you need my email?"
  - "What's this for?"
  - Ongoing only

- **CONFIRMATION**: Yes/no answers
  - "Yes", "Correct", "No", "That's wrong"
  - Ongoing only (response to confirmation prompt)

### Entregables

- [ ] `digression.py`, `clarification.py`, `confirmation.py`
- [ ] All generators working
- [ ] Unit tests
- [ ] Target: ~20 examples

### Implementación Detallada

**digression.py**:
```python
class DigressionGenerator(PatternGenerator):
    @property
    def message_type(self) -> MessageType:
        return MessageType.DIGRESSION

    # Examples: "What airlines?", "Do you have WiFi?"
    # Ongoing only - need context to be off-topic
```

**clarification.py**:
```python
class ClarificationGenerator(PatternGenerator):
    @property
    def message_type(self) -> MessageType:
        return MessageType.CLARIFICATION

    # Examples: "Why do you need that?", "What for?"
    # Ongoing only - responding to prompt
```

**confirmation.py**:
```python
class ConfirmationGenerator(PatternGenerator):
    @property
    def message_type(self) -> MessageType:
        return MessageType.CONFIRMATION

    # Positive: "Yes", "Correct", "That's right"
    # Negative: "No", "That's wrong", "Incorrect"
    # Ongoing only - response to confirmation step
```

### TDD Cycle

**Tests:**
```python
def test_all_question_patterns_ongoing_only():
    """Test all question patterns work only in ongoing."""
    patterns = [
        DigressionGenerator(),
        ClarificationGenerator(),
        ConfirmationGenerator(),
    ]

    for gen in patterns:
        cold = gen.generate_examples(FLIGHT_BOOKING, "cold_start", 3)
        ongoing = gen.generate_examples(FLIGHT_BOOKING, "ongoing", 3)
        assert len(cold) == 0, f"{gen.message_type} should not work in cold_start"
        assert len(ongoing) >= 1, f"{gen.message_type} should work in ongoing"


def test_confirmation_positive_and_negative():
    """Test confirmation includes both positive and negative examples."""
    gen = ConfirmationGenerator()
    examples = gen.generate_examples(FLIGHT_BOOKING, "ongoing", 5)

    # Should have mix of positive and negative
    positive = [ex for ex in examples if "yes" in ex.user_message.lower() or "correct" in ex.user_message.lower()]
    negative = [ex for ex in examples if "no" in ex.user_message.lower()]

    assert len(positive) >= 1
    assert len(negative) >= 1
```

### Criterios de Éxito

- [ ] All three generators implemented
- [ ] All ongoing only
- [ ] CONFIRMATION has both positive and negative examples
- [ ] Tests pass

### Validación

```bash
uv run pytest tests/unit/test_dataset_patterns.py -v -k "digression or clarification or confirmation"
```

### Notas

- All three patterns require conversation context (ongoing only)
- DIGRESSION: question doesn't change flow, just asks for info
- CLARIFICATION: meta-question about the conversation itself
- CONFIRMATION: must include both positive and negative responses
