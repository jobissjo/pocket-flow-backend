from typing import List
from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.credit_card import (
    CreditCardCreate,
    CreditCardResponse,
    CreditCardUpdate,
)
from app.services.credit_card import credit_card_service

router = APIRouter(prefix="/credit-cards", tags=["Credit Cards"])


@router.post(
    "",
    response_model=CreditCardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new credit card",
    description="Registers a credit card with limit, billing cycle, and outstanding balance.",
)
async def create_credit_card(
    data: CreditCardCreate,
    current_user: User = Depends(get_current_user),
) -> CreditCardResponse:
    return await credit_card_service.create_credit_card(current_user, data)


@router.get(
    "",
    response_model=List[CreditCardResponse],
    summary="List all credit cards",
    description="Retrieves all credit cards associated with the current user.",
)
async def list_credit_cards(
    current_user: User = Depends(get_current_user),
) -> List[CreditCardResponse]:
    return await credit_card_service.list_credit_cards(current_user)


@router.get(
    "/{card_id}",
    response_model=CreditCardResponse,
    summary="Get credit card details",
    description="Retrieves information for a specific credit card.",
)
async def get_credit_card(
    card_id: str,
    current_user: User = Depends(get_current_user),
) -> CreditCardResponse:
    return await credit_card_service.get_credit_card(card_id, current_user)


@router.patch(
    "/{card_id}",
    response_model=CreditCardResponse,
    summary="Update credit card",
    description="Updates credit card details such as limit, dates, or outstanding amount.",
)
async def update_credit_card(
    card_id: str,
    data: CreditCardUpdate,
    current_user: User = Depends(get_current_user),
) -> CreditCardResponse:
    return await credit_card_service.update_credit_card(card_id, current_user, data)


@router.delete(
    "/{card_id}",
    response_model=MessageResponse,
    summary="Delete credit card",
    description="Removes a credit card from the user's account.",
)
async def delete_credit_card(
    card_id: str,
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await credit_card_service.delete_credit_card(card_id, current_user)
    return MessageResponse(message="Credit card deleted successfully.")
