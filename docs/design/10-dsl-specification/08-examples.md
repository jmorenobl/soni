# Complete Example: Flight Booking

[← Back to Index](00-index.md) | [← Control Flow & Errors](07-control-error.md)

---

## 11. Complete Example

This example demonstrates a complete flight booking flow using all the DSL features.

```yaml
version: "1.0"

settings:
  conversation:
    default_flow: welcome
    fallback_flow: fallback
  i18n:
    default_language: en

slots:
  origin:
    type: string
    description: "Departure city"
    prompt: "Which city are you departing from?"
    validator: city_name

  destination:
    type: string
    description: "Arrival city"
    prompt: "Where would you like to fly to?"
    validator: city_name

  departure_date:
    type: date
    description: "Departure date"
    prompt: "What date would you like to depart?"
    validator: future_date

  selected_flight:
    type: object
    description: "The chosen flight"
    prompt: "Which flight would you like? (Enter the number)"

actions:
  search_flights:
    description: "Search available flights"
    inputs: [origin, destination, departure_date]
    outputs: [flights, result_count]

  book_flight:
    description: "Book the selected flight"
    inputs: [selected_flight]
    outputs: [booking_reference, confirmation]

flows:
  book_flight:
    description: "Complete flight booking process"

    trigger:
      intents:
        - "I want to book a flight"
        - "Book a flight to Paris"
        - "I need to fly to London"

    outputs:
      - booking_reference

    process:
      # 1. Collect travel details
      - step: get_origin
        type: collect
        slot: origin

      - step: get_destination
        type: collect
        slot: destination

      - step: get_date
        type: collect
        slot: departure_date

      # 2. Search for flights
      - step: search
        type: action
        call: search_flights
        on_error: search_error

      # 3. Check results
      - step: check_results
        type: branch
        when:
          - condition: "result_count == 0"
            then: no_flights
          - else: show_flights

      # 4. Show results and select
      - step: show_flights
        type: say
        message: "I found {result_count} flights from {origin} to {destination}:"

      - step: select_flight
        type: collect
        slot: selected_flight
        from: flights
        display: "{flight_number} | {departure_time} | ${price}"

      # 5. Confirm booking
      - step: confirm
        type: confirm
        message: |
          Please confirm your booking:
          - Route: {origin} → {destination}
          - Date: {departure_date}
          - Flight: {selected_flight.flight_number}
          - Price: ${selected_flight.price}

          Proceed with booking?
        on_yes: execute_booking
        on_no: modify
        # on_change is auto-handled: updates slot and re-confirms

      # 6. Execute booking
      - step: execute_booking
        type: action
        call: book_flight
        on_error: booking_error

      # 7. Success
      - step: success
        type: say
        message: |
          ✅ Booking confirmed!
          Reference: {booking_reference}

          You'll receive a confirmation email shortly.
        jump_to: end

      # --- Alternative Paths ---

      - step: no_flights
        type: say
        message: "No flights found for those dates. Would you like to try different dates?"
        jump_to: get_date

      # on_no: User rejected completely - ask what they want to do
      - step: modify
        type: say
        message: "No problem. What would you like to change?"

      - step: wait_for_change
        type: collect
        slot: change_requested
        prompt: "You can change: origin, destination, date, or flight. Or say 'cancel' to start over."

      - step: apply_change
        type: branch
        when:
          - condition: "change_requested == 'cancel'"
            then: get_origin
          - else: route_change

      # Route to appropriate collection step, then return to confirm
      - step: route_change
        type: branch
        when:
          - condition: "change_requested == 'origin'"
            then: change_origin
          - condition: "change_requested == 'destination'"
            then: change_destination
          - condition: "change_requested == 'date'"
            then: change_date
          - condition: "change_requested == 'flight'"
            then: select_flight
          - else: confirm

      - step: change_origin
        type: collect
        slot: origin
        force: true
        jump_to: confirm  # Return to confirmation after change

      - step: change_destination
        type: collect
        slot: destination
        force: true
        jump_to: confirm  # Return to confirmation after change

      - step: change_date
        type: collect
        slot: departure_date
        force: true
        jump_to: confirm  # Return to confirmation after change

      # NOTE: Corrections during confirmation are handled AUTOMATICALLY by the runtime.
      # If user says "Sorry, I meant San Diego not San Francisco" during confirm step,
      # the runtime updates the slot and re-displays confirmation without any DSL config.

      - step: search_error
        type: say
        message: "I couldn't search for flights right now. Please try again later."
        jump_to: end

      - step: booking_error
        type: say
        message: "The booking couldn't be completed: {_error_message}"
        jump_to: end

  # ─── Required Special Flows ───

  welcome:
    description: "Initial greeting when conversation starts"
    process:
      - step: greet
        type: say
        message: "Hello! I'm your flight booking assistant. I can help you search and book flights."
      - step: prompt
        type: say
        message: "Just tell me where you'd like to go, or say 'help' for more options."

  fallback:
    description: "Handle unrecognized input"
    process:
      - step: apologize
        type: say
        message: "I'm not sure I understood that."
      - step: suggest
        type: say
        message: "I can help you book flights. Try saying something like 'Book a flight to Paris' or 'I need to fly to London'."
```

---

## Key Patterns Demonstrated

### 1. Multi-Slot Extraction
When user says "Book a flight from Madrid to Paris on December 15th", the NLU extracts all three slots at once, skipping the individual `collect` steps.

### 2. Automatic Corrections
During the `confirm` step, if user says "Sorry, I meant San Diego not San Francisco", the runtime automatically:
- Detects the correction
- Updates the destination slot
- Re-displays the confirmation

### 3. Error Handling
Each action has an `on_error` handler that gracefully handles failures.

### 4. Flow Modification
The `modify` path allows users to change specific values without restarting the entire flow.

### 5. Validation
Each slot references a `validator` that is implemented in Python, keeping technical details out of the YAML.

---

[Next: Reference →](09-reference.md)
