# Reference: Python Implementation & Appendices

[← Back to Index](00-index.md) | [← Examples](08-examples.md)

---

## 12. Python Implementation Reference

### 12.1 Action Registration

```python
from soni.actions import ActionRegistry

@ActionRegistry.register("search_flights")
async def search_flights(origin: str, destination: str, departure_date: date) -> dict:
    results = await flight_api.search(origin, destination, departure_date)
    return {
        "flights": [f.to_dict() for f in results],
        "result_count": len(results)
    }
```

### 12.2 Validator Registration

Validators can be sync or async, and optionally receive a `context` parameter with current state:

```python
from soni.validation import ValidatorRegistry

# Simple validator (no context)
@ValidatorRegistry.register("city_name")
def validate_city(value: str) -> bool:
    # Technical validation logic hidden from DSL
    return bool(re.match(r"^[A-Za-z\s\-']+$", value)) and len(value) >= 2

@ValidatorRegistry.register("future_date")
def validate_future_date(value: date) -> bool:
    return value > date.today()

# Validator with context (receives current flow state)
@ValidatorRegistry.register("return_after_departure")
def validate_return_date(value: date, context: dict) -> bool:
    """Validate return date is after departure."""
    departure = context.get("departure_date")
    if departure and value <= departure:
        return False
    return value > date.today()

# Async validator with context
@ValidatorRegistry.register("available_destination")
async def validate_destination(value: str, context: dict) -> bool:
    """Check if destination is available from origin."""
    origin = context.get("origin")
    routes = await flight_api.get_routes(origin)
    return value in routes
```

**Context Parameter:**
- Optional second parameter named `context`
- Contains all current flow state variables as a dict
- Runtime auto-detects if validator accepts context
- Use for cross-slot validation (see Section 15.5 for limitations)

### 12.3 Normalizer Registration

Normalizers transform user input into a canonical form after validation:

```python
from soni.validation import NormalizerRegistry

@NormalizerRegistry.register("capitalize")
def normalize_capitalize(value: str) -> str:
    """Capitalize first letter of each word."""
    return value.title()

@NormalizerRegistry.register("city_name")
def normalize_city(value: str) -> str:
    """Normalize city names to standard format."""
    # Map common variations to canonical names
    city_map = {
        "nyc": "New York",
        "ny": "New York",
        "la": "Los Angeles",
        "sf": "San Francisco",
        "cdmx": "Mexico City",
    }
    normalized = value.lower().strip()
    return city_map.get(normalized, value.title())

@NormalizerRegistry.register("phone_number")
def normalize_phone(value: str) -> str:
    """Remove formatting from phone numbers."""
    import re
    return re.sub(r"[^\d+]", "", value)

@NormalizerRegistry.register("iata_code")
def normalize_iata(value: str) -> str:
    """Normalize airport codes to uppercase."""
    return value.upper().strip()
```

**Async Normalizers:**

For normalizers that need external lookups:

```python
@NormalizerRegistry.register("city_to_iata")
async def normalize_city_to_iata(value: str) -> str:
    """Convert city name to IATA airport code."""
    # Can make async API calls
    result = await airport_api.lookup_city(value)
    return result.iata_code if result else value
```

**Normalizers with Context:**

Like validators, normalizers can receive a `context` parameter for context-aware transformations:

```python
@NormalizerRegistry.register("relative_date")
def normalize_relative_date(value: str, context: dict) -> date:
    """Normalize relative dates based on reference date."""
    from datetime import timedelta

    reference = context.get("departure_date") or date.today()
    if value.lower() == "next day":
        return reference + timedelta(days=1)
    elif value.lower() == "same day":
        return reference
    return value  # Return as-is if not a relative date
```

**Usage in slots:**

```yaml
slots:
  origin:
    type: string
    prompt: "Where are you flying from?"
    validator: city_name
    normalizer: city_name  # Transform "nyc" → "New York"

  origin_code:
    type: string
    normalizer: iata_code  # Transform "jfk" → "JFK"
```

---

## 13. Appendix: Step Type Summary

