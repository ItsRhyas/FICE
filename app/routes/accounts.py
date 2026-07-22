"""Account management routes for FICE."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.db import get_session
from app.models import Cuenta, CURRENCIES, ACCOUNT_TYPES
from app.services import compute_balance
from app.templating import templates

router = APIRouter(prefix="/accounts", tags=["accounts"])

SessionDep = Annotated[Session, Depends(get_session)]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redirect(request: Request, url: str) -> RedirectResponse:
    """Return a redirect that also works for HTMX requests."""
    response = RedirectResponse(url=url, status_code=303)
    if request.headers.get("HX-Request") == "true":
        response.headers["HX-Redirect"] = url
    return response


@router.get("/", response_class=HTMLResponse)
def list_accounts(request: Request, session: SessionDep, include_archived: bool = False):
    """List accounts, excluding archived ones by default."""
    query = select(Cuenta)
    if not include_archived:
        query = query.where(Cuenta.archived == False)  # noqa: E712
    cuentas = session.exec(query).all()

    # Attach computed balances for template rendering without mutating the
    # SQLModel instance (Pydantic rejects unknown fields).
    accounts_with_balance = [
        {"cuenta": cuenta, "balance": compute_balance(cuenta, session)}
        for cuenta in cuentas
    ]

    return templates.TemplateResponse(
        request,
        "accounts/list.html",
        {"accounts": accounts_with_balance, "include_archived": include_archived},
    )


@router.get("/new", response_class=HTMLResponse)
def new_account(request: Request):
    """Render the create-account form."""
    return templates.TemplateResponse(
        request,
        "accounts/form.html",
        {"cuenta": None},
    )


@router.post("/", response_class=HTMLResponse)
def create_account(
    request: Request,
    session: SessionDep,
    name: str = Form(...),
    type: str = Form(...),
    currency: str = Form(...),
    opening_balance_cents: str = Form("0"),
):
    """Create a new account."""
    try:
        obc = int(opening_balance_cents)
    except ValueError:
        return templates.TemplateResponse(
            request,
            "accounts/form.html",
            {
                "cuenta": None,
                "error": "El saldo inicial debe ser un número entero (centavos).",
                "name": name,
                "type": type,
                "currency": currency,
                "opening_balance_cents": opening_balance_cents,
            },
            status_code=422,
        )

    try:
        cuenta = Cuenta(
            name=name,
            type=type,
            currency=currency,
            opening_balance_cents=obc,
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "accounts/form.html",
            {
                "cuenta": None,
                "error": str(exc),
                "name": name,
                "type": type,
                "currency": currency,
                "opening_balance_cents": opening_balance_cents,
            },
            status_code=422,
        )

    session.add(cuenta)
    session.commit()
    session.refresh(cuenta)
    return _redirect(request, "/accounts")


@router.get("/{account_id}", response_class=HTMLResponse)
def account_detail(request: Request, account_id: int, session: SessionDep):
    """Show account details including computed balance."""
    cuenta = session.get(Cuenta, account_id)
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    balance = compute_balance(cuenta, session)
    return templates.TemplateResponse(
        request,
        "accounts/detail.html",
        {"cuenta": cuenta, "balance": balance},
    )


@router.get("/{account_id}/edit", response_class=HTMLResponse)
def edit_account(request: Request, account_id: int, session: SessionDep):
    """Render the edit form for an account."""
    cuenta = session.get(Cuenta, account_id)
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return templates.TemplateResponse(
        request,
        "accounts/form.html",
        {"cuenta": cuenta},
    )


@router.put("/{account_id}", response_class=HTMLResponse)
@router.post("/{account_id}", response_class=HTMLResponse)
def update_account(
    request: Request,
    account_id: int,
    session: SessionDep,
    name: str = Form(...),
    type: str | None = Form(None),
    currency: str | None = Form(None),
):
    """Update account name. Type and currency are immutable."""
    cuenta = session.get(Cuenta, account_id)
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    if type is not None and type != cuenta.type:
        return templates.TemplateResponse(
            request,
            "accounts/form.html",
            {
                "cuenta": cuenta,
                "error": "El tipo de cuenta no se puede cambiar.",
            },
            status_code=422,
        )

    if currency is not None and currency != cuenta.currency:
        return templates.TemplateResponse(
            request,
            "accounts/form.html",
            {
                "cuenta": cuenta,
                "error": "La moneda no se puede cambiar.",
            },
            status_code=422,
        )

    cuenta.name = name
    cuenta.updated_at = _iso_now()
    session.add(cuenta)
    session.commit()
    session.refresh(cuenta)
    return _redirect(request, "/accounts")


@router.put("/{account_id}/archive", response_class=HTMLResponse)
@router.post("/{account_id}/archive", response_class=HTMLResponse)
def toggle_archive(request: Request, account_id: int, session: SessionDep):
    """Toggle the archived flag on an account."""
    cuenta = session.get(Cuenta, account_id)
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    cuenta.archived = not cuenta.archived
    cuenta.updated_at = _iso_now()
    session.add(cuenta)
    session.commit()
    session.refresh(cuenta)
    return _redirect(request, "/accounts")
