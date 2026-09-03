from typing import Any, Dict, List, Optional

from app.mcp.context import resolve_user
from app.mcp.registry import register_tool
from app.schemas.credit_card import CreditCardCreate, CreditCardUpdate
from app.services.credit_card import credit_card_service


@register_tool(
    name="list_credit_cards",
    description="List all credit cards with credit limits, current outstanding balances, and remaining available limits.",
    category="credit_cards",
)
async def list_credit_cards(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List credit cards for the user."""
    user = await resolve_user(user_id)
    cards = await credit_card_service.list_credit_cards(user)
    return [c.model_dump(mode="json") for c in cards]


@register_tool(
    name="get_credit_card",
    description="Retrieve details of a specific credit card by its ID.",
    category="credit_cards",
)
async def get_credit_card(card_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get single credit card details."""
    user = await resolve_user(user_id)
    card = await credit_card_service.get_credit_card(card_id, user)
    return card.model_dump(mode="json")


@register_tool(
    name="create_credit_card",
    description="Add a new credit card with credit limit, current outstanding balance, billing cycle day, and payment due day.",
    category="credit_cards",
)
async def create_credit_card(
    card_name: str,
    provider: str,
    last_four: str,
    credit_limit: float = 0.0,
    outstanding_amount: float = 0.0,
    billing_date: int = 1,
    payment_due_date: int = 20,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new credit card."""
    user = await resolve_user(user_id)
    card_data = CreditCardCreate(
        card_name=card_name,
        provider=provider,
        last_four=last_four,
        credit_limit=credit_limit,
        outstanding_amount=outstanding_amount,
        billing_date=billing_date,
        payment_due_date=payment_due_date,
    )
    saved = await credit_card_service.create_credit_card(user, card_data)
    return saved.model_dump(mode="json")


@register_tool(
    name="update_credit_card",
    description="Update credit card details such as limit, outstanding amount, provider, or billing cycle dates.",
    category="credit_cards",
)
async def update_credit_card(
    card_id: str,
    card_name: Optional[str] = None,
    provider: Optional[str] = None,
    last_four: Optional[str] = None,
    credit_limit: Optional[float] = None,
    outstanding_amount: Optional[float] = None,
    billing_date: Optional[int] = None,
    payment_due_date: Optional[int] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Update credit card fields."""
    user = await resolve_user(user_id)
    card_update = CreditCardUpdate(
        card_name=card_name,
        provider=provider,
        last_four=last_four,
        credit_limit=credit_limit,
        outstanding_amount=outstanding_amount,
        billing_date=billing_date,
        payment_due_date=payment_due_date,
    )
    updated = await credit_card_service.update_credit_card(card_id, user, card_update)
    return updated.model_dump(mode="json")


@register_tool(
    name="delete_credit_card",
    description="Delete a credit card by its ID.",
    category="credit_cards",
)
async def delete_credit_card(card_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Delete a credit card."""
    user = await resolve_user(user_id)
    await credit_card_service.delete_credit_card(card_id, user)
    return {"message": f"Credit card '{card_id}' deleted successfully."}
