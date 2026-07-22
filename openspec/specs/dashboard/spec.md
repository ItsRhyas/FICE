# Dashboard Specification

## Purpose

Present aggregated financial data: net worth, per-account balances, current-month income vs expense, and recent transactions. Render charts with Chart.js and update sections via HTMX.

## Requirements

### Requirement: Net Worth

The system MUST compute net worth as the sum of all non-archived account balances. Multi-currency balances MUST be summed per currency (no exchange conversion in v1); a per-currency breakdown MUST accompany the total.

#### Scenario: Net worth across accounts

- GIVEN accounts A (USD) balance `100000` and B (NIO) balance `500000`
- WHEN net worth is requested
- THEN it returns per-currency totals (USD `100000`, NIO `500000`) rather than a single converted figure

### Requirement: Per-Account Balances

The system MUST display the computed balance of each non-archived account with its currency symbol.

#### Scenario: List account balances

- GIVEN three non-archived accounts
- WHEN the dashboard loads
- THEN each account's name, currency, and computed balance is shown

### Requirement: Current Month Summary

The system MUST compute the current calendar month's total income and total expense across all non-archived accounts.

#### Scenario: Month summary

- GIVEN this month has income `500000` and expense `300000`
- WHEN the current-month summary is requested
- THEN income `500000` and expense `300000` are returned

### Requirement: Recent Transactions

The system MUST show the last 10 transactions ordered by date descending across all non-archived accounts.

#### Scenario: Last ten transactions

- GIVEN 15 transactions exist
- WHEN the recent-transactions section loads
- THEN exactly the 10 most recent are displayed

### Requirement: Charts

The system MUST render three charts using Chart.js: a bar chart of monthly income vs expense, a doughnut chart of balance distribution by account, and a line chart of net-worth trend over time. Charts MUST consume server-provided JSON data.

#### Scenario: Bar chart data

- GIVEN income and expense totals per month for the trailing months
- WHEN the bar chart section renders
- THEN a labeled bar chart shows income vs expense per month

#### Scenario: Doughnut distribution

- GIVEN multiple accounts with positive balances
- WHEN the doughnut section renders
- THEN each slice represents one account's share of total balance

#### Scenario: Line trend

- GIVEN historical net-worth points over time
- WHEN the line chart renders
- THEN a line plots net worth across dates

### Requirement: HTMX Partial Updates

The system MUST allow individual dashboard sections to refresh via HTMX partial requests without reloading the full page.

#### Scenario: Partial refresh of transactions

- GIVEN the dashboard is displayed
- WHEN an HTMX request targets the recent-transactions section
- THEN only that section's HTML is replaced

### Requirement: Archived Exclusion

The dashboard MUST exclude archived accounts and their transactions from all aggregations.

#### Scenario: Archived account ignored

- GIVEN one archived account with a positive balance
- WHEN net worth is computed
- THEN the archived account contributes nothing