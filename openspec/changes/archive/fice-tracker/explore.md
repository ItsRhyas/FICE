# Exploration: FICE — Personal Finance Tracker

> Greenfield exploration. No existing code to read. This document analyzes the
> domain, evaluates tech stacks, and proposes a minimal first slice for the
> orchestrator to feed into `sdd-propose`.

---

## Current State

**Project state**: Empty git repository. No source code, no `package.json`,
no `requirements.txt`, no `go.mod`. Only `openspec/` (config + empty
`specs/`), `.git/`, and `.atl/` exist.

**What the user wants**: A simple, single-user personal finance tracker
covering four concepts:

- **Ingresos** — money coming in (salary, transfers received, refunds, etc.)
- **Ahorros** — savings (modeled as either a type of account or a transfer to one)
- **Salidas** — money going out (food, rent, subscriptions, etc.)
- **Cuentas** — accounts overview (bank, cash, savings, credit, etc.)

**Constraints (from `openspec/config.yaml` and `sdd-init`)**:
- Personal-use scope. No multi-user, no auth, no roles.
- `strict_tdd: false`. `testing: { runner: none, coverage: false, linter: false, type_checker: false, formatter: false }`.
- Persistence: `hybrid` (OpenSpec files + Engram memory).
- Conversation language: Spanish. Artifacts default to English.

