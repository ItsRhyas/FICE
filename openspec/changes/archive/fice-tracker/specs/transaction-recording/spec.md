# Transaction Recording Specification

## Purpose

Record income, expense, and transfer transactions against accounts. All amounts are integer cents. Transfers are a single atomic row affecting two accounts. Transactions are filterable by account, type, and date range.

## Requirements

### Requirement: Income Transaction

The system MUST record income with `account_id`, `type = income`, `amount_cents` (positive integer), `description`, and `date` (DATE, no time). Income MUST increase the account's computed balance.

#### Scenario: Record income

- GIVEN an account with balance `0`
- WHEN an income of `amount_cents = 200000` is recorded
- THEN the account balance becomes `200000`

#### Scenario: Reject negative income amount

- GIVEN the user submits amount_cents `-100`
- WHEN creation is attempted
- THEN the system rejects the request

### Requirement: Expense Transaction

The system MUST record expense with `account_id`, `type = expense`, `amount_cents` (positive integer), `description`, and `date` (DATE only). Expense MUST decrease the account's computed balance.

#### Scenario: Record expense

- GIVEN an account with balance `100000`
- WHEN an expense of `amount_cents = 30000` is recorded
- THEN the account balance becomes `70000`

### Requirement: Atomic Transfer

The system MUST record a transfer as a single row with `type = transfer`, `account_id` (source), `destination_account_id` (target), and `amount_cents`. The source balance MUST decrease and the target balance MUST increase by the same amount. The operation MUST be atomic — both effects succeed or both fail.

#### Scenario: Transfer between accounts

- GIVEN account A balance `100000` and account B balance `50000`
- WHEN a transfer of `amount_cents = 20000` from A to B is recorded
- THEN A's balance becomes `80000` and B's balance becomes `70000`

#### Scenario: Transfer to same account rejected

- GIVEN account A
- WHEN a transfer with `account_id == destination_account_id` is attempted
- THEN the system rejects the request

#### Scenario: Atomic rollback on failure

- GIVEN a transfer where the target account does not exist
- WHEN the transfer is attempted
- THEN no row is persisted and neither balance changes

### Requirement: Transaction Date

The system MUST store `date` as a DATE (no time component). User input MUST be a local date string (`YYYY-MM-DD`).

#### Scenario: Date stored without time

- GIVEN a transaction recorded with date "2026-07-16"
- WHEN the persisted row is inspected
- THEN it contains no time-of-day component

### Requirement: Transaction Filtering

The system MUST allow filtering transactions by `account_id`, `type`, and date range (`from_date` / `to_date`, inclusive).

#### Scenario: Filter by account and type

- GIVEN transactions across two accounts, mixed types
- WHEN filtering by account A and type `income`
- THEN only income rows for account A are returned

#### Scenario: Filter by date range

- GIVEN transactions on July 1, 15, and 31
- WHEN filtering from "2026-07-10" to "2026-07-20"
- THEN only the July 15 transaction is returned

### Requirement: Transaction Edit and Delete

The system MUST allow editing a transaction's `description`, `amount_cents`, and `date`. Deleting a transaction MUST remove its effect from balance recomputation.

#### Scenario: Edit amount updates balance

- GIVEN an account with an expense of `30000`
- WHEN the expense amount is edited to `25000`
- THEN the recomputed balance reflects the new amount

#### Scenario: Delete transaction removes balance effect

- GIVEN an account with one expense of `30000`
- WHEN the transaction is deleted
- THEN the balance no longer reflects that expense