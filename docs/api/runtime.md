# Runtime

Runtime loop and message processing.

::: soni.runtime.runtime
    options:
      show_root_heading: true
      show_source: true

::: soni.runtime.config_manager
    options:
      show_root_heading: true
      show_source: true

::: soni.runtime.conversation_manager
    options:
      show_root_heading: true
      show_source: true

::: soni.runtime.streaming_manager
    options:
      show_root_heading: true
      show_source: true

## Examples

### Basic Usage

```python
from soni.runtime.runtime import RuntimeLoop

# Initialize runtime
runtime = RuntimeLoop("config.yaml")

# Process message
response = await runtime.process_message("Hello", "user-123")
print(response)
```

### Streaming

```python
async for token in runtime.process_message_stream("Hello", "user-123"):
    print(token, end="", flush=True)
```

### With Custom Components

```python
from soni.core.scope import ScopeManager
from soni.runtime.runtime import RuntimeLoop

# Create custom scope manager
scope_manager = ScopeManager(config)

# Initialize with custom components
runtime = RuntimeLoop(
    "config.yaml",
    scope_manager=scope_manager,
)
```
