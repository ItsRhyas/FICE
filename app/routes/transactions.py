"""Transaction recording routes for FICE."""

from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.db import get_session
from app.models import Cuenta, CURRENCIES, Movimiento, TRANSACTION_TYPES
from app.services import (
    compute_balance,
    delete_transaction,
    get_transactions,
    record_transaction,
    update_transaction,
)
from app.templating import templates

router = APIRouter(prefix="/transactions", tags=["transactions"])

SessionDep = Annotated[Session, Depends(get_session)]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redirect(request: Request, url: str) -> RedirectResponse:
    """Return a redirect that also works for HTMX requests."""
    response = RedirectResponse(url=url, status_code=303)
    if request.headers.get("HX-Request") == "true":
        response.headers["HX-Redirect"] = url
    return response


def _format_currency(currency: str) -> str:
    """Return the symbol for a known currency code."""
    return {"USD": "$", "NIO": "C$"}.get(currency, currency)


@router.get("/", response_class=HTMLResponse)
def list_transactions(
    request: Request,
    session: SessionDep,
    account_id: str = "",
    type: str = "",
    from_date: str = "",
    to_date: str = "",
):
    """List transactions with optional filters."""
    movimientos = get_transactions(
        session,
        account_id=account_id or None,
        type=type or None,
        from_date=from_date or None,
        to_date=to_date or None,
    )

    # Build an account lookup for display (include archived so historical rows
    # still show their account name).
    accounts = {c.id: c for c in session.exec(select(Cuenta)).all()}

    return templates.TemplateResponse(
        request,
        "transactions/list.html",
        {
            "transactions": movimientos,
            "accounts": accounts,
            "account_id": account_id,
            "type": type,
            "from_date": from_date,
            "to_date": to_date,
            "currency_symbol": _format_currency,
            "TRANSACTION_TYPES": TRANSACTION_TYPES,
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_transaction(request: Request, session: SessionDep, type: str = ""):
    """Render the create-transaction form."""
    accounts = session.exec(select(Cuenta).where(Cuenta.archived == False)).all()  # noqa: E712
    today = date.today().isoformat()
    return templates.TemplateResponse(
        request,
        "transactions/form.html",
        {
            "movimiento": None,
            "accounts": accounts,
            "type": type or "income",
            "date": today,
            "currency_symbol": _format_currency,
            "error": None,
        },
    )


@router.post("/", response_class=HTMLResponse)
def create_transaction(
    request: Request,
    session: SessionDep,
    account_id: str = Form(...),
    type: str = Form(...),
    amount_cents: str = Form(...),
    description: str = Form(""),
    date: str = Form(...),
    destination_account_id: str = Form(""),
):
    """Create a new transaction."""
    try:
        record_transaction(
            session,
            {
                "account_id": account_id,
                "type": type,
                "amount_cents": amount_cents,
                "description": description,
                "date": date,
                "destination_account_id": destination_account_id,
            },
        )
    except ValueError as exc:
        accounts = session.exec(select(Cuenta).where(Cuenta.archived == False)).all()  # noqa: E712
        return templates.TemplateResponse(
            request,
            "transactions/form.html",
            {
                "movimiento": None,
                "accounts": accounts,
                "type": type,
                "account_id": account_id,
                "destination_account_id": destination_account_id,
                "amount_cents": amount_cents,
                "description": description,
                "date": date,
                "currency_symbol": _format_currency,
                "error": str(exc),
            },
            status_code=422,
        )

    return _redirect(request, "/transactions")


@router.get("/{transaction_id}/edit", response_class=HTMLResponse)
def edit_transaction(request: Request, transaction_id: int, session: SessionDep):
    """Render the edit form for a transaction."""
    movimiento = session.get(Movimiento, transaction_id)
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")

    accounts = session.exec(select(Cuenta).where(Cuenta.archived == False)).all()  # noqa: E712
    return templates.TemplateResponse(
        request,
        "transactions/form.html",
        {
            "movimiento": movimiento,
            "accounts": accounts,
            "type": movimiento.type,
            "date": movimiento.date.isoformat(),
            "currency_symbol": _format_currency,
            "error": None,
        },
    )


@router.put("/{transaction_id}", response_class=HTMLResponse)
@router.post("/{transaction_id}", response_class=HTMLResponse)
def update_existing_transaction(
    request: Request,
    transaction_id: int,
    session: SessionDep,
    amount_cents: str = Form(...),
    description: str = Form(""),
    date: str = Form(...),
):
    """Update a transaction's editable fields."""
    movimiento = session.get(Movimiento, transaction_id)
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")

    try:
        update_transaction(
            session,
            transaction_id,
            {
                "amount_cents": amount_cents,
                "description": description,
                "date": date,
            },
        )
    except ValueError as exc:
        accounts = session.exec(select(Cuenta).where(Cuenta.archived == False)).all()  # noqa: E712
        return templates.TemplateResponse(
            request,
            "transactions/form.html",
            {
                "movimiento": movimiento,
                "accounts": accounts,
                "type": movimiento.type,
                "amount_cents": amount_cents,
                "description": description,
                "date": date,
                "currency_symbol": _format_currency,
                "error": str(exc),
            },
            status_code=422,
        )

    return _redirect(request, "/transactions")


@router.delete("/{transaction_id}", response_class=HTMLResponse)
@router.post("/{transaction_id}/delete", response_class=HTMLResponse)
def remove_transaction(request: Request, transaction_id: int, session: SessionDep):
    """Hard delete a transaction."""
    try:
        delete_transaction(session, transaction_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    return _redirect(request, "/transactions")
