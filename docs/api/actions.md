# Actions

Action registry system.

::: soni.actions.registry
    options:
      show_root_heading: true
      show_source: true

::: soni.actions.base
    options:
      show_root_heading: true
      show_source: true

## Examples

### Registering a Custom Action

```python
from soni.actions import ActionRegistry

@ActionRegistry.register("my_custom_action")
async def my_custom_action(param1: str, param2: int) -> dict[str, Any]:
    """
    Custom action description.

    Args:
        param1: First parameter description
        param2: Second parameter description

    Returns:
        Dictionary with action results
    """
    # Implementation here
    return {"result": "success", "value": param1 + str(param2)}
```

### Using Actions in YAML

```yaml
flows:
  my_flow:
    steps:
      - step: call_action
        type: action
        call: my_custom_action
        inputs:
          param1: "test"
          param2: 42
```
