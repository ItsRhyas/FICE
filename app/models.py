"""SQLModel domain models for FICE.

Table names are in Spanish to match the domain language. Column names are
a mix: core domain fields keep Spanish names (`cuenta`, `movimiento`) while
type/currency labels and transaction types use the identifiers agreed in the
specification.
"""

from datetime import date as date_type
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Column, Date, ForeignKey, Integer, Text
from sqlalchemy.orm import validates
from sqlmodel import Field, SQLModel

ACCOUNT_TYPES = ("banco", "efectivo", "ahorro")
CURRENCIES = ("USD", "NIO")
TRANSACTION_TYPES = ("income", "expense", "transfer")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_float(value: float | int | None, field_name: str) -> int | None:
    """Reject float values for integer-cents fields."""
    if value is None:
        return None
    if isinstance(value, float):
        raise ValueError(f"{field_name} must be an integer number of cents, not a float")
    return int(value)


def _validate_enum(value: str | None, allowed: tuple[str, ...], field_name: str) -> str | None:
    """Reject values outside an allowed enum set."""
    if value is None:
        return None
    if value not in allowed:
        raise ValueError(f"{field_name} must be one of {allowed}, got '{value}'")
    return value


class Cuenta(SQLModel, table=True):
    """A financial account."""

    __tablename__ = "cuenta"
    __table_args__ = (
        CheckConstraint(f"type IN {ACCOUNT_TYPES}", name="check_cuenta_type"),
        CheckConstraint(f"currency IN {CURRENCIES}", name="check_cuenta_currency"),
    )

    id: int | None = Field(default=None, sa_column=Column(Integer, primary_key=True))
    name: str = Field(sa_column=Column(Text, nullable=False))
    type: str = Field(sa_column=Column(Text, nullable=False))
    currency: str = Field(sa_column=Column(Text, nullable=False))
    opening_balance_cents: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, default=0),
    )
    archived: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, default=False),
    )
    created_at: str = Field(default_factory=_iso_now, sa_column=Column(Text, nullable=False))
    updated_at: str = Field(default_factory=_iso_now, sa_column=Column(Text, nullable=False))

    @validates("type")
    def validate_type(self, key: str, value: str) -> str:
        return _validate_enum(value, ACCOUNT_TYPES, "type")

    @validates("currency")
    def validate_currency(self, key: str, value: str) -> str:
        return _validate_enum(value, CURRENCIES, "currency")

    @validates("opening_balance_cents")
    def validate_opening_balance_cents(self, key: str, value: int | float) -> int:
        return _reject_float(value, "opening_balance_cents")


class Movimiento(SQLModel, table=True):
    """A single financial transaction."""

    __tablename__ = "movimiento"
    __table_args__ = (
        CheckConstraint(f"type IN {TRANSACTION_TYPES}", name="check_movimiento_type"),
        CheckConstraint("amount_cents > 0", name="check_movimiento_amount_positive"),
    )

    id: int | None = Field(default=None, sa_column=Column(Integer, primary_key=True))
    account_id: int = Field(
        sa_column=Column(Integer, ForeignKey("cuenta.id"), nullable=False, index=True),
    )
    type: str = Field(sa_column=Column(Text, nullable=False))
    amount_cents: int = Field(sa_column=Column(Integer, nullable=False))
    description: str = Field(
        default="",
        sa_column=Column(Text, nullable=False, default=""),
    )
    date: date_type = Field(sa_column=Column(Date, nullable=False, index=True))
    destination_account_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("cuenta.id"),
            nullable=True,
            index=True,
        ),
    )
    created_at: str = Field(default_factory=_iso_now, sa_column=Column(Text, nullable=False))
    updated_at: str = Field(default_factory=_iso_now, sa_column=Column(Text, nullable=False))

    @validates("type")
    def validate_type(self, key: str, value: str) -> str:
        return _validate_enum(value, TRANSACTION_TYPES, "type")

    @validates("amount_cents")
    def validate_amount_cents(self, key: str, value: int | float) -> int:
        value = _reject_float(value, "amount_cents")
        if value <= 0:
            raise ValueError("amount_cents must be greater than 0")
        return value

    def __init__(self, **data):
        # SQLAlchemy sets attributes one by one during construction, so
        # cross-field transfer rules must be deferred until all values are set.
        object.__setattr__(self, "_initializing", True)
        try:
            super().__init__(**data)
        finally:
            object.__setattr__(self, "_initializing", False)
        self._enforce_transfer_rules()

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name in ("account_id", "destination_account_id", "type"):
            if not getattr(self, "_initializing", False):
                self._enforce_transfer_rules()

    def _enforce_transfer_rules(self):
        txn_type = getattr(self, "type", None)
        destination = getattr(self, "destination_account_id", None)
        account_id = getattr(self, "account_id", None)

        if txn_type == "transfer":
            if destination is None:
                raise ValueError("destination_account_id is required for transfers")
            if account_id is not None and destination == account_id:
                raise ValueError("destination_account_id cannot be the same as account_id")
        elif destination is not None:
            raise ValueError("destination_account_id is only allowed for transfers")
