# Data Model: Slots & Actions

[← Back to Index](00-index.md) | [← Configuration](02-configuration.md)

---

## 4. Slots (Data Definitions)

Slots define the data the bot collects or tracks. They are **global definitions** that can be used in any flow.

```yaml
slots:
  origin:
    type: string
    description: "Departure city for the flight"
    prompt: "Which city are you departing from?"
    validator: city_name
    normalizer: city_name
    examples: ["Madrid", "NYC", "London", "San Francisco"]

  departure_date:
    type: date
    description: "When the user wants to depart"
    prompt: "What date would you like to depart?"
    validator: future_date

  passenger_count:
    type: integer
    description: "Number of passengers"
    prompt: "How many passengers?"
    default: 1

  selected_flight:
    type: object
    description: "The flight chosen by the user from search results"
    prompt: "Which flight would you like to book? (Enter the flight number)"
```

### 4.1 Slot Fields

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Data type: `string`, `integer`, `float`, `boolean`, `date`, `list`, `object` |
| `description` | Yes | Used by LLM to understand the slot's purpose |
| `prompt` | Yes | Question asked when slot is missing (supports `{var}` interpolation) |
| `validator` | No | Semantic name of a registered Python validator |
| `normalizer` | No | Semantic name of a registered Python normalizer |
| `invalid_message` | No | Custom message when validation fails |
| `default` | No | Default value if not provided |
| `examples` | No | Example values for NLU training |
| `sensitive` | No | If `true`, value is masked in logs (default: `false`) |

**Processing Order:**

When a user provides a value for a slot:
1. **NLU Extraction**: Raw value extracted from user message
2. **Validation**: `validator` function checks if value is valid
3. **Normalization**: If valid, `normalizer` transforms to canonical form
4. **Storage**: Normalized value stored in state

```
User: "nyc"
  → validator("nyc") → true (valid city abbreviation)
  → normalizer("nyc") → "New York"
  → state.origin = "New York"
```

**Example with validation message:**

```yaml
slots:
  email:
    type: string
    description: "User's email address"
    prompt: "What's your email address?"
    validator: email_format
    invalid_message: "That doesn't look like a valid email. Please use format: user@example.com"

  credit_card:
    type: string
    description: "Payment card number"
    prompt: "Please enter your card number"
    validator: credit_card_number
    sensitive: true  # Masked in logs: "****-****-****-1234"
```

### 4.2 Type Behavior

| Type | Python | NLU Extraction |
|------|--------|----------------|
| `string` | `str` | Direct text extraction |
| `integer` | `int` | Number parsing ("three" → 3) |
| `float` | `float` | Decimal parsing |
| `boolean` | `bool` | Yes/no detection |
| `date` | `datetime.date` | Date parsing ("next Friday" → 2024-12-06) |
| `list` | `list[str]` | Selection only (see Reference) |
| `object` | `dict` | Complex structured data (Selection only) |

### 4.3 Global vs Inline Slots

**Global Slots** (defined in `slots:` section) are recommended for:
- Slots with validation (`validator`)
- Slots with custom prompts
- Slots reused across multiple flows
- Slots that need NLU training (`examples`)

**Inline Slots** can be collected without a global definition when:
- The slot is temporary/flow-specific
- No validation is needed
- A prompt is provided in the `collect` step

```yaml
# Global slot - recommended for important data
slots:
  destination:
    type: string
    description: "Arrival city"
    prompt: "Where would you like to go?"
    validator: city_name

# Inline slot - acceptable for temporary data
- step: get_choice
  type: collect
  slot: user_choice           # Not defined globally
  prompt: "What would you like to change?"  # Prompt required inline
```

**Rules for Inline Slots:**
1. `prompt` is **required** (no default prompt available)
2. No validation (accepts any input)
3. Type is inferred as `string`
4. Not available for NLU multi-slot extraction

**Recommendation:** Define important slots globally for better NLU training and validation.

---

## 5. Actions (Contracts)

Actions define the bot's capabilities. The DSL only specifies the **contract** (inputs/outputs), not the implementation.

```yaml
actions:
  search_flights:
    description: "Search for available flights between two cities"
    inputs:
      - origin
      - destination
      - departure_date
      - passenger_count
    outputs:
      - flights        # List of available flights
      - total_results  # Count of results

  book_flight:
    description: "Book a specific flight for the user"
    inputs:
      - selected_flight
      - passenger_count
    outputs:
      - booking_reference
      - confirmation_details

  send_confirmation_email:
    description: "Send booking confirmation to user's email"
    inputs:
      - booking_reference
      - user_email
    outputs:
      - email_sent  # boolean
```

### 5.1 Action Fields

| Field | Required | Description |
|-------|----------|-------------|
| `description` | Yes | Used by LLM for intent matching |
| `inputs` | Yes | List of slot names (append `?` for optional) |
| `outputs` | Yes | List of output keys merged into state |

**Optional Inputs:**

Mark inputs as optional with `?`:

```yaml
actions:
  search_flights:
    description: "Search for available flights"
    inputs:
      - origin
      - destination
      - departure_date
      - return_date?       # Optional
      - cabin_class?       # Optional
      - flexible_dates?    # Optional
    outputs:
      - flights
      - total_results
```

Optional inputs receive `null` if not provided.

### 5.2 Python Binding

```python
from soni.actions import ActionRegistry

@ActionRegistry.register("search_flights")
async def search_flights(
    origin: str,
    destination: str,
    departure_date: date,
    passenger_count: int
) -> dict[str, Any]:
    """Implementation hidden from DSL."""
    results = await flight_api.search(origin, destination, departure_date, passenger_count)
    return {
        "flights": results,
        "total_results": len(results)
    }
```

---

[Next: Flows →](04-flows.md)
