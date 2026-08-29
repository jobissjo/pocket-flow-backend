from typing import List
from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.schemas.common import MessageResponse
from app.services.account import account_service

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
    description="Adds a bank, salary, cash, or wallet account for the authenticated user.",
)
async def create_account(
    data: AccountCreate,
    current_user: User = Depends(get_current_user),
) -> AccountResponse:
    return await account_service.create_account(current_user, data)


@router.get(
    "",
    response_model=List[AccountResponse],
    summary="List all accounts",
    description="Retrieves all bank and cash accounts belonging to the authenticated user.",
)
async def list_accounts(
    current_user: User = Depends(get_current_user),
) -> List[AccountResponse]:
    return await account_service.list_accounts(current_user)


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get account details",
    description="Retrieves details for a specific user-owned account.",
)
async def get_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
) -> AccountResponse:
    return await account_service.get_account(account_id, current_user)


@router.patch(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Update account details",
    description="Updates account properties like name, bank name, or balance.",
)
async def update_account(
    account_id: str,
    data: AccountUpdate,
    current_user: User = Depends(get_current_user),
) -> AccountResponse:
    return await account_service.update_account(account_id, current_user, data)


@router.delete(
    "/{account_id}",
    response_model=MessageResponse,
    summary="Delete account",
    description="Deletes a specific user account.",
)
async def delete_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await account_service.delete_account(account_id, current_user)
    return MessageResponse(message="Account deleted successfully.")
