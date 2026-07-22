"""Business services for FICE.

Balance computation and future aggregation logic live here.
"""

from calendar import monthrange
from collections import defaultdict
from datetime import date as date_type
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlmodel import Session

from app.models import Cuenta, Movimiento


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_balance(account: Cuenta | int, session: Session) -> int:
    """Compute the current balance of an account from its transactions.

    Formula (per spec):
        opening_balance_cents
        + SUM(income)
        - SUM(expense)
        + SUM(transfers_in)
        - SUM(transfers_out)

    Transfers are recorded once with a source account (account_id) and a
    destination account (destination_account_id). The same amount is
    subtracted from the source and added to the destination.
    """
    if isinstance(account, int):
        cuenta = session.get(Cuenta, account)
        if cuenta is None:
            raise ValueError(f"Account {account} not found")
        account_id = cuenta.id
        opening_balance_cents = cuenta.opening_balance_cents
    else:
        account_id = account.id
        opening_balance_cents = account.opening_balance_cents

    income = _sum_amounts(session, account_id, "income")
    expense = _sum_amounts(session, account_id, "expense")
    transfers_in = _sum_transfers_in(session, account_id)
    transfers_out = _sum_amounts(session, account_id, "transfer")

    return opening_balance_cents + income - expense + transfers_in - transfers_out


def _sum_amounts(session: Session, account_id: int, txn_type: str) -> int:
    """Sum amount_cents for a given account and transaction type."""
    query = select(
        func.coalesce(func.sum(Movimiento.amount_cents), 0),
    ).where(
        Movimiento.account_id == account_id,
        Movimiento.type == txn_type,
    )
    result = session.scalar(query)
    return result or 0


def _sum_transfers_in(session: Session, account_id: int) -> int:
    """Sum amount_cents transferred into this account."""
    query = select(
        func.coalesce(func.sum(Movimiento.amount_cents), 0),
    ).where(
        Movimiento.destination_account_id == account_id,
        Movimiento.type == "transfer",
    )
    result = session.scalar(query)
    return result or 0


