from datetime import datetime
from typing import Any, Dict, List, Optional

from app.mcp.context import resolve_user
from app.mcp.registry import register_tool
from app.models.emi import EMIStatus
from app.schemas.emi import EMICreate, EMIUpdate
from app.services.emi import emi_service


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
    name="list_emis",
    description="List Equated Monthly Installments (EMIs) / loans, optionally filtered by status ('active', 'completed', 'overdue').",
    category="emis",
)
async def list_emis(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List EMIs for the user."""
    user = await resolve_user(user_id)
    emi_status = EMIStatus(status.lower()) if status else None
    emis = await emi_service.list_emis(user, status=emi_status)
    return [e.model_dump(mode="json") for e in emis]


@register_tool(
    name="get_emi",
    description="Retrieve details of an EMI by its ID, including installments paid, remaining installments, and next payment date.",
    category="emis",
)
async def get_emi(emi_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get single EMI details."""
    user = await resolve_user(user_id)
    emi = await emi_service.get_emi(emi_id, user)
    return emi.model_dump(mode="json")


@register_tool(
    name="create_emi",
    description="Create a new EMI schedule for a loan, device financing, or credit purchase.",
    category="emis",
)
async def create_emi(
    name: str,
    total_amount: float,
    monthly_emi_amount: float,
    total_installments: int,
    paid_installments: int = 0,
    start_date: Optional[str] = None,
    due_day: int = 1,
    account_id: Optional[str] = None,
    credit_card_id: Optional[str] = None,
    category_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new EMI schedule."""
    user = await resolve_user(user_id)
    parsed_date = _parse_datetime(start_date) or datetime.utcnow()

    emi_data = EMICreate(
        name=name,
        total_amount=total_amount,
        monthly_emi_amount=monthly_emi_amount,
        total_installments=total_installments,
        paid_installments=paid_installments,
        start_date=parsed_date,
        due_day=due_day,
        account_id=account_id,
        credit_card_id=credit_card_id,
        category_id=category_id,
    )
    saved = await emi_service.create_emi(user, emi_data)
    return saved.model_dump(mode="json")


@register_tool(
    name="update_emi",
    description="Update an existing EMI's terms, installment amounts, status, or linked account/card.",
    category="emis",
)
async def update_emi(
    emi_id: str,
    name: Optional[str] = None,
    total_amount: Optional[float] = None,
    monthly_emi_amount: Optional[float] = None,
    total_installments: Optional[int] = None,
    paid_installments: Optional[int] = None,
    start_date: Optional[str] = None,
    due_day: Optional[int] = None,
    account_id: Optional[str] = None,
    credit_card_id: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an EMI."""
    user = await resolve_user(user_id)
    parsed_date = _parse_datetime(start_date)

    emi_update = EMIUpdate(
        name=name,
        total_amount=total_amount,
        monthly_emi_amount=monthly_emi_amount,
        total_installments=total_installments,
        paid_installments=paid_installments,
        start_date=parsed_date,
        due_day=due_day,
        account_id=account_id,
        credit_card_id=credit_card_id,
        status=EMIStatus(status.lower()) if status else None,
    )
    updated = await emi_service.update_emi(emi_id, user, emi_update)
    return updated.model_dump(mode="json")


@register_tool(
    name="delete_emi",
    description="Delete an EMI schedule by ID.",
    category="emis",
)
async def delete_emi(emi_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Delete an EMI."""
    user = await resolve_user(user_id)
    await emi_service.delete_emi(emi_id, user)
    return {"message": f"EMI '{emi_id}' deleted successfully."}


@register_tool(
    name="mark_emi_paid",
    description="Mark the next installment of an EMI as paid. Automatically increments paid installments and applies deduction to linked account or card.",
    category="emis",
)
async def mark_emi_paid(emi_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Record installment payment for an EMI."""
    user = await resolve_user(user_id)
    result = await emi_service.mark_paid(emi_id, user)
    return result.model_dump(mode="json")
