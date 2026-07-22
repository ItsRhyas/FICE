# Tasks: FICE — Personal Finance Tracker v1

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1300–1500 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy | force-chained |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | PR | Notes |
|------|------|----|-------|
| 1 | Foundation: deps, app factory, DB, SQLModel tables | PR 1 | base for all |
| 2 | Account CRUD + base UI shell + balance service | PR 2 | depends on PR 1 |
| 3 | Transaction recording + filters | PR 3 | depends on PR 2 |
| 4 | Dashboard, HTMX partials, charts, static assets | PR 4 | depends on PR 3 |

## Phase 1: Foundation (PR #1)

- [x] 1.1 Add `requirements.txt`; files: `requirements.txt`; AC: install succeeds; dep: none; est: 5.
- [x] 1.2 Create `main.py`; files: `main.py`; AC: pywebview window opens; dep: 1.1; est: 20.
- [x] 1.3 Create `app/__init__.py`; files: `app/__init__.py`; AC: `uvicorn app:create_app --reload` starts; dep: 1.1; est: 25.
- [x] 1.4 Create `app/db.py`; files: `app/db.py`; AC: tables created at startup; dep: 1.3; est: 30.
- [x] 1.5 Create `app/models.py`; files: `app/models.py`; AC: validators reject invalid enum/float/negative; dep: 1.4; est: 70.
- [x] 1.6 Write `tests/test_models.py`; files: `tests/test_models.py`; AC: pytest passes; dep: 1.5; est: 80.

## Phase 2: Account Management (PR #2)

- [x] 2.1 Add `compute_balance()` to `app/services.py`; files: `app/services.py`; AC: spec formula; dep: 1.6; est: 35.
- [x] 2.2 Create `app/routes/accounts.py`; files: `app/routes/accounts.py`; AC: CRUD + archive endpoints; dep: 2.1; est: 90.
- [x] 2.3 Create `app/templates/base.html`; files: `app/templates/base.html`; AC: layout + nav + HTMX; dep: 2.2; est: 35.
- [x] 2.4 Create account templates; files: `app/templates/accounts/list.html`, `app/templates/accounts/form.html`; AC: CRUD flows render; dep: 2.3; est: 75.
- [x] 2.5 Create base CSS; files: `app/static/css/style.css`; AC: readable UI; dep: 2.3; est: 60.
- [x] 2.6 Write `tests/test_accounts.py`; files: `tests/test_accounts.py`; AC: create/edit/archive/balance; dep: 2.4, 2.5; est: 90.

## Phase 3: Transaction Recording (PR #3)

- [x] 3.1 Add transaction filters to `app/services.py`; files: `app/services.py`; AC: filter by account/type/date; dep: 2.1; est: 40.
- [x] 3.2 Create `app/routes/transactions.py`; files: `app/routes/transactions.py`; AC: income/expense/transfer CRUD; dep: 3.1; est: 120.
- [x] 3.3 Create transaction templates; files: `app/templates/transactions/list.html`, `app/templates/transactions/form.html`; AC: forms render/submit; dep: 3.2, 2.3; est: 100.
- [x] 3.4 Write `tests/test_transactions.py`; files: `tests/test_transactions.py`; AC: atomicity/edit/delete/filters; dep: 3.3; est: 110.

## Phase 4: Dashboard & Charts (PR #4)

- [x] 4.1 Add dashboard aggregations to `app/services.py`; files: `app/services.py`; AC: exclude archived; dep: 3.1; est: 70.
- [x] 4.2 Create `app/routes/dashboard.py`; files: `app/routes/dashboard.py`; AC: page/partials/chart JSON; dep: 4.1; est: 90.
- [x] 4.3 Create dashboard template + partials; files: `app/templates/dashboard.html`, `app/templates/partials/_net_worth.html`, `_account_balances.html`, `_month_summary.html`, `_recent_transactions.html`; AC: partials render; dep: 4.2; est: 100.
- [x] 4.4 Create `app/static/js/charts.js`; files: `app/static/js/charts.js`; AC: charts consume JSON endpoints; dep: 4.2; est: 60.
- [x] 4.5 Extend dashboard CSS; files: `app/static/css/style.css`; AC: dashboard layout; dep: 4.3; est: 30.
- [x] 4.6 Write `tests/test_dashboard.py`; files: `tests/test_dashboard.py`; AC: net worth/partials/charts; dep: 4.3, 4.4, 4.5; est: 70.