**Reference init memory**: `obs-23c26aa3c72b711b` (#238).

---

## Domain Model

For a single-user personal finance tool, the domain collapses to **two
entities + one optional tag**. Trying to model more is over-engineering for
a v1.

### Core entities

**Account** (`Cuenta`)
- `id` (uuid or autoincrement)
- `name` (e.g., "BBVA Nómina", "Efectivo", "Ahorro USD")
- `type` (enum: `checking`, `savings`, `cash`, `credit`, `other`)
- `currency` (default `MXN` for now; single-currency v1)
- `opening_balance` (decimal, optional — needed to anchor historical balance)
- `archived` (bool, soft delete)
- `created_at`, `updated_at`

**Transaction** (`Movimiento`) — the heart of the system
- `id`
- `type` (enum: `income` | `expense` | `transfer`)
- `amount` (decimal, always positive; sign is implied by `type`)
- `date` (when the movement actually happened, not when it was recorded)
- `account_id` (the source account)
- `destination_account_id` (nullable; only set when `type = transfer`)
- `category` (free-form string, optional — e.g., "Comida", "Salario")
- `description` (short note, optional)
- `created_at`, `updated_at`

**Category** (`Categoría`) — optional, defer to v1.1
- Free-form string on the transaction is enough for v1. A separate table
  only earns its keep when you want budgets, color coding, or analytics
  per category. Not in MVP.

### Modeling "Ahorros" (the tricky one)

"Ahorros" is not a separate entity in clean personal-finance domain
modeling. It is one of these:

1. **A type of account** — a savings account at a bank is just another
   `Cuenta` with `type = savings`. The user sees it in the accounts list.
2. **A transfer** — moving money from a checking account to a savings
   account is a `type = transfer` transaction. Both balances move.
3. **A goal** (amount target + deadline) — defer to v1.1. Tracking actual
   progress is the same as a savings account + filtered view.

**Recommended approach for v1**: treat savings as **a type of account +
inter-account transfers**. Zero new entities, fully expressive, matches
how the user already thinks about it ("the money is in the savings
account").

### Derived values (computed, not stored)

- **Account balance** = `opening_balance + SUM(income) - SUM(expense) +
  SUM(transfers_in) - SUM(transfers_out)`. Never stored.
- **Net worth** = `SUM(balance across all non-archived accounts)`. Computed
  on read.
- **Monthly summary** = `SUM(income) - SUM(expense)` for a given month
  and (optionally) account.

Storing derived values is a common bug source. Compute them.

### Decimal handling

Money is decimal. Use `DECIMAL(12, 2)` in SQLite (or store cents as
integers — also valid, simpler arithmetic). **Do not use floats for money.**
This is a non-negotiable.

---

## Affected Areas

Greenfield — there is nothing to modify yet. The areas that will exist
after the first slice:

- `app/` (or root) — application code
  - `models.py` (or equivalent) — Account, Transaction
  - `db.py` — SQLite connection, migrations
  - `routes/` — HTTP handlers (accounts, transactions, dashboard)
  - `templates/` — Jinja2 / Go template / etc.
  - `static/` — CSS, minimal JS
  - `main.py` (or `main.go`) — entry point
- `data/fice.db` — SQLite database file (gitignored)
- `requirements.txt` / `go.mod` / `package.json` — dependencies
- `README.md` — how to run it
- `openspec/specs/finance/spec.md` — the source-of-truth spec (created in `sdd-spec`)

---

## Approaches

### Option A — Python + FastAPI + SQLite + Jinja2 + HTMX (server-rendered, interactive)

**Stack**: Python 3.11+, FastAPI, SQLModel (or SQLAlchemy 2.x), SQLite,
Jinja2 templates, HTMX for interactivity, PicoCSS or simple hand-rolled
CSS for styling.

- **Pros**
  - FastAPI is the most ergonomic web framework for this scale — type-safe
    routes, automatic validation, auto-generated OpenAPI docs.
  - SQLModel = Pydantic + SQLAlchemy in one; one model class for both DB
    row and HTTP request/response.
  - Jinja2 + HTMX gives SPA-like interactivity (form submits, partial
    updates) without a JS build pipeline, no `node_modules`, no bundler.
  - SQLite is the right call for single-user, single-device.
  - Python's data tooling (pandas, matplotlib) is unmatched if/when
    reports or charts are added later.
  - Easy to deploy: `uvicorn main:app` behind a reverse proxy, or even
    a `systemd` service.
  - Most likely the user's comfort zone for a personal project.
- **Cons**
  - Requires Python runtime (not a single binary).
  - Slight friction with the GIL for parallel requests — irrelevant for
    one user.
- **Effort**: **Low** — fastest path to a working app.

### Option B — TypeScript / Node + Express + SQLite + Vanilla JS (or React)

**Stack**: Node 20+, TypeScript, Express (or Fastify), better-sqlite3,
a static HTML/JS frontend (or React + Vite if a richer UI is wanted).

- **Pros**
  - Most familiar full-stack combo on the planet.
  - TypeScript end-to-end.
  - `better-sqlite3` is synchronous and extremely fast for embedded use.
  - React gives the richest UI if the user wants dashboards with charts.
- **Cons**
  - `node_modules` and a JS toolchain for what is fundamentally a
    personal CRUD app — high ceremony for low benefit.
  - Without SSR, the user has to either build a Vite/React app (more
    files, build step) or live with `fetch()` boilerplate.
  - Adding charts later means picking a lib (Recharts, Chart.js) and
    rebuilding.
  - No `pandas`-equivalent for ad-hoc data analysis.
- **Effort**: **Medium** — more moving parts than Option A for the same
  surface area.

### Option C — Go + SQLite + `html/template` (single binary)

**Stack**: Go 1.22+, `modernc.org/sqlite` (pure Go, no CGO), standard
`net/http`, standard `html/template`, minimal CSS.

- **Pros**
  - **Single binary distribution** — `go build` produces one file. Copy it
    to any server, run it. No runtime, no `node_modules`, no venv.
  - Fastest runtime, lowest memory, smallest attack surface.
  - Compile-time type safety across DB and HTTP.
  - Templates render server-side, no build pipeline.
  - `modernc.org/sqlite` works on any platform without a C toolchain.
- **Cons**
  - More verbose than Python. Every struct tag, every `if err != nil`.
  - `html/template` is functional but bare; no layouts without manual
    composition, no macros.
  - No data-analysis story. Charts and reports would need another tool.
  - Steeper if the user does not already know Go.
- **Effort**: **Medium** — straightforward, but more lines of code than
  Option A.

### Option D — Rust + Tauri (native desktop)

- **Pros**: native, fast, secure.
- **Cons**: massive overkill. Slow to build, complex toolchain, much
  higher cognitive load.
- **Verdict**: **Reject** for v1. A web app on localhost is 90% of the
  UX for 10% of the effort.

### Option E — Pure stdlib Python (no framework)

- **Pros**: zero dependencies.
- **Cons**: reinventing routing, validation, templating, static-file
  serving. A regression to the 2000s.
- **Verdict**: **Reject**. FastAPI costs almost nothing and gives a
  real foundation.

---

## Comparison Table

| Criterion                | A: Python+FastAPI+HTMX | B: TS+Express+React  | C: Go+SQLite            | D: Rust+Tauri |
|--------------------------|------------------------|----------------------|--------------------------|---------------|
| Time to first working app| **Hours**              | 1–2 days             | 1 day                    | 1–2 weeks     |
| Lines of code (v1)       | **~400–600**           | ~800–1200            | ~600–900                 | ~1500+        |
| Single binary            | No (Python runtime)    | No (Node runtime)    | **Yes**                  | Yes (executable) |
| Deployment simplicity    | `uvicorn` + venv       | node + node_modules  | **scp + run**            | Install .app/.exe |
| Data analysis later      | **Best (pandas, etc.)**| OK                   | Weakest                  | OK            |
| Learning curve           | **Lowest**             | Medium               | Medium-High              | High          |
| Maintainability (1 user) | **High**               | Medium               | High                     | High          |
| Build pipeline / tooling | None                   | Vite/npm             | None                     | Cargo + Node  |

---

## Recommendation

**Pick Option A: Python + FastAPI + SQLite + Jinja2 + HTMX.**

Reasons, in order of weight:

1. **Speed to value.** A working v1 (CRUD accounts, CRUD transactions,
   dashboard with balances and monthly summary) is achievable in a
   single focused session. That is the entire point of a personal tool.
2. **Right size for the problem.** One user, localhost, < 10 entities.
   Single binary deployment is a nice-to-have, not a need. The Python
   runtime is already on every dev machine the user will touch.
3. **Future-proofing without commitment.** When the user eventually wants
   charts, CSV reports, or a budget view, Python's data ecosystem is the
   best in class. Adding a `/reports` page with pandas is one file.
4. **HTMX is the right interactivity layer.** It gives partial updates,
   inline editing, and form validation without a SPA build. The
   cognitive load stays near zero.
5. **Stack is reversible.** If the user later wants a desktop app, the
   FastAPI app can be embedded in a Tauri shell with almost no change.

**Concrete dependency list (for the proposal phase):**
- `fastapi`
- `uvicorn[standard]`
- `sqlmodel` (or `sqlalchemy` + `pydantic` if more control is wanted)
- `jinja2`
- `python-multipart` (for form handling)
- `htmx` (single JS file, no build step)
- `pico-css` (single CSS file, optional)

That's it. Six lines of dependencies.

**Stack-agnostic architectural decisions to lock in early (carry to
`sdd-design`):**
- Money is stored as integer cents. Floats are banned.
- Balances are computed, never stored.
- Soft-delete accounts via `archived` flag, never `DELETE`.
- All money operations are server-side. The browser only renders.
- `datetime` for `date` and timestamps; store as ISO-8601 strings in
  SQLite, parse in Python with `datetime.fromisoformat`.
- Locale: Spanish UI strings (the user's domain language), English code
  identifiers per the SDD language contract.

---

## Minimal First Slice (MVP)

A single proposal that gives real value end-to-end:

1. **Account management**
   - List accounts with current balance.
   - Create, edit, archive an account.
   - Opening balance captured at creation.

2. **Transaction recording**
   - Record an income or expense against any account.
   - Record a transfer between two accounts (one transaction, two
     balance effects).
   - List transactions, filter by date range, account, and type.

3. **Dashboard (one page)**
   - Total net worth.
   - Per-account balance list.
   - This month's income, expense, net.
   - Last 10 transactions.

4. **Out of scope for v1** (explicit non-goals to keep scope honest):
   - Authentication / multi-user.
   - Recurring transactions.
   - Budgets.
   - Multi-currency.
   - CSV import (CSV **export** is fair game, but defer).
   - Charts (defer to v1.1; tables first).
   - Mobile app / PWA (responsive web is enough).
   - Cloud sync / backup (SQLite file in the repo is the backup story).

---

## Risks

- **No tests configured.** `config.yaml` has all testing layers off. The
  user has explicitly opted out of TDD. The risk is silent regressions
  in money math. **Mitigation**: at minimum, write 3–5 hand-rolled
  sanity tests for the balance-calculation function before declaring
  v1 done. Not formal TDD, just belt-and-suspenders for the only part
  of the system where bugs cost real money.
- **No auth.** The app assumes localhost or a trusted network. If the
  user later exposes it to the internet, they need to add auth or a
  reverse proxy with basic auth. **Document this prominently in the
  README.**
- **Decimal precision.** Storing money as floats is a classic
  bug. The proposal MUST mandate integer cents.
- **Time zone bugs.** A transaction dated "2026-07-16" entered at
  23:55 local time but logged at 00:05 UTC will land in the wrong day.
  Use the user's local date as input, store as naive `date` (not
  `datetime`) in the DB. The proposal should call this out.
- **Scope creep.** The temptation to add categories, budgets, charts,
  and CSV import on day one is real. The MVP list above is the
  contract — anything outside it waits.
- **Stack reversal cost is non-zero.** If the user later wants Go, the
  Python work is not wasted (the domain model and specs are language-
  agnostic), but the code is. Low risk, but worth flagging.

---

## Open Questions for the User (orchestrator to ask)

Only one matters enough to ask before `sdd-propose`:

1. **Currency** — Is this a single-currency (MXN) personal tracker, or
   does the user have accounts in more than one currency? (Affects
   whether v1 needs a `currency` column at all, or just a global
   setting.)

Everything else can be decided in `sdd-propose` / `sdd-spec`.

---

## Ready for Proposal

**Yes.** The orchestrator can launch `sdd-propose` for change
`fice-tracker` with:

- **Topic**: build v1 of the personal finance tracker.
- **Recommended stack**: Python + FastAPI + SQLite + Jinja2 + HTMX.
- **Scope**: account CRUD, transaction CRUD, dashboard, all in MVP.
- **Open question to surface to the user first**: single vs. multi
  currency. The orchestrator should ask this before `sdd-propose`
  writes anything user-facing, since it changes the schema and the
  README.
