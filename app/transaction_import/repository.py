from typing import List, Optional
from beanie import PydanticObjectId

from app.models.transaction_import import TransactionImport
from app.repositories.base import BaseRepository


class TransactionImportRepository(BaseRepository[TransactionImport]):
    def __init__(self):
        super().__init__(TransactionImport)

    async def get_by_id_and_user(
        self, import_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> Optional[TransactionImport]:
        return await TransactionImport.find_one(
            TransactionImport.id == import_id,
            TransactionImport.user_id == user_id,
        )

    async def list_by_user(
        self,
        user_id: PydanticObjectId,
        limit: int = 20,
        skip: int = 0,
    ) -> List[TransactionImport]:
        return (
            await TransactionImport.find(TransactionImport.user_id == user_id)
            .sort(-TransactionImport.created_at)
            .skip(skip)
            .limit(limit)
            .to_list()
        )


transaction_import_repo = TransactionImportRepository()
