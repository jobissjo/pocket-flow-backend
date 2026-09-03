from datetime import datetime
from typing import Any, Dict, List, Optional
from beanie import PydanticObjectId

from app.mcp.context import resolve_user
from app.mcp.registry import register_tool
from app.models.transaction import TransactionType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionFilterParams,
    TransactionUpdate,
)
from app.services.transaction import transaction_service


def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        # Support both '2026-03-01' and '2026-03-01T12:00:00'
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
    return None


@register_tool(
    name="list_transactions",
    description="List transactions with filtering by search query, income/expense type, category, account, credit card, or date range.",
    category="transactions",
)
async def list_transactions(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    type: Optional[str] = None,
    category_id: Optional[str] = None,
    account_id: Optional[str] = None,
    credit_card_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """List and filter transactions."""
    user = await resolve_user(user_id)
    tx_type = TransactionType(type.lower()) if type else None
    parsed_start = _parse_datetime(start_date)
    parsed_end = _parse_datetime(end_date)

    cat_oid = PydanticObjectId(category_id) if category_id else None
    acc_oid = PydanticObjectId(account_id) if account_id else None
    card_oid = PydanticObjectId(credit_card_id) if credit_card_id else None

    params = TransactionFilterParams(
        page=page,
        limit=limit,
        search=search,
        type=tx_type,
        category=cat_oid,
        account=acc_oid,
        credit_card=card_oid,
        start_date=parsed_start,
        end_date=parsed_end,
    )
    paginated = await transaction_service.list_transactions(user, params)
    return paginated.model_dump(mode="json")


@register_tool(
    name="get_transaction",
    description="Retrieve full details of a specific transaction by its ID.",
    category="transactions",
)
async def get_transaction(transaction_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get single transaction by ID."""
    user = await resolve_user(user_id)
    tx = await transaction_service.get_transaction(transaction_id, user)
    return tx.model_dump(mode="json")


@register_tool(
    name="create_transaction",
    description="Create a new income or expense transaction. Automatically adjusts linked bank account balance or credit card outstanding amount.",
    category="transactions",
)
async def create_transaction(
    title: str,
    amount: float,
    type: str,
    category_id: str,
    account_id: Optional[str] = None,
    credit_card_id: Optional[str] = None,
    date: Optional[str] = None,
    notes: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a new transaction."""
    user = await resolve_user(user_id)
    parsed_date = _parse_datetime(date) or datetime.utcnow()

    tx_data = TransactionCreate(
        title=title,
        amount=amount,
        type=TransactionType(type.lower()),
        category_id=category_id,
        account_id=account_id,
        credit_card_id=credit_card_id,
        date=parsed_date,
        notes=notes,
    )
    created = await transaction_service.create_transaction(user, tx_data)
    return created.model_dump(mode="json")


@register_tool(
    name="update_transaction",
    description="Update an existing transaction's details (title, amount, category, account, card, date, notes) and recalculates balances.",
    category="transactions",
)
async def update_transaction(
    transaction_id: str,
    title: Optional[str] = None,
    amount: Optional[float] = None,
    type: Optional[str] = None,
    category_id: Optional[str] = None,
    account_id: Optional[str] = None,
    credit_card_id: Optional[str] = None,
    date: Optional[str] = None,
    notes: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Update transaction fields."""
    user = await resolve_user(user_id)
    parsed_date = _parse_datetime(date)

    tx_update = TransactionUpdate(
        title=title,
        amount=amount,
        type=TransactionType(type.lower()) if type else None,
        category_id=category_id,
        account_id=account_id,
        credit_card_id=credit_card_id,
        date=parsed_date,
        notes=notes,
    )
    updated = await transaction_service.update_transaction(transaction_id, user, tx_update)
    return updated.model_dump(mode="json")


@register_tool(
    name="delete_transaction",
    description="Delete a transaction by ID and re-adjusts account balance or credit card outstanding balance accordingly.",
    category="transactions",
)
async def delete_transaction(transaction_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Delete a transaction and revert its balance impact."""
    user = await resolve_user(user_id)
    await transaction_service.delete_transaction(transaction_id, user)
    return {"message": f"Transaction '{transaction_id}' deleted successfully."}
