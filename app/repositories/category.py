from typing import List, Optional
from beanie import PydanticObjectId
from beanie.operators import Or
from app.models.category import Category, CategoryType
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self):
        super().__init__(Category)

    async def list_for_user(
        self, user_id: PydanticObjectId, category_type: Optional[CategoryType] = None
    ) -> List[Category]:
        conditions = [
            Or(Category.is_system == True, Category.user_id == user_id)
        ]
        if category_type:
            conditions.append(Category.type == category_type)
        return (
            await Category.find(*conditions)
            .sort(Category.name)
            .to_list()
        )

    async def get_accessible_by_id(
        self, category_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> Optional[Category]:
        return await Category.find_one(
            Category.id == category_id,
            Or(Category.is_system == True, Category.user_id == user_id),
        )

    async def get_custom_by_id_and_user(
        self, category_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> Optional[Category]:
        return await Category.find_one(
            Category.id == category_id,
            Category.user_id == user_id,
            Category.is_system == False,
        )

    async def get_by_ids(self, category_ids: List[PydanticObjectId]) -> List[Category]:
        return await Category.find({"_id": {"$in": category_ids}}).to_list()


category_repo = CategoryRepository()
