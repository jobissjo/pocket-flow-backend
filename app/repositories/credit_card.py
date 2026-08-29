from typing import List, Optional
from beanie import PydanticObjectId
from app.models.credit_card import CreditCard
from app.repositories.base import BaseRepository


class CreditCardRepository(BaseRepository[CreditCard]):
    def __init__(self):
        super().__init__(CreditCard)

    async def get_by_id_and_user(
        self, card_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> Optional[CreditCard]:
        return await CreditCard.find_one(
            CreditCard.id == card_id,
            CreditCard.user_id == user_id,
        )

    async def list_by_user(
        self, user_id: PydanticObjectId, skip: int = 0, limit: int = 100
    ) -> List[CreditCard]:
        return (
            await CreditCard.find(CreditCard.user_id == user_id)
            .sort(-CreditCard.created_at)
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def update_outstanding(
        self, card_id: PydanticObjectId, user_id: PydanticObjectId, delta: float
    ) -> Optional[CreditCard]:
        card = await self.get_by_id_and_user(card_id, user_id)
        if card:
            card.outstanding_amount += delta
            if card.outstanding_amount < 0:
                card.outstanding_amount = 0.0
            await card.save()
        return card

    async def get_total_outstanding(self, user_id: PydanticObjectId) -> float:
        cards = await CreditCard.find(CreditCard.user_id == user_id).to_list()
        return sum(card.outstanding_amount for card in cards)


credit_card_repo = CreditCardRepository()