def _to_int(value: str | int | None, field_name: str) -> int:
    """Convert a form/query value to an integer, raising a clear error."""
    if value is None or value == "":
        raise ValueError(f"{field_name} is required")
    try:
        return int(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{field_name} must be an integer number of cents") from exc


def _to_date(value: str | date_type | None, field_name: str) -> date_type:
    """Convert a form/query value to a date, raising a clear error."""
    if value is None or value == "":
        raise ValueError(f"{field_name} is required")
    if isinstance(value, date_type):
        return value
    try:
        return date_type.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a date in YYYY-MM-DD format") from exc


def get_transactions(
    session: Session,
    account_id: int | str | None = None,
    type: str | None = None,
    from_date: str | date_type | None = None,
    to_date: str | date_type | None = None,
) -> list[Movimiento]:
    """Return transactions ordered by date DESC, id DESC, with optional filters."""
    query = select(Movimiento)

    if account_id is not None and account_id != "":
        query = query.where(Movimiento.account_id == _to_int(account_id, "account_id"))

    if type is not None and type != "":
        query = query.where(Movimiento.type == type)

    if from_date is not None and from_date != "":
        query = query.where(Movimiento.date >= _to_date(from_date, "from_date"))

    if to_date is not None and to_date != "":
        query = query.where(Movimiento.date <= _to_date(to_date, "to_date"))

    query = query.order_by(Movimiento.date.desc(), Movimiento.id.desc())
    return list(session.exec(query).scalars().all())


def record_transaction(session: Session, data: dict) -> Movimiento:
    """Create an income, expense, or transfer transaction atomically.

    `data` keys:
        - account_id (int or str)
        - type (str): income, expense, transfer
        - amount_cents (int or str): positive integer cents
        - description (str, optional)
        - date (date or str in YYYY-MM-DD)
        - destination_account_id (int or str, required for transfer)
    """
    try:
        account_id = _to_int(data.get("account_id"), "account_id")
        txn_type = data.get("type")
        amount_cents = _to_int(data.get("amount_cents"), "amount_cents")
        description = data.get("description", "")
        txn_date = _to_date(data.get("date"), "date")

        source = session.get(Cuenta, account_id)
        if source is None:
            raise ValueError("Source account not found")
        if source.archived:
            raise ValueError("Cannot record transactions for an archived account")

        kwargs: dict = {
            "account_id": account_id,
            "type": txn_type,
            "amount_cents": amount_cents,
            "description": description,
            "date": txn_date,
        }

        if txn_type == "transfer":
            destination_id = _to_int(
                data.get("destination_account_id"), "destination_account_id"
            )
            destination = session.get(Cuenta, destination_id)
            if destination is None:
                raise ValueError("Destination account not found")
            if destination.archived:
                raise ValueError("Cannot transfer to an archived account")
            kwargs["destination_account_id"] = destination_id

        movimiento = Movimiento(**kwargs)
        session.add(movimiento)
        session.commit()
        session.refresh(movimiento)
        return movimiento
    except Exception:
        session.rollback()
        raise


def update_transaction(session: Session, transaction_id: int, data: dict) -> Movimiento:
    """Edit a transaction's description, amount_cents, and date.

    The account, type, and destination (for transfers) are immutable in v1.
    """
    try:
        movimiento = session.get(Movimiento, transaction_id)
        if movimiento is None:
            raise ValueError("Transaction not found")

        if "description" in data:
            movimiento.description = data["description"]
        if "amount_cents" in data and data["amount_cents"] not in (None, ""):
            movimiento.amount_cents = _to_int(data["amount_cents"], "amount_cents")
        if "date" in data and data["date"] not in (None, ""):
            movimiento.date = _to_date(data["date"], "date")

        movimiento.updated_at = _iso_now()
        session.add(movimiento)
        session.commit()
        session.refresh(movimiento)
        return movimiento
    except Exception:
        session.rollback()
        raise


def delete_transaction(session: Session, transaction_id: int) -> None:
    """Hard delete a transaction and its effect on balances."""
    movimiento = session.get(Movimiento, transaction_id)
    if movimiento is None:
        raise ValueError("Transaction not found")
    session.delete(movimiento)
    session.commit()


def _active_account_ids(session: Session) -> set[int]:
    """Return IDs of all non-archived accounts."""
    rows = session.exec(
        select(Cuenta.id).where(Cuenta.archived == False)  # noqa: E712
    ).scalars().all()
    return {row for row in rows}


def _compute_active_balance(account: Cuenta, session: Session, active_ids: set[int]) -> int:
    """Compute balance using only transactions between active accounts."""
    balance = account.opening_balance_cents

    for tx in session.exec(
        select(Movimiento).where(Movimiento.account_id == account.id)
    ).scalars().all():
        # Ignore transfers whose destination is archived.
        if tx.destination_account_id is not None and tx.destination_account_id not in active_ids:
            continue
        if tx.type == "income":
            balance += tx.amount_cents
        elif tx.type == "expense":
            balance -= tx.amount_cents
        elif tx.type == "transfer":
            balance -= tx.amount_cents

    for tx in session.exec(
        select(Movimiento).where(
            Movimiento.destination_account_id == account.id,
            Movimiento.type == "transfer",
        )
    ).scalars().all():
        # Only count transfers coming from active accounts.
        if tx.account_id in active_ids:
            balance += tx.amount_cents

    return balance


def _active_transactions_query(session: Session):
    """Return a query for transactions that involve only active accounts."""
    active_ids = _active_account_ids(session)
    if not active_ids:
        return select(Movimiento).where(False)

    return (
        select(Movimiento)
        .where(Movimiento.account_id.in_(active_ids))
        .where(
            (Movimiento.destination_account_id.is_(None))
            | (Movimiento.destination_account_id.in_(active_ids))
        )
    )


def get_net_worth(session: Session) -> dict[str, int]:
    """Return per-currency totals for all non-archived accounts.

    Multi-currency balances are kept separate; no exchange conversion is
    performed.
    """
    active_accounts = session.exec(
        select(Cuenta).where(Cuenta.archived == False)  # noqa: E712
    ).scalars().all()
    active_ids = {a.id for a in active_accounts}

    totals = {"USD": 0, "NIO": 0}
    for account in active_accounts:
        totals[account.currency] += _compute_active_balance(account, session, active_ids)
    return totals


def get_account_balances(session: Session) -> list[dict]:
    """Return non-archived accounts with their computed balances."""
    active_accounts = session.exec(
        select(Cuenta)
        .where(Cuenta.archived == False)  # noqa: E712
        .order_by(Cuenta.name)
    ).scalars().all()
    active_ids = {a.id for a in active_accounts}

    return [
        {
            "account": account,
            "balance": _compute_active_balance(account, session, active_ids),
            "currency": account.currency,
        }
        for account in active_accounts
    ]


def get_month_summary(session: Session, year: int, month: int) -> dict[str, int]:
    """Return total income and expense for a given calendar month.

    Only transactions on non-archived accounts are included. Transfers are
    excluded because they move value between accounts rather than create it.
    """
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    active_ids = _active_account_ids(session)
    if not active_ids:
        return {"income": 0, "expense": 0}

    income = session.exec(
        select(func.coalesce(func.sum(Movimiento.amount_cents), 0))
        .select_from(Movimiento)
        .where(Movimiento.type == "income")
        .where(Movimiento.date >= start)
        .where(Movimiento.date <= end)
        .where(Movimiento.account_id.in_(active_ids))
    ).scalars().first() or 0

    expense = session.exec(
        select(func.coalesce(func.sum(Movimiento.amount_cents), 0))
        .select_from(Movimiento)
        .where(Movimiento.type == "expense")
        .where(Movimiento.date >= start)
        .where(Movimiento.date <= end)
        .where(Movimiento.account_id.in_(active_ids))
    ).scalars().first() or 0

    return {"income": int(income), "expense": int(expense)}


def get_recent_transactions(session: Session, limit: int = 10) -> list[Movimiento]:
    """Return the most recent active-account transactions."""
    query = (
        _active_transactions_query(session)
        .order_by(Movimiento.date.desc(), Movimiento.id.desc())
        .limit(limit)
    )
    return list(session.exec(query).scalars().all())


def _month_date_range(today: date, months_back: int) -> list[tuple[int, int]]:
    """Return a list of (year, month) tuples for the trailing months."""
    result = []
    year, month = today.year, today.month
    for _ in range(months_back):
        result.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(result))


