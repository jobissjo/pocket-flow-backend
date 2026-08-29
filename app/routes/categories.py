from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_current_user
from app.models.category import CategoryType
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.schemas.common import MessageResponse
from app.services.category import category_service

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create custom category",
    description="Creates a new custom income or expense category for the current user.",
)
async def create_category(
    data: CategoryCreate,
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    return await category_service.create_category(current_user, data)


@router.get(
    "",
    response_model=List[CategoryResponse],
    summary="List all categories",
    description="Retrieves both system default categories and user custom categories.",
)
async def list_categories(
    type: Optional[CategoryType] = Query(None, description="Filter by category type (income/expense)"),
    current_user: User = Depends(get_current_user),
) -> List[CategoryResponse]:
    return await category_service.list_categories(current_user, category_type=type)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get category details",
    description="Retrieves a specific system or user category.",
)
async def get_category(
    category_id: str,
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    return await category_service.get_category(category_id, current_user)


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update custom category",
    description="Updates a custom category created by the user (system categories cannot be edited).",
)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    return await category_service.update_category(category_id, current_user, data)


@router.delete(
    "/{category_id}",
    response_model=MessageResponse,
    summary="Delete custom category",
    description="Deletes a user's custom category (system categories cannot be deleted).",
)
async def delete_category(
    category_id: str,
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await category_service.delete_category(category_id, current_user)
    return MessageResponse(message="Category deleted successfully.")
