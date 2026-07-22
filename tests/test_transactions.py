"""Integration tests for transaction routes and services."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app import create_app
from app.db import get_session
from app.models import Cuenta, Movimiento
from app.services import (
    compute_balance,
    delete_transaction,
    get_transactions,
    record_transaction,
    update_transaction,
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


@pytest.fixture(name="cuenta")
def cuenta_fixture(session: Session):
    """Create a basic active account."""
    cuenta = Cuenta(name="Billetera", type="efectivo", currency="NIO")
    session.add(cuenta)
    session.commit()
    session.refresh(cuenta)
    return cuenta


@pytest.fixture(name="destino")
def destino_fixture(session: Session):
    """Create a second active account."""
    cuenta = Cuenta(name="Ahorros", type="ahorro", currency="NIO")
    session.add(cuenta)
    session.commit()
    session.refresh(cuenta)
    return cuenta


def test_record_income_increases_balance(session: Session, cuenta: Cuenta):
    record_transaction(
        session,
        {
            "account_id": cuenta.id,
            "type": "income",
            "amount_cents": 200000,
            "description": "Salario",
            "date": date(2026, 7, 16),
        },
    )
    assert compute_balance(cuenta, session) == 200000


def test_record_expense_decreases_balance(session: Session, cuenta: Cuenta):
    record_transaction(
        session,
        {
            "account_id": cuenta.id,
            "type": "expense",
            "amount_cents": 30000,
            "description": "Compra",
            "date": date(2026, 7, 16),
        },
    )
    assert compute_balance(cuenta, session) == -30000


def test_transfer_updates_both_balances(session: Session, cuenta: Cuenta, destino: Cuenta):
    record_transaction(
        session,
        {
            "account_id": cuenta.id,
            "type": "income",
            "amount_cents": 100000,
            "description": "Salario",
            "date": date(2026, 7, 16),
        },
    )
    record_transaction(
        session,
        {
            "account_id": cuenta.id,
            "type": "transfer",
            "amount_cents": 20000,
            "description": "Ahorro",
            "date": date(2026, 7, 16),
            "destination_account_id": destino.id,
        },
    )
    assert compute_balance(cuenta, session) == 80000
    assert compute_balance(destino, session) == 20000


def test_reject_same_account_transfer(session: Session, cuenta: Cuenta):
    with pytest.raises(ValueError):
        record_transaction(
            session,
            {
                "account_id": cuenta.id,
                "type": "transfer",
                "amount_cents": 10000,
                "description": "Auto transfer",
                "date": date(2026, 7, 16),
                "destination_account_id": cuenta.id,
            },
        )


def test_reject_transfer_to_archived_account(session: Session, cuenta: Cuenta, destino: Cuenta):
    destino.archived = True
    session.add(destino)
    session.commit()

    with pytest.raises(ValueError, match="archived"):
        record_transaction(
            session,
            {
                "account_id": cuenta.id,
                "type": "transfer",
                "amount_cents": 10000,
                "description": "Ahorro",
                "date": date(2026, 7, 16),
                "destination_account_id": destino.id,
            },
        )


def test_atomic_rollback_on_invalid_destination(session: Session, cuenta: Cuenta):
    record_transaction(
        session,
        {
            "account_id": cuenta.id,
            "type": "income",
            "amount_cents": 100000,
            "description": "Salario",
            "date": date(2026, 7, 16),
        },
    )

    with pytest.raises(ValueError):
        record_transaction(
            session,
            {
                "account_id": cuenta.id,
                "type": "transfer",
                "amount_cents": 20000,
                "description": "Ahorro",
                "date": date(2026, 7, 16),
                "destination_account_id": 99999,
            },
        )

    # Source balance unchanged because the transfer rolled back.
    assert compute_balance(cuenta, session) == 100000
    # No transfer row persisted.
    rows = session.exec(
        select(Movimiento).where(Movimiento.type == "transfer")
    ).all()
    assert len(rows) == 0


def test_reject_negative_income_amount(session: Session, cuenta: Cuenta):
    with pytest.raises(ValueError):
        record_transaction(
            session,
            {
                "account_id": cuenta.id,
                "type": "income",
                "amount_cents": -100,
                "description": "Bad",
                "date": date(2026, 7, 16),
            },
        )


def test_reject_negative_expense_amount(session: Session, cuenta: Cuenta):
    with pytest.raises(ValueError):
        record_transaction(
            session,
            {
                "account_id": cuenta.id,
                "type": "expense",
                "amount_cents": -100,
                "description": "Bad",
                "date": date(2026, 7, 16),
            },
        )


def test_edit_transaction_amount_updates_balance(session: Session, cuenta: Cuenta):
    mov = record_transaction(
        session,
        {
            "account_id": cuenta.id,
            "type": "expense",
            "amount_cents": 30000,
            "description": "Compra",
            "date": date(2026, 7, 16),
        },
    )
    assert compute_balance(cuenta, session) == -30000

    update_transaction(
        session,
        mov.id,
        {
            "amount_cents": 25000,
            "description": "Compra ajustada",
            "date": date(2026, 7, 16),
        },
    )
    assert compute_balance(cuenta, session) == -25000


def test_delete_transaction_removes_balance_effect(session: Session, cuenta: Cuenta):
    mov = record_transaction(
        session,
        {
            "account_id": cuenta.id,
            "type": "expense",
            "amount_cents": 30000,
            "description": "Compra",
            "date": date(2026, 7, 16),
        },
    )
    assert compute_balance(cuenta, session) == -30000

    delete_transaction(session, mov.id)
    assert compute_balance(cuenta, session) == 0


def test_filter_transactions_by_account_type_and_date(session: Session, cuenta: Cuenta, destino: Cuenta):
    record_transaction(
        session,
        {
            "account_id": cuenta.id,
            "type": "income",
            "amount_cents": 10000,
            "description": "Ingreso A",
            "date": date(2026, 7, 1),
        },
    )
    record_transaction(
        session,
        {
            "account_id": cuenta.id,
            "type": "expense",
            "amount_cents": 5000,
            "description": "Egreso A",
            "date": date(2026, 7, 15),
        },
    )
    record_transaction(
        session,
        {
            "account_id": destino.id,
            "type": "income",
            "amount_cents": 20000,
            "description": "Ingreso B",
            "date": date(2026, 7, 31),
        },
    )

    by_account = get_transactions(session, account_id=cuenta.id)
    assert len(by_account) == 2

    by_type = get_transactions(session, account_id=cuenta.id, type="income")
    assert len(by_type) == 1
    assert by_type[0].description == "Ingreso A"

    by_date = get_transactions(session, from_date=date(2026, 7, 10), to_date=date(2026, 7, 20))
    assert len(by_date) == 1
    assert by_date[0].description == "Egreso A"


def test_create_transaction_via_route(client: TestClient):
    client.post(
        "/accounts/",
        data={
            "name": "Banco",
            "type": "banco",
            "currency": "USD",
            "opening_balance_cents": "0",
        },
        follow_redirects=False,
    )

    response = client.post(
        "/transactions/",
        data={
            "account_id": "1",
            "type": "income",
            "amount_cents": "50000",
            "description": "Depósito",
            "date": "2026-07-16",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["Location"] == "/transactions"

    list_response = client.get("/transactions")
    assert "Depósito" in list_response.text
    assert "500.00" in list_response.text


def test_transfer_route_updates_balances(client: TestClient):
    client.post(
        "/accounts/",
        data={
            "name": "Origen",
            "type": "banco",
            "currency": "NIO",
            "opening_balance_cents": "100000",
        },
        follow_redirects=False,
    )
    client.post(
        "/accounts/",
        data={
            "name": "Destino",
            "type": "ahorro",
            "currency": "NIO",
            "opening_balance_cents": "0",
        },
        follow_redirects=False,
    )

    response = client.post(
        "/transactions/",
        data={
            "account_id": "1",
            "type": "transfer",
            "amount_cents": "30000",
            "description": "Ahorro",
            "date": "2026-07-16",
            "destination_account_id": "2",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    source_detail = client.get("/accounts/1")
    assert "700.00" in source_detail.text

    dest_detail = client.get("/accounts/2")
    assert "300.00" in dest_detail.text


def test_delete_transaction_via_route(client: TestClient):
    client.post(
        "/accounts/",
        data={
            "name": "Gastos",
            "type": "efectivo",
            "currency": "NIO",
            "opening_balance_cents": "0",
        },
        follow_redirects=False,
    )
    client.post(
        "/transactions/",
        data={
            "account_id": "1",
            "type": "expense",
            "amount_cents": "10000",
            "description": "Cena",
            "date": "2026-07-16",
        },
        follow_redirects=False,
    )

    response = client.delete(
        "/transactions/1",
        follow_redirects=False,
    )
    assert response.status_code == 303

    detail = client.get("/accounts/1")
    assert "-100.00" not in detail.text
    assert "0.00" in detail.text


def test_reject_negative_amount_via_route(client: TestClient):
    client.post(
        "/accounts/",
        data={
            "name": "Gastos",
            "type": "efectivo",
            "currency": "NIO",
            "opening_balance_cents": "0",
        },
        follow_redirects=False,
    )

    response = client.post(
        "/transactions/",
        data={
            "account_id": "1",
            "type": "income",
            "amount_cents": "-100",
            "description": "Bad",
            "date": "2026-07-16",
        },
    )
    assert response.status_code == 422


def test_list_page_renders_empty(client: TestClient):
    response = client.get("/transactions")
    assert response.status_code == 200
    assert "No hay movimientos" in response.text


def test_new_transaction_form_renders(client: TestClient):
    response = client.get("/transactions/new")
    assert response.status_code == 200
    assert "Nuevo movimiento" in response.text
