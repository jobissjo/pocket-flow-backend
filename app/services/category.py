from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from beanie import PydanticObjectId

from app.models.category import Category, CategoryType
from app.models.user import User
from app.repositories.category import category_repo
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate


class CategoryService:
    def _to_response(self, cat: Category) -> CategoryResponse:
        return CategoryResponse(
            id=str(cat.id),
            name=cat.name,
            type=cat.type,
            icon=cat.icon,
            is_system=cat.is_system,
            user_id=str(cat.user_id) if cat.user_id else None,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
        )

    async def create_category(self, user: User, data: CategoryCreate) -> CategoryResponse:
        category = Category(
            name=data.name,
            type=data.type,
            icon=data.icon,
            is_system=False,
            user_id=user.id,
        )
        saved = await category_repo.create(category)
        return self._to_response(saved)

    async def list_categories(
        self, user: User, category_type: Optional[CategoryType] = None
    ) -> List[CategoryResponse]:
        categories = await category_repo.list_for_user(user.id, category_type)
        return [self._to_response(c) for c in categories]

    async def get_category(self, category_id: str, user: User) -> CategoryResponse:
        try:
            oid = PydanticObjectId(category_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID format.",
            )

        cat = await category_repo.get_accessible_by_id(oid, user.id)
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )
        return self._to_response(cat)

    async def update_category(
        self, category_id: str, user: User, data: CategoryUpdate
    ) -> CategoryResponse:
        try:
            oid = PydanticObjectId(category_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID format.",
            )

        cat = await category_repo.get_accessible_by_id(oid, user.id)
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )

        if cat.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Default system categories cannot be modified.",
            )

        if cat.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this category.",
            )

        if data.name is not None:
            cat.name = data.name
        if data.type is not None:
            cat.type = data.type
        if data.icon is not None:
            cat.icon = data.icon

        cat.updated_at = datetime.now(timezone.utc)
        saved = await category_repo.save(cat)
        return self._to_response(saved)

    async def delete_category(self, category_id: str, user: User) -> None:
        try:
            oid = PydanticObjectId(category_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID format.",
            )

        cat = await category_repo.get_accessible_by_id(oid, user.id)
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )

        if cat.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Default system categories cannot be deleted.",
            )

        if cat.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this category.",
            )

        await category_repo.delete(cat)


category_service = CategoryService()
