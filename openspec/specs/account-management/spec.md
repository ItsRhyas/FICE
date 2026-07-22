# Account Management Specification

## Purpose

Create, edit, list, and soft-delete financial accounts (bank `banco`, cash `efectivo`, savings `ahorro`) tracked in USD or NIO. Account balances are always computed from transactions, never persisted.

## Requirements

### Requirement: Account Creation

The system MUST allow creating an account with `name`, `type`, `currency`, and `opening_balance_cents`. `type` MUST be one of `banco`, `efectivo`, `ahorro`. `currency` MUST be `USD` or `NIO`. `opening_balance_cents` MUST be an integer (may be negative). The system MUST reject floats and missing fields.

#### Scenario: Create a valid bank account

- GIVEN the user submits name "BAC USD", type `banco`, currency `USD`, opening_balance_cents `100000`
- WHEN the account is created
- THEN the account is persisted with `archived = FALSE`
- AND its balance equals `opening_balance_cents` until transactions exist

#### Scenario: Reject float opening balance

- GIVEN the user submits opening_balance_cents `100.50`
- WHEN creation is attempted
- THEN the system rejects the request with a validation error

#### Scenario: Reject unknown type or currency

- GIVEN the user submits type `credit` or currency `EUR`
- WHEN creation is attempted
- THEN the system rejects with a validation error

### Requirement: Account Editing

The system MUST allow editing an account's `name` and `archived` flag. `type` and `currency` MUST be immutable after creation.

#### Scenario: Rename an account

- GIVEN an existing account
- WHEN the user updates its name
- THEN only the name changes; type and currency remain unchanged

#### Scenario: Currency change rejected

- GIVEN an existing USD account
- WHEN the user attempts to set currency to NIO
- THEN the system rejects the update

### Requirement: Soft Delete

The system MUST support archiving via an `archived` boolean (default `FALSE`). Default list and balance queries MUST exclude archived accounts. Archived accounts MUST remain queryable when explicitly requested.

#### Scenario: Archive excludes from default list

- GIVEN two accounts, one archived
- WHEN the default list is requested
- THEN only the non-archived account is returned

#### Scenario: Archived accounts queryable on demand

- GIVEN one archived account
- WHEN the list is requested with `include_archived = true`
- THEN the archived account is returned

### Requirement: Computed Balance

The system MUST compute balance as `opening_balance_cents + SUM(income) - SUM(expense) + SUM(transfers_in) - SUM(transfers_out)`. The system MUST NOT persist a running balance column.

#### Scenario: Balance reflects transactions

- GIVEN an account with opening_balance_cents `0` and one expense of `5000` cents
- WHEN the balance is read
- THEN it returns `-5000`

#### Scenario: No stored balance column

- GIVEN the account table schema
- WHEN inspected
- THEN no column stores a current balance value