| Type | Purpose | Waits for User | Modifies State |
|------|---------|----------------|----------------|
| `collect` | Gather slot value | Yes | Yes (slot) |
| `action` | Execute business logic | No | Yes (outputs) |
| `branch` | Conditional routing | No | No |
| `say` | Send message | No | No |
| `confirm` | Request confirmation | Yes | Yes* |
| `generate` | LLM response | No | Optional |
| `call_flow` | Invoke sub-flow | Yes (indirect) | Yes (outputs) |
| `set` | Set variables | No | Yes |
| `handoff` | Transfer to human | Yes | No |

*`confirm` modifies state when user makes corrections or modifications during confirmation (handled automatically by runtime).

---

## 14. Appendix: Reserved Keywords

The following are reserved and cannot be used as step IDs:
- `end` - End the flow normally
- `error` - End the flow with error state
- `continue` - Go to next sequential step (in `then`)
- `cancel_flow` - Cancel current flow and return to parent/idle (used in `on_no`)

---

## 15. Known Limitations & Future Work

This section documents features that are **not yet supported** but are planned for future versions.

### 15.1 Not Yet Implemented

| Feature | Description | Workaround |
|---------|-------------|------------|
| **External Events** | Receiving webhooks/push notifications | Use polling actions |
| **Cross-Session Persistence** | Remember user across sessions | Store in external DB via action |
| **Knowledge Base Config** | DSL-based KB for digressions | Use `generate` with context |
| **Hand-back from Human** | Return to bot after handoff | Manual flow restart |
| **Cross-Slot Validation** | Validate `return_date > departure_date` | Custom validator in Python |
| **Parallel Step Execution** | Run multiple actions simultaneously | Sequential with caching |

### 15.2 External Events (Planned)

Future versions will support receiving external events:

```yaml
# PLANNED - NOT YET IMPLEMENTED
events:
  payment_completed:
    trigger:
      webhook: /webhooks/payment
    handler: handle_payment_success

  flight_cancelled:
    trigger:
      webhook: /webhooks/flight-status
    handler: notify_cancellation
```

### 15.3 Cross-Session User Memory (Planned)

Future versions will support persistent user preferences:

```yaml
# PLANNED - NOT YET IMPLEMENTED
settings:
  user_memory:
    enabled: true
    storage: postgres

# Access via user.* prefix
- step: greet
  type: say
  message: "Welcome back, {user.preferred_name}! Your usual route is {user.favorite_origin} to {user.favorite_destination}."
```

### 15.4 Knowledge Base (Planned)

Future versions will support declarative KB for digressions:

```yaml
# PLANNED - NOT YET IMPLEMENTED
knowledge_base:
  sources:
    - type: faq
      path: ./faqs.yaml
    - type: documents
      path: ./docs/

  digression_handling:
    search_kb: true
    fallback_to_llm: true
```

### 15.5 Cross-Slot Validation

Cross-slot validation (e.g., `return_date > departure_date`) is supported via validators with `context` parameter (see Section 12.2). However, this requires Python code.

Future versions may support **declarative** cross-slot rules directly in YAML:

```yaml
# PLANNED - NOT YET IMPLEMENTED
slots:
  return_date:
    type: date
    validator: future_date
    constraints:
      - "return_date > departure_date"
      - "return_date <= departure_date + 365 days"
```

### 15.6 List and Object Collection

Currently, `list` and `object` slot types cannot be **extracted** directly from user text via NLU. However, they **can** be collected by allowing the user to **select** from a pre-existing list (using the `from` field in a `collect` step).

Future versions may add explicit support for iterative collection (e.g., "Add another passenger?"):

```yaml
# PLANNED - NOT YET IMPLEMENTED
- step: get_passengers
  type: collect_list
  slot: passengers
  item_type: passenger_info
  min_items: 1
  max_items: 9
  prompts:
    first: "Who is the first passenger?"
    next: "Add another passenger or say 'done'"
```

---

**Document Version**: 1.5
**Status**: Design Specification
**Last Updated**: 2024-12-05
