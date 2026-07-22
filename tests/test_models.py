"""Tests for FICE SQLModel validation rules."""

from datetime import date

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import Cuenta, Movimiento


@pytest.fixture(name="session", scope="function")
def session_fixture():
    """In-memory SQLite session for isolated model tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


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
    """Create a second account to use as transfer destination."""
    cuenta = Cuenta(name="Ahorros", type="ahorro", currency="NIO")
    session.add(cuenta)
    session.commit()
    session.refresh(cuenta)
    return cuenta


class TestCuentaValidation:
    def test_create_valid_account(self, session: Session):
        cuenta = Cuenta(
            name="BAC USD",
            type="banco",
            currency="USD",
            opening_balance_cents=100000,
        )
        session.add(cuenta)
        session.commit()
        session.refresh(cuenta)
        assert cuenta.id is not None
        assert cuenta.archived is False
        assert cuenta.opening_balance_cents == 100000

    def test_create_account_defaults(self, session: Session):
        cuenta = Cuenta(name="Efectivo", type="efectivo", currency="NIO")
        session.add(cuenta)
        session.commit()
        session.refresh(cuenta)
        assert cuenta.opening_balance_cents == 0
        assert cuenta.archived is False

    def test_reject_float_opening_balance(self):
        with pytest.raises(ValueError):
            Cuenta(
                name="BAC USD",
                type="banco",
                currency="USD",
                opening_balance_cents=100.50,
            )

    @pytest.mark.parametrize("bad_type", ["credit", "bank", "", "ahorros"])
    def test_reject_unknown_type(self, bad_type: str):
        with pytest.raises(ValueError):
            Cuenta(name="X", type=bad_type, currency="USD")

    @pytest.mark.parametrize("bad_currency", ["EUR", "CRC", ""])
    def test_reject_unknown_currency(self, bad_currency: str):
        with pytest.raises(ValueError):
            Cuenta(name="X", type="banco", currency=bad_currency)


class TestMovimientoValidation:
    def test_create_income(self, session: Session, cuenta: Cuenta):
        mov = Movimiento(
            account_id=cuenta.id,
            type="income",
            amount_cents=200000,
            description="Salario",
            date=date(2026, 7, 16),
        )
        session.add(mov)
        session.commit()
        session.refresh(mov)
        assert mov.id is not None
        assert mov.destination_account_id is None

    def test_create_expense(self, session: Session, cuenta: Cuenta):
        mov = Movimiento(
            account_id=cuenta.id,
            type="expense",
            amount_cents=30000,
            description="Compra",
            date=date(2026, 7, 16),
        )
        session.add(mov)
        session.commit()
        session.refresh(mov)
        assert mov.id is not None

    def test_create_transfer(self, session: Session, cuenta: Cuenta, destino: Cuenta):
        mov = Movimiento(
            account_id=cuenta.id,
            type="transfer",
            amount_cents=20000,
            description="Transferencia",
            date=date(2026, 7, 16),
            destination_account_id=destino.id,
        )
        session.add(mov)
        session.commit()
        session.refresh(mov)
        assert mov.destination_account_id == destino.id

    def test_reject_negative_income(self):
        with pytest.raises(ValueError):
            Movimiento(
                account_id=1,
                type="income",
                amount_cents=-100,
                description="Bad",
                date=date(2026, 7, 16),
            )

    def test_reject_negative_expense(self):
        with pytest.raises(ValueError):
            Movimiento(
                account_id=1,
                type="expense",
                amount_cents=-100,
                description="Bad",
                date=date(2026, 7, 16),
            )

    def test_reject_zero_amount(self):
        with pytest.raises(ValueError):
            Movimiento(
                account_id=1,
                type="income",
                amount_cents=0,
                description="Zero",
                date=date(2026, 7, 16),
            )

    def test_reject_float_amount(self):
        with pytest.raises(ValueError):
            Movimiento(
                account_id=1,
                type="income",
                amount_cents=100.50,
                description="Float",
                date=date(2026, 7, 16),
            )

    @pytest.mark.parametrize("bad_type", ["ingreso", "egreso", "transferencia", ""])
    def test_reject_invalid_transaction_type(self, bad_type: str):
        with pytest.raises(ValueError):
            Movimiento(
                account_id=1,
                type=bad_type,
                amount_cents=1000,
                description="Bad",
                date=date(2026, 7, 16),
            )

    def test_transfer_requires_destination(self):
        with pytest.raises(ValueError):
            Movimiento(
                account_id=1,
                type="transfer",
                amount_cents=1000,
                description="Missing destination",
                date=date(2026, 7, 16),
            )

    def test_non_transfer_rejects_destination(self, cuenta: Cuenta):
        with pytest.raises(ValueError):
            Movimiento(
                account_id=cuenta.id,
                type="income",
                amount_cents=1000,
                description="Unexpected destination",
                date=date(2026, 7, 16),
                destination_account_id=999,
            )

    def test_transfer_to_same_account_rejected(self, cuenta: Cuenta):
        with pytest.raises(ValueError):
            Movimiento(
                account_id=cuenta.id,
                type="transfer",
                amount_cents=1000,
                description="Self transfer",
                date=date(2026, 7, 16),
                destination_account_id=cuenta.id,
            )
