# Configuration

[← Back to Index](00-index.md) | [← Introduction](01-introduction.md)

---

## 3. Configuration Structure

```yaml
version: "1.0"

settings:
  # Runtime configuration (Section 3.1)
  ...

responses:
  # System message templates (Section 3.2)
  ...

slots:
  # Data definitions (Section 4)
  ...

actions:
  # Action contracts (Section 5)
  ...

flows:
  # Conversation logic (Section 6)
  ...
```

### 3.1 Settings

```yaml
settings:
  runtime:
    max_step_executions: 100  # Max executions per step in a flow (loop protection)

  persistence:
    backend: sqlite  # sqlite, postgres, redis
    connection: "dialogue_state.db"

  llm:
    provider: openai
    model: gpt-4o-mini

  handoff:
    default_queue: general_support  # Default queue for implicit handoffs (e.g. max retries)

  flow_management:
    max_stack_depth: 3
    on_limit_reached: cancel_oldest  # cancel_oldest, reject_new

  conversation:
    default_flow: welcome           # Flow to start when no context
    fallback_flow: fallback         # Flow when no trigger matches
    session_timeout: 1800           # Seconds before session expires
    max_turns_without_progress: 10  # Max turns in same step (see below)
    on_no_progress: handoff         # Action when max_turns reached: handoff | fallback | retry

  collection:
    max_validation_attempts: 3      # Default max retries for invalid input
    validation_timeout: 300         # Seconds to wait for user input

# No Progress Handling:
# When user is stuck in same step for max_turns_without_progress turns:
#   - handoff: Transfer to human agent (default)
#   - fallback: Go to fallback_flow
#   - retry: Reset flow and start over

  i18n:
    default_language: en
    supported_languages: [en, es, fr]
    auto_detect: true           # Detect language from first message
```

### 3.2 Responses (System Messages)

The `responses` section defines **all system messages**. Each response has a default value but can be customized. Responses support:
- **Variables**: `{slot_name}` interpolation (string only, no `{{ }}` expressions)
- **Variations**: Multiple options (randomly selected)
- **Per-language**: i18n support

**Note:** Responses only support `{variable}` interpolation, not `{{ expression }}`. For computed values in responses, calculate them first with a `set` step.

```yaml
responses:
  # ─── Slot Collection ───
  slot_invalid:
    default: "That doesn't seem right. {validation_message}"
    variations:
      - "I didn't understand that. {validation_message}"
      - "Hmm, that doesn't look valid. {validation_message}"

  slot_invalid_max_attempts:
    default: "I'm having trouble understanding. Let me connect you with someone who can help."

  slot_ask_again:
    default: "Could you please tell me {slot_description}?"

  # ─── Corrections & Modifications ───
  correction_acknowledged:
    default: "Got it, I've updated {slot_name} to {new_value}."
    variations:
      - "No problem, {slot_name} changed to {new_value}."
      - "Updated! {slot_name} is now {new_value}."

  modification_acknowledged:
    default: "Done, I've changed {slot_name} to {new_value}."

  # ─── Confirmation ───
  confirm_prompt_suffix:
    default: "Is this correct?"

  confirm_yes_acknowledged:
    default: "Perfect, proceeding..."

  confirm_no_acknowledged:
    default: "No problem. What would you like to change?"

  confirm_partial:
    default: "Got it, I've updated {slot_name}. Let me confirm again..."
    variations:
      - "Updated {slot_name}. Please re-confirm:"
      - "Changed! Here's the updated summary:"

  # ─── Flow Management ───
  flow_started:
    default: ""  # Silent by default

  flow_completed:
    default: ""  # Silent by default

  flow_interrupted:
    default: "I'll pause what we were doing. We can come back to it later."

  flow_resumed:
    default: "Let's continue where we left off."

  # Used when flow ends via on_no default behavior (system-initiated)
  flow_cancelled:
    default: "Okay, I've cancelled that."

  # ─── Cancellation ───
  # Used when USER explicitly cancels ("forget it", "cancel", "never mind")
  cancellation_acknowledged:
    default: "No problem, I've cancelled that. Let me know if you need anything else."
    variations:
      - "Okay, cancelled. Is there anything else I can help with?"
      - "Got it, I've stopped that. What would you like to do instead?"

  # ─── No Progress ───
  no_progress_reached:
    default: "I'm having trouble helping you with this. Let me connect you with someone who can assist better."

  # ─── Digressions ───
  digression_answered:
    default: "{answer}"  # Just the answer, then re-prompt

  digression_unknown:
    default: "I'm not sure about that. Let me focus on what we were doing."

  # ─── Clarifications ───
  clarification_slot:
    default: "I need {slot_description} to {flow_description}."

  # ─── Errors ───
  error_action_failed:
    default: "Something went wrong. Please try again."

  error_timeout:
    default: "I haven't heard from you in a while. Are you still there?"

  error_system:
    default: "I'm experiencing technical difficulties. Please try again later."

  # ─── Fallback ───
  fallback_no_match:
    default: "I'm not sure what you'd like to do. Could you rephrase that?"

  fallback_out_of_scope:
    default: "I can't help with that, but I can help you with {available_capabilities}."

  # ─── Handoff ───
  handoff_initiated:
    default: "I'm connecting you with a human agent. Please wait."

  handoff_context:
    default: "Here's what we discussed: {conversation_summary}"
```

