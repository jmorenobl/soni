# Flight Booking - Example Conversation

This document shows an example conversation flow for the flight booking system.

## Conversation Flow

**User:** I want to book a flight

**System:** Where would you like to fly from?

**User:** New York

**System:** Where would you like to fly to?

**User:** Los Angeles

**System:** When would you like to depart?

**User:** Next Friday

**System:** I found 2 available flights:
- Flight AA123: Departure 08:00, Arrival 10:30, Price $299.99
- Flight UA456: Departure 14:00, Arrival 16:30, Price $349.99

Your flight AA123 from New York to Los Angeles on 2024-01-12 has been confirmed. Booking reference: BK-AA123-2024-001

## Expected Behavior

1. User triggers booking intent
2. System collects origin, destination, and date
3. System searches for flights (mock)
4. System confirms booking (mock)
5. System provides booking reference

## Testing

To test this conversation:

```bash
# Start server
uv run soni server --config examples/flight_booking/soni.yaml

# Send messages sequentially
curl -X POST http://localhost:8000/chat/user-123 \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to book a flight"}'

curl -X POST http://localhost:8000/chat/user-123 \
  -H "Content-Type: application/json" \
  -d '{"message": "New York"}'

curl -X POST http://localhost:8000/chat/user-123 \
  -H "Content-Type: application/json" \
  -d '{"message": "Los Angeles"}'

curl -X POST http://localhost:8000/chat/user-123 \
  -H "Content-Type: application/json" \
  -d '{"message": "Next Friday"}'

# ... continue with remaining messages
```
