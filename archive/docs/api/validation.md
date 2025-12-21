# Validation

Validator registry system.

::: soni.validation.registry
    options:
      show_root_heading: true
      show_source: true

::: soni.validation.validators
    options:
      show_root_heading: true
      show_source: true

## Examples

### Registering a Custom Validator

```python
from soni.validation.registry import ValidatorRegistry

@ValidatorRegistry.register("my_validator")
def validate_my_field(value: str) -> bool:
    """
    Validates the field format.

    Args:
        value: Value to validate

    Returns:
        True if valid, False otherwise
    """
    return bool(value and len(value) > 0 and value.isalnum())
```

### Using Validators in YAML

```yaml
entities:
  my_entity:
    validators:
      - my_validator
```
