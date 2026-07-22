# Proposal: FICE — Personal Finance Tracker v1

## Intent

Build a single-user personal finance tracker to record income, expenses, and transfers across bank and cash accounts in USD and NIO. The user needs visibility into net worth, per-account balances, and monthly cash flow — currently tracked mentally or in spreadsheets, leading to lost data and no historical view.

## Scope

### In Scope
- Account CRUD (create, edit, archive) for bank (`banco`) and cash (`efectivo`) types
- Transaction CRUD: income, expense, inter-account transfers
- Multi-currency support (USD, NIO) — each account has a `currency` column
- Dashboard with charts: net worth trend, account balances, monthly income/expense summary
- Soft delete via `archived` flag on accounts
- Savings modeled as savings-typed account + transfers
- Desktop app packaging via `pywebview`: native window, app icon, close window → release port

### Out of Scope
- Authentication / multi-user
- Recurring transactions
- Budgets and spending limits
- Multi-currency exchange rate conversion
- CSV import/export
- Data sync / cloud backup
- Mobile app / PWA

## Capabilities

### New Capabilities
- `account-management`: CRUD for accounts (bank, cash, savings types) with soft delete and balance computation
- `transaction-recording`: Record income, expense, and transfer transactions against accounts; compute balances
- `dashboard`: Visual dashboard with charts for net worth, account balances, and monthly summary

### Modified Capabilities
None — greenfield project, no existing specs.

## Approach

**Stack**: Python 3.11+ / FastAPI / SQLite / SQLModel / Jinja2 / HTMX / Chart.js / pywebview

- **Money**: integer cents everywhere. `amount` stored as `INTEGER` (cents). Display formatted with currency symbol. Non-negotiable.
- **Balances**: computed from transactions on read. Never stored. Formula: `opening_balance + SUM(income) - SUM(expense) + SUM(transfers_in) - SUM(transfers_out)`.
- **Soft delete**: `archived BOOLEAN DEFAULT FALSE` on accounts. Queries filter `WHERE archived = FALSE` by default.
- **Transfers**: single `Movimiento` row with `type = transfer`, `account_id` (source), `destination_account_id` (target). Both balances move atomically.
- **Charts**: server-side rendered using Chart.js (single JS file, no build step). HTMX for partial page updates.
- **Locale**: Spanish UI labels, English code identifiers per SDD contract.
- **Desktop packaging**: `pywebview` wraps the FastAPI app in a native OS window. No external browser needed. Window close terminates the Python process and releases the port. App icon configurable. Develop in browser, ship as desktop app.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/models.py` | New | SQLModel definitions for Account, Transaction |
| `app/db.py` | New | SQLite connection, schema creation |
| `app/routes/accounts.py` | New | Account CRUD endpoints + templates |
| `app/routes/transactions.py` | New | Transaction CRUD endpoints + templates |
| `app/routes/dashboard.py` | New | Dashboard endpoint with aggregated data |
| `app/templates/` | New | Jinja2 templates for all views |
| `app/static/` | New | HTMX, Chart.js, minimal CSS |
| `main.py` | New | FastAPI app entry point + pywebview desktop launcher |
| `requirements.txt` | New | Python dependencies |
| `data/fice.db` | New | SQLite database (gitignored) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Float precision bugs in money math | Low | Integer cents mandate enforced in models and tests |
| Timezone off-by-one in transaction dates | Medium | Store naive `DATE` (not `datetime`); user inputs local date |
| Scope creep (categories, budgets, charts) | Medium | MVP list is the contract — anything outside waits |
| No auth on localhost | Low | Document in README; acceptable for personal use |
| pywebview rendering quirks across OS | Low | Test on both Windows and Linux; graceful fallback to browser mode |

## Rollback Plan

Greenfield — rollback is `git revert` to the commit before this change. SQLite database file is gitignored, so data survives code rollback. No migrations to reverse.

## Dependencies

- Python 3.11+ installed on target machine
- `fastapi`, `uvicorn[standard]`, `sqlmodel`, `jinja2`, `python-multipart`, `pywebview`
- HTMX (single JS file, CDN or local)
- Chart.js (single JS file, CDN or local)

## Success Criteria

- [ ] User can create, edit, and archive bank and cash accounts in USD or NIO
- [ ] User can record income, expense, and transfer transactions
- [ ] Account balances are computed correctly from transactions
- [ ] Dashboard shows net worth, per-account balances, and monthly summary with charts
- [ ] All money stored as integer cents, no floats in the data path
- [ ] Soft-deleted accounts excluded from default views
- [ ] App launches as native desktop window on double-click; closing window terminates process