def get_monthly_summary_chart(session: Session, months: int = 12) -> list[dict]:
    """Return income vs expense totals for the trailing N months."""
    today = date.today()
    return [
        {
            "month": f"{year}-{month:02d}",
            **get_month_summary(session, year, month),
        }
        for year, month in _month_date_range(today, months)
    ]


def get_balance_distribution_chart(session: Session) -> list[dict]:
    """Return per-account balances for the doughnut chart."""
    return [
        {
            "label": item["account"].name,
            "balance": item["balance"],
            "currency": item["currency"],
        }
        for item in get_account_balances(session)
    ]


def get_net_worth_trend(session: Session, days: int = 90) -> list[dict]:
    """Return daily per-currency net-worth snapshots for the trailing N days.

    Each data point represents the net worth at the end of that day, computed
    from opening balances plus all active-to-active transactions dated on or
    before that day.
    """
    active_accounts = session.exec(
        select(Cuenta).where(Cuenta.archived == False)  # noqa: E712
    ).scalars().all()
    active_ids = {a.id for a in active_accounts}

    today = date.today()
    start_date = today - timedelta(days=days - 1)

    transactions = session.exec(
        select(Movimiento)
        .where(Movimiento.account_id.in_(active_ids))
        .where(
            (Movimiento.destination_account_id.is_(None))
            | (Movimiento.destination_account_id.in_(active_ids))
        )
        .order_by(Movimiento.date)
    ).scalars().all()

    tx_by_date: dict[date, list[Movimiento]] = defaultdict(list)
    for tx in transactions:
        tx_by_date[tx.date].append(tx)

    balances = {account.id: account.opening_balance_cents for account in active_accounts}

    # Apply transactions dated before the trend window so the first data point
    # reflects the true net worth at the start of the window.
    for tx in transactions:
        if tx.date >= start_date:
            continue
        if tx.type == "income":
            balances[tx.account_id] += tx.amount_cents
        elif tx.type == "expense":
            balances[tx.account_id] -= tx.amount_cents
        elif tx.type == "transfer":
            balances[tx.account_id] -= tx.amount_cents
            if tx.destination_account_id in balances:
                balances[tx.destination_account_id] += tx.amount_cents

    trend = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        for tx in tx_by_date.get(day, []):
            if tx.type == "income":
                balances[tx.account_id] += tx.amount_cents
            elif tx.type == "expense":
                balances[tx.account_id] -= tx.amount_cents
            elif tx.type == "transfer":
                balances[tx.account_id] -= tx.amount_cents
                if tx.destination_account_id in balances:
                    balances[tx.destination_account_id] += tx.amount_cents

        totals = {"USD": 0, "NIO": 0}
        for account in active_accounts:
            totals[account.currency] += balances[account.id]

        trend.append({"date": day.isoformat(), "USD": totals["USD"], "NIO": totals["NIO"]})

    return trend
