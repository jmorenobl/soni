# Banking Assistant Example

A comprehensive banking assistant demonstrating Soni Framework capabilities including multi-step flows, branching, loops, confirmations, and action handling.

## Features

| Feature | Description |
|---------|-------------|
| **Balance Checking** | Query any account (checking, savings, investment) |
| **Transactions** | View transaction history with pagination |
| **Money Transfers** | IBAN validation, 2FA for high-value (>10K) |
| **Card Management** | Block lost/stolen cards, request replacements |
| **Bill Payments** | Pay utilities with issuer lookup |

## Project Structure

```
examples/banking/
├── domain/                    # YAML flow definitions
│   ├── 00-settings.yaml       # Model configuration
│   ├── 01-slots.yaml          # Slot definitions with validation
│   ├── 02-actions.yaml        # Action declarations
│   ├── 10-general.yaml        # Greeting flow
│   ├── 20-accounts.yaml       # Balance & transactions
│   ├── 30-transfers.yaml      # Money transfers with branching
│   ├── 40-cards.yaml          # Card blocking & requests
│   └── 50-bills.yaml          # Bill payments
├── handlers.py                # Action implementations
├── validators.py              # Slot validators (IBAN, amounts, etc.)
├── scripts/                   # Testing framework
│   ├── runner.py              # CLI entry point
│   ├── base.py                # FlowTestRunner, logging utilities
│   └── scenarios/             # Test scenario definitions
└── README.md
```

## Quick Start

### Interactive Chat

```bash
# From project root
make chat

# Or manually:
uv run soni chat \
  --config examples/banking/domain \
  --module examples.banking.handlers
```

### Run Test Scenarios

```bash
# List all available scenarios
python -m examples.banking.scripts.runner list

# Run a single scenario
python -m examples.banking.scripts.runner run check_balance_happy -v

# Run with detailed output (NLU results, state changes)
python -m examples.banking.scripts.runner run check_balance_happy -vv

# Run with full debug (flow stack tree)
python -m examples.banking.scripts.runner run check_balance_happy -vvv

# Run all scenarios with a tag
python -m examples.banking.scripts.runner run all --tag complex -v

# Use real LLM instead of mock NLU
python -m examples.banking.scripts.runner run check_balance_happy --real-nlu -v
```

## Flows Overview

### check_balance
Simple 4-step flow: collect account → fetch balance → format → say result.

### check_transactions
Demonstrates **while loops** for pagination:
```yaml
- step: transactions_loop
  type: while
  condition: "view_more_transactions == 'yes'"
  do:
    - fetch_transactions
```

### transfer_funds
Complex flow with **branching** for 2FA on high-value transfers:
```yaml
- step: auth_branch
  type: branch
  slot: requires_extra_auth
  cases:
    "yes": collect_security_code
    "no": collect_concept
```

### block_card / request_card
Flows with **confirmations** before critical actions:
```yaml
- step: confirm_block
  type: confirm
  slot: block_confirmed
  message: "I'm about to block your {card_type} card..."
```

### pay_bill
Action chaining with dynamic lookups (bill issuer, amount, due date).

## Test Scenarios

| Category | Scenarios | Description |
|----------|-----------|-------------|
| `account` | 4 | Balance checks, transaction pagination |
| `transfer` | 5 | Basic, high-value, denial, modification |
| `cards` | 5 | Block, request, cancellation |
| `bills` | 3 | Payment flows |
| `complex` | 10 | Interruptions, multi-flow, edge cases |

**Total: 27 scenarios**

## Verbosity Levels

| Flag | Level | Shows |
|------|-------|-------|
| `-v` | BASIC | User/Soni messages, final slots, summary |
| `-vv` | DETAILED | + NLU commands, state changes per turn |
| `-vvv` | DEBUG | + Flow stack tree visualization |

## Example Session

```
$ python -m examples.banking.scripts.runner run check_balance_happy -v

Running 1 scenario(s) at verbosity level BASIC
Using mock NLU (deterministic)

╭──────────────────── Scenario ────────────────────╮
│ check_balance_happy                              │
│ Simple balance check flow                        │
╰──────────────────────────────────────────────────╯

───────────────────── Turn 1/2 ─────────────────────
User > What's my balance?
Soni > Which account would you like to check? I can
show you your checking, savings, or investment account.

───────────────────── Turn 2/2 ─────────────────────
User > checking
Soni > Your checking account balance is 3 847.52 EUR.
  ✓ Pattern found: 'balance'
  ✓ Pattern found: 'EUR'

╭────────── Summary: check_balance_happy ──────────╮
│ Status: PASSED                                   │
│ Turns: 2/2 passed                                │
│ Duration: 16ms                                   │
╰──────────────────────────────────────────────────╯
```

## Handlers

All actions are implemented in `handlers.py` with mock data:

- `get_balance` - Returns account balance
- `format_balance_message` - Formats balance for display
- `lookup_iban` - Validates IBAN and looks up bank
- `check_transfer_limits` - Determines if 2FA needed
- `execute_transfer` - Processes transfer
- `block_card` - Blocks card, returns reference
- `request_new_card` - Orders replacement card
- `lookup_bill` / `pay_bill` - Bill payment flow

## Validators

Slot validators in `validators.py`:

- `iban` - Full IBAN validation with MOD-97 checksum
- `account_type` - checking/savings/investment
- `positive_amount` - Positive numbers
- `card_digits` - 4-digit card suffix
- `security_code` - 6-digit OTP
- `address` - Basic address format

> **Note:** Validators require `soni.validation.registry` module which is not yet implemented.
