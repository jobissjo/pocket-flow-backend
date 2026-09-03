from datetime import datetime
from typing import Any, Dict, List, Optional

from app.mcp.context import resolve_user
from app.mcp.registry import register_tool
from app.services.dashboard import dashboard_service


def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
    return None


@register_tool(
    name="get_dashboard_summary",
    description="Get overall financial summary: total balance across accounts, total income, total expenses, credit card outstanding balance, net savings, and savings percentage.",
    category="dashboard",
)
async def get_dashboard_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve financial summary KPIs."""
    user = await resolve_user(user_id)
    summary = await dashboard_service.get_summary(
        user,
        start_date=_parse_datetime(start_date),
        end_date=_parse_datetime(end_date),
    )
    return summary.model_dump(mode="json")


@register_tool(
    name="get_financial_analytics",
    description="Get detailed financial analytics: daily/monthly income vs expense trends and category breakdowns for both income and expenses.",
    category="dashboard",
)
async def get_financial_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve time series and category spending breakdowns."""
    user = await resolve_user(user_id)
    analytics = await dashboard_service.get_analytics(
        user,
        start_date=_parse_datetime(start_date),
        end_date=_parse_datetime(end_date),
    )
    return analytics.model_dump(mode="json")


@register_tool(
    name="get_recent_transactions",
    description="Retrieve the most recent transactions with populated category, account, and card details.",
    category="dashboard",
)
async def get_recent_transactions(
    limit: int = 10,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve recent transactions."""
    user = await resolve_user(user_id)
    txs = await dashboard_service.get_recent_transactions(user, limit=limit)
    return [t.model_dump(mode="json") for t in txs]


@register_tool(
    name="get_upcoming_emis",
    description="Retrieve active EMIs sorted by upcoming payment due date.",
    category="dashboard",
)
async def get_upcoming_emis(
    limit: int = 10,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve upcoming EMI payments."""
    user = await resolve_user(user_id)
    emis = await dashboard_service.get_upcoming_emi(user, limit=limit)
    return [e.model_dump(mode="json") for e in emis]
