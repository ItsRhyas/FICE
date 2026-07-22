"""Dashboard routes for FICE.

Provides the main dashboard page, HTMX partials for each section, and
JSON endpoints used by Chart.js.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session

from app.db import get_session
from app.models import Cuenta
from app.services import (
    get_account_balances,
    get_balance_distribution_chart,
    get_month_summary,
    get_monthly_summary_chart,
    get_net_worth,
    get_net_worth_trend,
    get_recent_transactions,
)
from app.templating import templates

router = APIRouter(tags=["dashboard"])

SessionDep = Annotated[Session, Depends(get_session)]


def _format_currency(currency: str) -> str:
    """Return the symbol for a known currency code."""
    return {"USD": "$", "NIO": "C$"}.get(currency, currency)


def _currency_accounts(accounts: list[Cuenta]) -> dict[int, Cuenta]:
    """Build an account lookup from a list of accounts."""
    return {account.id: account for account in accounts}


def _dashboard_context(session: Session) -> dict:
    """Build the shared context for the dashboard and its partials."""
    today = date.today()
    recent = get_recent_transactions(session, limit=10)
    account_balances = get_account_balances(session)
    accounts_by_id = {item["account"].id: item["account"] for item in account_balances}

    return {
        "net_worth": get_net_worth(session),
        "account_balances": account_balances,
        "month_summary": get_month_summary(session, today.year, today.month),
        "recent_transactions": recent,
        "accounts_by_id": accounts_by_id,
        "currency_symbol": _format_currency,
    }


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, session: SessionDep):
    """Render the full dashboard page."""
    context = _dashboard_context(session)
    context["request"] = request
    return templates.TemplateResponse(request, "dashboard.html", context)


@router.get("/partials/net-worth", response_class=HTMLResponse)
def partial_net_worth(request: Request, session: SessionDep):
    """HTMX partial for the net-worth section."""
    context = {
        "request": request,
        "net_worth": get_net_worth(session),
        "currency_symbol": _format_currency,
    }
    return templates.TemplateResponse(request, "partials/_net_worth.html", context)


@router.get("/partials/account-balances", response_class=HTMLResponse)
def partial_account_balances(request: Request, session: SessionDep):
    """HTMX partial for the account balances section."""
    context = {
        "request": request,
        "account_balances": get_account_balances(session),
        "currency_symbol": _format_currency,
    }
    return templates.TemplateResponse(request, "partials/_account_balances.html", context)


@router.get("/partials/month-summary", response_class=HTMLResponse)
def partial_month_summary(request: Request, session: SessionDep):
    """HTMX partial for the current-month summary section."""
    today = date.today()
    context = {
        "request": request,
        "month_summary": get_month_summary(session, today.year, today.month),
        "currency_symbol": _format_currency,
    }
    return templates.TemplateResponse(request, "partials/_month_summary.html", context)


@router.get("/partials/recent-transactions", response_class=HTMLResponse)
def partial_recent_transactions(request: Request, session: SessionDep):
    """HTMX partial for the recent transactions section."""
    recent = get_recent_transactions(session, limit=10)
    accounts_by_id = _currency_accounts(
        [item["account"] for item in get_account_balances(session)]
    )
    context = {
        "request": request,
        "recent_transactions": recent,
        "accounts_by_id": accounts_by_id,
        "currency_symbol": _format_currency,
    }
    return templates.TemplateResponse(request, "partials/_recent_transactions.html", context)


@router.get("/api/charts/monthly-summary")
def chart_monthly_summary(session: SessionDep):
    """JSON data for the monthly income vs expense bar chart."""
    return get_monthly_summary_chart(session)


@router.get("/api/charts/balance-distribution")
def chart_balance_distribution(session: SessionDep):
    """JSON data for the balance distribution doughnut chart."""
    return get_balance_distribution_chart(session)


@router.get("/api/charts/net-worth-trend")
def chart_net_worth_trend(session: SessionDep):
    """JSON data for the net-worth trend line chart."""
    return get_net_worth_trend(session)
