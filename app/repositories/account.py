from typing import List, Optional
from beanie import PydanticObjectId
from app.models.account import Account
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    def __init__(self):
        super().__init__(Account)

    async def get_by_id_and_user(
        self, account_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> Optional[Account]:
        return await Account.find_one(
            Account.id == account_id,
            Account.user_id == user_id,
        )

    async def list_by_user(
        self, user_id: PydanticObjectId, skip: int = 0, limit: int = 100
    ) -> List[Account]:
        return (
            await Account.find(Account.user_id == user_id)
            .sort(-Account.created_at)
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def update_balance(
        self, account_id: PydanticObjectId, user_id: PydanticObjectId, delta: float
    ) -> Optional[Account]:
        account = await self.get_by_id_and_user(account_id, user_id)
        if account:
            account.balance += delta
            await account.save()
        return account

    async def get_total_balance(self, user_id: PydanticObjectId) -> float:
        accounts = await Account.find(Account.user_id == user_id).to_list()
        return sum(acc.balance for acc in accounts)


account_repo = AccountRepository()
