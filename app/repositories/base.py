from typing import Generic, List, Optional, Type, TypeVar
from beanie import Document, PydanticObjectId

DocType = TypeVar("DocType", bound=Document)


class BaseRepository(Generic[DocType]):
    def __init__(self, model: Type[DocType]):
        self.model = model

    async def get_by_id(self, doc_id: PydanticObjectId) -> Optional[DocType]:
        return await self.model.get(doc_id)

    async def get_user_doc(
        self, doc_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> Optional[DocType]:
        return await self.model.find_one(
            self.model.id == doc_id,
            self.model.user_id == user_id,
        )

    async def list_by_user(
        self, user_id: PydanticObjectId, skip: int = 0, limit: int = 100
    ) -> List[DocType]:
        return (
            await self.model.find(self.model.user_id == user_id)
            .sort(-self.model.created_at)
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def create(self, document: DocType) -> DocType:
        return await document.insert()

    async def save(self, document: DocType) -> DocType:
        return await document.save()

    async def delete(self, document: DocType) -> None:
        await document.delete()
