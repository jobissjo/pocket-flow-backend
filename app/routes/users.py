from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse, UserUpdate
from app.services.user import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get user profile",
    description="Returns the profile information of the current logged-in user.",
)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return user_service.get_profile(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update user profile",
    description="Updates user profile fields such as full name and mobile number.",
)
async def update_user_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return await user_service.update_profile(current_user, data)


@router.delete(
    "/me",
    response_model=MessageResponse,
    summary="Delete user account",
    description="Permanently deletes the user account and associated personal financial data.",
)
async def delete_user_profile(
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await user_service.delete_account(current_user)
    return MessageResponse(message="User account deleted successfully.")
