from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException, status
from beanie import PydanticObjectId

from app.models.credit_card import CreditCard
from app.models.user import User
from app.repositories.credit_card import credit_card_repo
from app.schemas.credit_card import (
    CreditCardCreate,
    CreditCardResponse,
    CreditCardUpdate,
)


class CreditCardService:
    def _to_response(self, card: CreditCard) -> CreditCardResponse:
        available_limit = max(0.0, card.credit_limit - card.outstanding_amount)
        return CreditCardResponse(
            id=str(card.id),
            user_id=str(card.user_id),
            card_name=card.card_name,
            provider=card.provider,
            last_four=card.last_four,
            credit_limit=card.credit_limit,
            outstanding_amount=card.outstanding_amount,
            available_limit=available_limit,
            billing_date=card.billing_date,
            payment_due_date=card.payment_due_date,
            created_at=card.created_at,
            updated_at=card.updated_at,
        )

    async def create_credit_card(
        self, user: User, data: CreditCardCreate
    ) -> CreditCardResponse:
        card = CreditCard(
            user_id=user.id,
            card_name=data.card_name,
            provider=data.provider,
            last_four=data.last_four,
            credit_limit=data.credit_limit,
            outstanding_amount=data.outstanding_amount,
            billing_date=data.billing_date,
            payment_due_date=data.payment_due_date,
        )
        saved = await credit_card_repo.create(card)
        return self._to_response(saved)

    async def list_credit_cards(self, user: User) -> List[CreditCardResponse]:
        cards = await credit_card_repo.list_by_user(user.id)
        return [self._to_response(c) for c in cards]

    async def get_credit_card(self, card_id: str, user: User) -> CreditCardResponse:
        try:
            oid = PydanticObjectId(card_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid credit card ID format.",
            )

        card = await credit_card_repo.get_by_id_and_user(oid, user.id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credit card not found.",
            )
        return self._to_response(card)

    async def update_credit_card(
        self, card_id: str, user: User, data: CreditCardUpdate
    ) -> CreditCardResponse:
        try:
            oid = PydanticObjectId(card_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid credit card ID format.",
            )

        card = await credit_card_repo.get_by_id_and_user(oid, user.id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credit card not found.",
            )

        if data.card_name is not None:
            card.card_name = data.card_name
        if data.provider is not None:
            card.provider = data.provider
        if data.last_four is not None:
            card.last_four = data.last_four
        if data.credit_limit is not None:
            card.credit_limit = data.credit_limit
        if data.outstanding_amount is not None:
            card.outstanding_amount = data.outstanding_amount
        if data.billing_date is not None:
            card.billing_date = data.billing_date
        if data.payment_due_date is not None:
            card.payment_due_date = data.payment_due_date

        card.updated_at = datetime.now(timezone.utc)
        saved = await credit_card_repo.save(card)
        return self._to_response(saved)

    async def delete_credit_card(self, card_id: str, user: User) -> None:
        try:
            oid = PydanticObjectId(card_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid credit card ID format.",
            )

        card = await credit_card_repo.get_by_id_and_user(oid, user.id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credit card not found.",
            )

        await credit_card_repo.delete(card)


credit_card_service = CreditCardService()
