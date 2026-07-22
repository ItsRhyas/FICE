# Design: FICE — Personal Finance Tracker v1

## Technical Approach

Greenfield monolith: FastAPI serves Jinja2 HTML + HTMX partials + JSON chart endpoints. SQLite via SQLModel. pywebview wraps the server in a native desktop window. All money as integer cents. Balances computed on read, never stored. Spanish UI labels, English identifiers.

## Architecture Decisions

| Decision | Choice | Alternative | Rationale |
|----------|--------|-------------|-----------|
| Multi-currency net worth | Per-currency totals on dashboard (USD line + NIO line) | Single converted total | Spec forbids exchange conversion in v1; per-currency is honest |
| Cross-currency transfers | Allowed, single `amount_cents` applies to both sides | Dual amount fields | Spec mandates single amount; user responsibility documented in UI hint |
| Transaction sort tiebreak | `ORDER BY date DESC, id DESC` | `date DESC` only | Deterministic ordering when dates match |
| Opening balance immutability | `opening_balance_cents` excluded from edit form; archive+recreate to change | Dedicated adjust endpoint | v1 simplicity; avoids balance reconciliation complexity |
| Transaction delete | Hard `DELETE` | Soft delete with flag | Transactions have no archival value; balances auto-recompute |
| Archived accounts in transfers | Reject new transfers to/from archived accounts at validation | Allow with warning | Prevents confusing balance changes on hidden accounts |
| DB table names | Spanish (`cuenta`, `movimiento`) matching domain | English | Matches UI language and user's mental model |
| Template engine | Jinja2 server-rendered + HTMX partials | SPA framework | No build step, simple, matches personal-app scope |

## Project Structure

```
FICE/
├── main.py                      # FastAPI app factory + pywebview launcher
├── requirements.txt
├── app/
│   ├── __init__.py              # create_app() factory
│   ├── db.py                    # Engine, session, SQLModel metadata
│   ├── models.py                # Cuenta, Movimiento tables
│   ├── services.py              # Balance computation, aggregation queries
│   ├── routes/
│   │   ├── accounts.py          # CRUD + HTMX partials
│   │   ├── transactions.py      # CRUD + filters + HTMX partials
│   │   └── dashboard.py         # Page + partials + /api/charts/* JSON
│   ├── templates/
│   │   ├── base.html            # Layout shell, nav, script includes
│   │   ├── dashboard.html       # Extends base, HTMX section containers
│   │   ├── accounts/
│   │   │   ├── list.html        # Extends base
│   │   │   └── form.html        # Create/edit form partial
│   │   ├── transactions/
│   │   │   ├── list.html        # Extends base, filter bar
│   │   │   └── form.html        # Create/edit form partial
│   │   └── partials/
│   │       ├── _net_worth.html
│   │       ├── _account_balances.html
│   │       ├── _month_summary.html
│   │       └── _recent_transactions.html
│   └── static/
│       ├── css/style.css
│       └── js/charts.js         # Chart.js init from JSON endpoints
└── data/                        # gitignored; fice.db created at runtime
```

## Database Schema

### `cuenta` (Account)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK, autoincrement |
| `name` | TEXT | NOT NULL |
| `type` | TEXT | NOT NULL, CHECK IN ('banco','efectivo','ahorro') |
| `currency` | TEXT | NOT NULL, CHECK IN ('USD','NIO') |
| `opening_balance_cents` | INTEGER | NOT NULL, DEFAULT 0 |
| `archived` | BOOLEAN | NOT NULL, DEFAULT FALSE |
| `created_at` | TEXT | NOT NULL, ISO-8601 |
| `updated_at` | TEXT | NOT NULL, ISO-8601 |

### `movimiento` (Transaction)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK, autoincrement |
| `account_id` | INTEGER | NOT NULL, FK → cuenta(id) |
| `type` | TEXT | NOT NULL, CHECK IN ('income','expense','transfer') |
| `amount_cents` | INTEGER | NOT NULL, CHECK > 0 |
| `description` | TEXT | NOT NULL, DEFAULT '' |
| `date` | DATE | NOT NULL (no time component) |
| `destination_account_id` | INTEGER | NULLABLE, FK → cuenta(id); required when type='transfer' |
| `created_at` | TEXT | NOT NULL, ISO-8601 |
| `updated_at` | TEXT | NOT NULL, ISO-8601 |

