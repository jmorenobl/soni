# Flight Booking Example

This example demonstrates a complete flight booking dialogue system using the Soni Framework.

## Overview

The flight booking system allows users to:
- Book a flight by providing origin, destination, and departure date
- Search for available flights
- Confirm their booking

## Configuration

The system is configured via `soni.yaml` which defines:
- **Flows**: The `book_flight` flow with linear steps
- **Slots**: `origin`, `destination`, `departure_date` with validators
- **Actions**: `search_available_flights` and `confirm_flight_booking`

## Running the Example

### Prerequisites

- Python 3.11+
- OpenAI API key (set `OPENAI_API_KEY` environment variable)
- Soni framework installed

### Start the Server

```bash
# From project root
uv run soni server --config examples/flight_booking/soni.yaml
```

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# Start a conversation
curl -X POST http://localhost:8000/chat/user-123 \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to book a flight"}'
```

## Example Conversation

See `test_conversation.md` for a complete example conversation.

## Architecture

- **YAML Configuration**: Defines the dialogue flow and structure
- **Handlers**: Python functions that implement business logic
- **Runtime**: Soni RuntimeLoop orchestrates the dialogue

## Notes

- This is an MVP example with mock handlers
- In production, handlers would call real flight APIs
- The example uses linear flows only (branching will be added in v0.3.0)
