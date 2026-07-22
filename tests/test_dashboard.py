"""Integration tests for the dashboard routes and aggregation services."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import create_app
from app.db import get_session
from app.models import Cuenta, Movimiento
from app.services import (
    get_account_balances,
    get_month_summary,
    get_net_worth,
    get_net_worth_trend,
    get_recent_transactions,
)


@pytest.fixture(name="test_engine")
def test_engine_fixture():
    """Create an isolated in-memory SQLite engine per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine


@pytest.fixture(name="session")
def session_fixture(test_engine):
    """Yield a fresh session on the in-memory test engine."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(test_engine):
    """FastAPI TestClient with the DB dependency overridden to in-memory SQLite."""
    def _override_get_session():
        with Session(test_engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_get_session

    with TestClient(app) as client:
        yield client


def _create_account(session: Session, name: str, currency: str, opening: int = 0, archived: bool = False):
    cuenta = Cuenta(
        name=name,
        type="banco",
        currency=currency,
        opening_balance_cents=opening,
        archived=archived,
    )
    session.add(cuenta)
    session.commit()
    session.refresh(cuenta)
    return cuenta


def _create_income(session: Session, account_id: int, amount: int, txn_date: date, description: str = "Ingreso"):
    mov = Movimiento(
        account_id=account_id,
        type="income",
        amount_cents=amount,
        description=description,
        date=txn_date,
    )
    session.add(mov)
    session.commit()
    session.refresh(mov)
    return mov


def _create_expense(session: Session, account_id: int, amount: int, txn_date: date, description: str = "Egreso"):
    mov = Movimiento(
        account_id=account_id,
        type="expense",
        amount_cents=amount,
        description=description,
        date=txn_date,
    )
    session.add(mov)
    session.commit()
    session.refresh(mov)
    return mov


def _create_transfer(session: Session, source_id: int, dest_id: int, amount: int, txn_date: date):
    mov = Movimiento(
        account_id=source_id,
        type="transfer",
        amount_cents=amount,
        description="Transferencia",
        date=txn_date,
        destination_account_id=dest_id,
    )
    session.add(mov)
    session.commit()
    session.refresh(mov)
    return mov


# ---------------------------------------------------------------------------
# Service-level aggregation tests
# ---------------------------------------------------------------------------


def test_net_worth_per_currency(session: Session):
    usd = _create_account(session, "BAC USD", "USD", opening=100000)
    nio = _create_account(session, "BAC NIO", "NIO", opening=500000)

    assert get_net_worth(session) == {"USD": 100000, "NIO": 500000}


def test_account_balances_exclude_archived(session: Session):
    active = _create_account(session, "Activa", "NIO", opening=10000)
    archived = _create_account(session, "Archivada", "NIO", opening=20000, archived=True)

    balances = get_account_balances(session)
    assert len(balances) == 1
    assert balances[0]["account"].id == active.id


def test_month_summary_computes_income_and_expense(session: Session):
    cuenta = _create_account(session, "Gastos", "NIO")
    today = date.today()

    _create_income(session, cuenta.id, 500000, today, "Salario")
    _create_expense(session, cuenta.id, 300000, today, "Compra")

    summary = get_month_summary(session, today.year, today.month)
    assert summary["income"] == 500000
    assert summary["expense"] == 300000


def test_recent_transactions_limited_and_ordered(session: Session):
    cuenta = _create_account(session, "Cuenta", "NIO")
    today = date.today()

    for i in range(15):
        _create_income(session, cuenta.id, 1000, today - timedelta(days=i), f"Mov {i}")

    recent = get_recent_transactions(session, limit=10)
    assert len(recent) == 10
    # Most recent first.
    assert recent[0].description == "Mov 0"
    assert recent[-1].description == "Mov 9"


def test_archived_account_excluded_from_net_worth(session: Session):
    active = _create_account(session, "Activa", "USD", opening=100000)
    archived = _create_account(session, "Archivada", "USD", opening=50000, archived=True)

    assert get_net_worth(session) == {"USD": 100000, "NIO": 0}


def test_archived_destination_transfer_ignored(session: Session):
    active = _create_account(session, "Activa", "USD", opening=100000)
    dest = _create_account(session, "Destino", "USD", opening=0)

    _create_transfer(session, active.id, dest.id, 20000, date.today())

    # Both active: transfer is counted.
    assert get_net_worth(session) == {"USD": 100000, "NIO": 0}

    # Archive destination: active account should recover the transferred amount.
    dest.archived = True
    session.add(dest)
    session.commit()

    assert get_net_worth(session) == {"USD": 100000, "NIO": 0}


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------


def test_dashboard_page_returns_200(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "Dashboard" in response.text


def test_dashboard_route_alias(client: TestClient):
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Dashboard" in response.text


def test_dashboard_shows_net_worth(client: TestClient, session: Session):
    _create_account(session, "BAC USD", "USD", opening=250000)

    response = client.get("/")
    assert response.status_code == 200
    assert "2500.00" in response.text
    assert "Patrimonio" in response.text


def test_dashboard_shows_account_balances(client: TestClient, session: Session):
    _create_account(session, "Billetera", "NIO", opening=50000)

    response = client.get("/")
    assert response.status_code == 200
    assert "Billetera" in response.text
    assert "500.00" in response.text


def test_dashboard_shows_month_summary(client: TestClient, session: Session):
    cuenta = _create_account(session, "Cuenta", "NIO")
    _create_income(session, cuenta.id, 100000, date.today())
    _create_expense(session, cuenta.id, 40000, date.today())

    response = client.get("/")
    assert response.status_code == 200
    assert "Ingresos" in response.text
    assert "Egresos" in response.text
    assert "1000.00" in response.text
    assert "400.00" in response.text


def test_dashboard_shows_recent_transactions(client: TestClient, session: Session):
    cuenta = _create_account(session, "Cuenta", "NIO")
    _create_income(session, cuenta.id, 10000, date.today(), "Depósito")

    response = client.get("/")
    assert response.status_code == 200
    assert "Últimos movimientos" in response.text
    assert "Depósito" in response.text


def test_partial_net_worth(client: TestClient, session: Session):
    _create_account(session, "USD Cuenta", "USD", opening=100000)

    response = client.get("/partials/net-worth", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "1000.00" in response.text
    assert "USD" in response.text


def test_partial_account_balances(client: TestClient, session: Session):
    _create_account(session, "NIO Cuenta", "NIO", opening=25000)

    response = client.get("/partials/account-balances", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "NIO Cuenta" in response.text
    assert "250.00" in response.text


def test_partial_month_summary(client: TestClient, session: Session):
    cuenta = _create_account(session, "Cuenta", "NIO")
    _create_income(session, cuenta.id, 200000, date.today())

    response = client.get("/partials/month-summary", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "Ingresos" in response.text
    assert "2000.00" in response.text


def test_partial_recent_transactions(client: TestClient, session: Session):
    cuenta = _create_account(session, "Cuenta", "NIO")
    _create_expense(session, cuenta.id, 15000, date.today(), "Cena")

    response = client.get("/partials/recent-transactions", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "Cena" in response.text
    assert "150.00" in response.text


# ---------------------------------------------------------------------------
# Chart JSON endpoints
# ---------------------------------------------------------------------------


def test_chart_monthly_summary_returns_data(client: TestClient, session: Session):
    cuenta = _create_account(session, "Cuenta", "NIO")
    today = date.today()
    _create_income(session, cuenta.id, 100000, today)
    _create_expense(session, cuenta.id, 30000, today)

    response = client.get("/api/charts/monthly-summary")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 12
    current_month = f"{today.year}-{today.month:02d}"
    current = next((item for item in data if item["month"] == current_month), None)
    assert current is not None
    assert current["income"] == 100000
    assert current["expense"] == 30000


def test_chart_balance_distribution_returns_data(client: TestClient, session: Session):
    _create_account(session, "Ahorros", "NIO", opening=50000)

    response = client.get("/api/charts/balance-distribution")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["label"] == "Ahorros"
    assert data[0]["balance"] == 50000
    assert data[0]["currency"] == "NIO"


def test_chart_net_worth_trend_returns_data(client: TestClient, session: Session):
    _create_account(session, "Cuenta", "USD", opening=100000)

    response = client.get("/api/charts/net-worth-trend")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 90
    assert data[0]["date"] <= data[-1]["date"]
    assert data[-1]["USD"] == 100000


def test_net_worth_trend_includes_transactions(session: Session):
    cuenta = _create_account(session, "Cuenta", "USD", opening=0)
    today = date.today()

    _create_income(session, cuenta.id, 50000, today)

    trend = get_net_worth_trend(session, days=7)
    assert trend[-1]["USD"] == 50000


def test_net_worth_trend_includes_transactions_before_window(session: Session):
    cuenta = _create_account(session, "Cuenta", "USD", opening=0)
    today = date.today()

    old_income = _create_income(session, cuenta.id, 75000, today - timedelta(days=100))
    recent_income = _create_income(session, cuenta.id, 25000, today)

    trend = get_net_worth_trend(session, days=7)
    # The starting point of the trend includes the old transaction.
    assert trend[0]["USD"] == 75000
    # The final point includes both transactions.
    assert trend[-1]["USD"] == 100000