**Response Format:**

Responses support three formats that can be combined:

```yaml
responses:
  # Format 1: Simple default
  simple_response:
    default: "Hello!"

  # Format 2: With variations (randomly selected)
  varied_response:
    default: "Got it!"
    variations:
      - "Understood!"
      - "Perfect!"
      - "Done!"

  # Format 3: Multi-language
  localized_response:
    en: "Hello!"
    es: "¡Hola!"
    fr: "Bonjour!"

  # Format 4: Combined (variations + i18n)
  full_response:
    en:
      default: "Got it!"
      variations:
        - "Understood!"
        - "Perfect!"
    es:
      default: "¡Entendido!"
      variations:
        - "¡Perfecto!"
        - "¡Listo!"
```

**Resolution Order:**
1. Check for `session.language` specific version
2. Fall back to `default_language` from settings
3. Fall back to `default` key
4. Use first available translation

**Using Responses in Steps:**

Reference responses in `say` steps:

```yaml
- step: notify_change
  type: say
  response: correction_acknowledged  # Uses the template
  # OR
  message: "Custom message here"     # Direct message
```

### 3.3 Internationalization (i18n)

All user-facing text can be localized. The runtime selects the appropriate language based on `session.language`.

**Per-Language Responses:**

```yaml
responses:
  welcome_message:
    en: "Hello! How can I help you today?"
    es: "¡Hola! ¿En qué puedo ayudarte hoy?"
    fr: "Bonjour! Comment puis-je vous aider?"
```

**Per-Language Slot Prompts:**

```yaml
slots:
  destination:
    type: string
    description: "Destination city"
    prompt:
      en: "Where would you like to go?"
      es: "¿A dónde te gustaría ir?"
      fr: "Où souhaitez-vous aller?"
    invalid_message:
      en: "I couldn't find that city. Please try again."
      es: "No pude encontrar esa ciudad. Inténtalo de nuevo."
```

**Language Detection:**

The NLU can auto-detect language from the first user message:

```yaml
settings:
  i18n:
    default_language: en
    supported_languages: [en, es, fr]
    auto_detect: true  # Detect from first message
```

**Setting Language Manually:**

Language can be set via:

1. **Session initialization** (from API):
```python
# When starting a session via API
session = await runtime.start_session(
    user_id="user123",
    language="es"  # Sets session.language
)
```

2. **Within a flow** using `set`:
```yaml
- step: set_spanish
  type: set
  values:
    session.language: "es"
```

3. **Via action** (e.g., user preference from database):
```yaml
- step: load_preferences
  type: action
  call: get_user_preferences
  map_outputs:
    language: session.language
```

**Fallback Behavior:**

If a translation is missing, the system uses:
1. `default_language` translation
2. First available translation
3. The key name itself (for debugging)

### 3.4 Rich UI Components

For channels that support rich UI (web, mobile, etc.), use the `ui` field:

**Buttons:**

```yaml
- step: ask_trip_type
  type: collect
  slot: trip_type
  prompt: "What type of trip?"
  ui:
    type: buttons
    options:
      - label: "One way"
        value: "one_way"
      - label: "Round trip"
        value: "round_trip"
```

**Quick Replies:**

```yaml
- step: confirm
  type: confirm
  message: "Book this flight?"
  ui:
    type: quick_replies
    options: ["Yes, book it", "No, change something", "Cancel"]
```

**Card (single item):**

```yaml
- step: show_booking
  type: say
  message: "Here's your booking:"
  ui:
    type: card
    title: "Flight {flight_number}"
    subtitle: "{origin} → {destination}"
    image: "{airline_logo_url}"
    fields:
      - label: "Date"
        value: "{departure_date}"
      - label: "Time"
        value: "{departure_time}"
      - label: "Price"
        value: "${price}"
    buttons:
      - label: "Confirm"
        value: "confirm"
      - label: "Change"
        value: "change"
```

**Carousel (list of cards):**

```yaml
- step: select_flight
  type: collect
  slot: selected_flight
  from: flights
  ui:
    type: carousel
    card:
      title: "{airline} {flight_number}"
      subtitle: "{departure_time} → {arrival_time}"
      image: "{airline_logo_url}"
      fields:
        - label: "Duration"
          value: "{duration}"
        - label: "Stops"
          value: "{stops}"
      buttons:
        - label: "Select"
          value: "{flight_id}"
```

**Image:**

```yaml
- step: show_map
  type: say
  message: "Here's the route:"
  ui:
    type: image
    url: "{route_map_url}"
    alt: "Flight route from {origin} to {destination}"
```

**Channel Degradation:**

Rich UI degrades gracefully for text-only channels:
- Buttons → Numbered list
- Carousel → Text list
- Images → Alt text or omitted

---

[Next: Data Model →](03-data-model.md)
