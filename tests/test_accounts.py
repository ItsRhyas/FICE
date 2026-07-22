"""Integration tests for account management routes and services."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import create_app
from app.db import get_session
from app.models import Cuenta, Movimiento


@pytest.fixture(name="test_engine")
def test_engine_fixture():
    """Create an isolated in-memory SQLite engine per test.

    StaticPool keeps the in-memory database alive across the separate
    connections used by the test fixture and the TestClient request threads.
    """
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


@pytest.fixture(name="cuenta")
def cuenta_fixture(session: Session):
    """Create a basic active account."""
    cuenta = Cuenta(name="Billetera", type="efectivo", currency="NIO")
    session.add(cuenta)
    session.commit()
    session.refresh(cuenta)
    return cuenta


def test_create_account(client: TestClient):
    # POST to the canonical router path (/accounts/) to avoid the slash
    # redirect; the design URL remains /accounts and works in the browser.
    response = client.post(
        "/accounts/",
        data={
            "name": "BAC USD",
            "type": "banco",
            "currency": "USD",
            "opening_balance_cents": "100000",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["Location"] == "/accounts"

    list_response = client.get("/accounts")
    assert "BAC USD" in list_response.text
    assert "1000.00" in list_response.text


def test_create_account_rejects_float(client: TestClient):
    response = client.post(
        "/accounts",
        data={
            "name": "BAC USD",
            "type": "banco",
            "currency": "USD",
            "opening_balance_cents": "100.50",
        },
    )
    assert response.status_code == 422
    assert "número entero" in response.text


def test_create_account_rejects_invalid_type(client: TestClient):
    response = client.post(
        "/accounts",
        data={
            "name": "Bad",
            "type": "credit",
            "currency": "USD",
            "opening_balance_cents": "0",
        },
    )
    assert response.status_code == 422


def test_create_account_rejects_invalid_currency(client: TestClient):
    response = client.post(
        "/accounts",
        data={
            "name": "Bad",
            "type": "banco",
            "currency": "EUR",
            "opening_balance_cents": "0",
        },
    )
    assert response.status_code == 422


def test_edit_account_name(client: TestClient, cuenta: Cuenta):
    response = client.put(
        f"/accounts/{cuenta.id}",
        data={"name": "Billetera actualizada", "type": cuenta.type, "currency": cuenta.currency},
        follow_redirects=False,
    )
    assert response.status_code == 303

    detail = client.get(f"/accounts/{cuenta.id}")
    assert "Billetera actualizada" in detail.text


def test_reject_currency_change(client: TestClient, cuenta: Cuenta):
    response = client.put(
        f"/accounts/{cuenta.id}",
        data={"name": cuenta.name, "type": cuenta.type, "currency": "USD"},
    )
    assert response.status_code == 422
    assert "moneda no se puede cambiar" in response.text.lower()


def test_archive_and_unarchive(client: TestClient, cuenta: Cuenta):
    # Archive the account.
    response = client.put(
        f"/accounts/{cuenta.id}/archive",
        follow_redirects=False,
    )
    assert response.status_code == 303

    # Default list excludes archived accounts.
    list_response = client.get("/accounts")
    assert "Billetera" not in list_response.text

    # Explicit request includes archived accounts.
    archived_response = client.get("/accounts?include_archived=true")
    assert "Billetera" in archived_response.text

    # Unarchive and verify it reappears.
    client.put(f"/accounts/{cuenta.id}/archive", follow_redirects=False)
    list_response = client.get("/accounts")
    assert "Billetera" in list_response.text


def test_balance_computation_with_transactions(client: TestClient, session: Session, cuenta: Cuenta):
    # Opening balance is 0.
    expense = Movimiento(
        account_id=cuenta.id,
        type="expense",
        amount_cents=5000,
        description="Compra",
        date=date(2026, 7, 16),
    )
    session.add(expense)
    session.commit()

    detail = client.get(f"/accounts/{cuenta.id}")
    assert "-50.00" in detail.text

    income = Movimiento(
        account_id=cuenta.id,
        type="income",
        amount_cents=12000,
        description="Salario",
        date=date(2026, 7, 16),
    )
    session.add(income)
    session.commit()

    detail = client.get(f"/accounts/{cuenta.id}")
    assert "70.00" in detail.text


def test_balance_with_transfer(client: TestClient, session: Session, cuenta: Cuenta):
    destino = Cuenta(name="Ahorros", type="ahorro", currency="NIO")
    session.add(destino)
    session.commit()
    session.refresh(destino)

    income = Movimiento(
        account_id=cuenta.id,
        type="income",
        amount_cents=10000,
        description="Salario",
        date=date(2026, 7, 16),
    )
    transfer = Movimiento(
        account_id=cuenta.id,
        type="transfer",
        amount_cents=3000,
        description="Ahorro",
        date=date(2026, 7, 16),
        destination_account_id=destino.id,
    )
    session.add(income)
    session.add(transfer)
    session.commit()

    source_detail = client.get(f"/accounts/{cuenta.id}")
    assert "70.00" in source_detail.text

    dest_detail = client.get(f"/accounts/{destino.id}")
    assert "30.00" in dest_detail.text


def test_no_stored_balance_column(client: TestClient):
    """The response page is built from a computed balance, not a stored column."""
    response = client.get("/accounts")
    assert response.status_code == 200
    # This test mainly documents the design: no balance column exists in Cuenta.
    from app.models import Cuenta
    assert "balance" not in Cuenta.__table__.columns