**Indexes**: `movimiento.account_id`, `movimiento.destination_account_id`, `movimiento.date`.

## Route Design

| Method | Path | Handler | Response |
|--------|------|---------|----------|
| GET | `/` | dashboard page | Full HTML |
| GET | `/partials/net-worth` | net worth section | HTML fragment |
| GET | `/partials/account-balances` | balances section | HTML fragment |
| GET | `/partials/month-summary` | month summary | HTML fragment |
| GET | `/partials/recent-transactions` | recent txns | HTML fragment |
| GET | `/api/charts/monthly-summary` | bar chart data | JSON |
| GET | `/api/charts/balance-distribution` | doughnut data | JSON |
| GET | `/api/charts/net-worth-trend` | line chart data | JSON |
| GET | `/accounts` | account list | Full HTML |
| GET | `/accounts/new` | create form | Full HTML |
| POST | `/accounts` | create account | Redirect / HX-Redirect |
| GET | `/accounts/{id}/edit` | edit form | Full HTML |
| PUT | `/accounts/{id}` | update name/archived | Redirect / HX-Redirect |
| DELETE | `/accounts/{id}` | archive (soft delete) | Redirect / HX-Redirect |
| GET | `/transactions` | txn list + filters | Full HTML |
| GET | `/transactions/new` | create form (?type=) | Full HTML |
| POST | `/transactions` | create txn | Redirect / HX-Redirect |
| GET | `/transactions/{id}/edit` | edit form | Full HTML |
| PUT | `/transactions/{id}` | update txn | Redirect / HX-Redirect |
| DELETE | `/transactions/{id}` | hard delete | Redirect / HX-Redirect |

## Data Flow: Balance Computation

```
Request → Route → services.compute_balance(account_id, session)
                      │
                      ├── account.opening_balance_cents
                      ├── SUM(amount) WHERE type='income' AND account_id=X
                      ├── SUM(amount) WHERE type='expense' AND account_id=X
                      ├── SUM(amount) WHERE type='transfer' AND destination_account_id=X
                      └── SUM(amount) WHERE type='transfer' AND account_id=X
                      │
                      └── return opening + income - expense + transfers_in - transfers_out
```

Four `COALESCE(SUM(...), 0)` queries per account. Acceptable for single-user, <100 accounts.

## HTMX Interaction Pattern

Full page loads render `base.html` + content template. HTMX partials return only the fragment HTML (no base layout). Detection: `HX-Request` header → return partial template. Form submissions use `hx-post`/`hx-put` and respond with `HX-Redirect` header to navigate after success.

## pywebview Integration

```python
# main.py
import threading, uvicorn, webview
from app import create_app

app = create_app()

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    webview.create_window("FICE", "http://127.0.0.1:8000", width=1200, height=800)
    # webview.start() blocks; window close → process exit → daemon thread dies → port released
```

Development: `uvicorn app:create_app --reload` (browser). Production: `python main.py` (desktop window).

## Error Handling

- **Validation**: Pydantic/SQLModel validators reject floats, negative amounts, invalid enums before DB hit. Forms re-render with inline error messages.
- **404**: FastAPI exception handler returns styled error page.
- **Transfer atomicity**: Single DB session transaction. If destination account missing or archived, session rolls back — no partial state.
- **HTMX errors**: Return HTTP 4xx with error HTML fragment; HTMX swaps it into the target container.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Balance computation, validation logic | pytest with in-memory SQLite |
| Integration | Route handlers, form submission, transfer atomicity | FastAPI TestClient + SQLite |
| Manual | pywebview window lifecycle, chart rendering | Run on Linux + Windows |

## Migration / Rollout

No migration required — greenfield. Database created via `SQLModel.metadata.create_all()` at startup. Future schema changes use Alembic (not in v1 scope).

## Open Questions

- [ ] Net-worth trend chart: how many historical data points? Proposal: daily snapshot for last 90 days, computed from transaction dates.
- [ ] Chart.js and HTMX: bundle locally or load from CDN? Local preferred for offline desktop use.
