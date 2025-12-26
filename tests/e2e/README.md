# E2E Test Scenarios Documentation

This document describes the end-to-end test scenarios implemented for the Soni dialogue system.

## Overview

The E2E test suite validates complete user journeys across different domains and complex interaction patterns. All tests use real NLU (DSPy with GPT-4o-mini) to ensure realistic behavior.

## Test Organization

### By Domain

#### Banking (`test_banking_real.py`)
- **test_real_nlu_transfer_flow**: Validates complete money transfer flow with slot collection

#### E-commerce (`test_ecommerce_real.py`)
- **test_product_search_and_purchase**: Complete shopping journey (search → add to cart → checkout)
- **test_order_modification**: Modify cart contents before checkout

#### Hotel Booking (`test_hotel_booking_real.py`)
- **test_room_booking_with_preferences**: Book room with location, dates, guests, and room type
- **test_booking_cancellation**: Cancel an in-progress booking

### By Pattern

#### Complex Patterns (`test_complex_patterns.py`)
- **test_nested_flow_with_multiple_digressions**: Handle interruptions and return to main flow
- **test_correction_during_confirmation**: Correct slot values during confirmation phase
- **test_cancellation_and_resume**: Cancel flow and start new one

#### Error Recovery (`test_error_recovery.py`)
- **test_nlu_error_recovery**: System remains responsive after NLU failures
- **test_action_error_recovery**: Graceful error handling when actions fail

#### Performance (`test_performance.py`)
- **test_response_time**: Response latency under 5 seconds
- **test_concurrent_sessions_performance**: Handle 5 concurrent sessions efficiently

## Test Execution

### Run All E2E Tests
```bash
uv run pytest tests/e2e/ -v
```

### Run Specific Domain
```bash
uv run pytest tests/e2e/test_banking_real.py -v
```

### Exclude Slow Tests
```bash
uv run pytest tests/e2e/ -v -m "not slow"
```

### Run Only Performance Tests
```bash
uv run pytest tests/e2e/test_performance.py -v
```

## Requirements

- `OPENAI_API_KEY` environment variable must be set
- All tests are marked with `@pytest.mark.e2e`
- Performance tests are additionally marked with `@pytest.mark.slow`

## Coverage Goals

E2E tests focus on integration and user journey validation rather than code coverage. They complement unit and integration tests to ensure:

1. **End-to-end functionality**: Complete user journeys work as expected
2. **Real LLM behavior**: System handles actual LLM responses correctly
3. **Error resilience**: Graceful degradation when components fail
4. **Performance baselines**: Response times meet acceptable thresholds

## Implementation Notes

### Domain Configurations

New domains (ecommerce, hotel_booking) were created with minimal configurations:
- `examples/ecommerce/domain/soni.yaml`
- `examples/hotel_booking/domain/soni.yaml`

### Action Handlers

Mock action handlers registered for each domain:
- `examples/ecommerce/handlers.py`: search_products, add_to_cart, process_payment
- `examples/hotel_booking/handlers.py`: search_hotels, book_hotel, cancel_reservation

### Error Handling

Enhanced `action_node` to catch exceptions and return user-friendly error messages instead of crashing, ensuring error recovery tests pass.

## Test Results Summary

- **Total Tests**: 12
- **Passing**: 10+
- **Coverage**: E2E tests increased overall coverage to 47%+
- **Execution Time**: ~50-70 seconds for full suite

## Future Enhancements

1. Add more domain scenarios (restaurant, flight booking)
2. Test multi-language support
3. Add stress testing for high-concurrency scenarios
4. Implement regression test suite for critical user journeys
