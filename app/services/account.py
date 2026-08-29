from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException, status
from beanie import PydanticObjectId

from app.models.account import Account
from app.models.user import User
from app.repositories.account import account_repo
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate


class AccountService:
    def _to_response(self, account: Account) -> AccountResponse:
        return AccountResponse(
            id=str(account.id),
            user_id=str(account.user_id),
            name=account.name,
            bank_name=account.bank_name,
            account_type=account.account_type,
            last_four=account.last_four,
            balance=account.balance,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

    async def create_account(self, user: User, data: AccountCreate) -> AccountResponse:
        # Extract last 4 digits
        clean_num = data.account_number.replace(" ", "").replace("-", "")
        last_four = clean_num[-4:] if len(clean_num) >= 4 else clean_num.zfill(4)

        account = Account(
            user_id=user.id,
            name=data.name,
            bank_name=data.bank_name,
            account_type=data.account_type,
            account_number=data.account_number,
            last_four=last_four,
            balance=data.balance,
        )
        saved = await account_repo.create(account)
        return self._to_response(saved)

    async def list_accounts(self, user: User) -> List[AccountResponse]:
        accounts = await account_repo.list_by_user(user.id)
        return [self._to_response(acc) for acc in accounts]

    async def get_account(self, account_id: str, user: User) -> AccountResponse:
        try:
            oid = PydanticObjectId(account_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid account ID format.",
            )

        account = await account_repo.get_by_id_and_user(oid, user.id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )
        return self._to_response(account)

    async def update_account(
        self, account_id: str, user: User, data: AccountUpdate
    ) -> AccountResponse:
        try:
            oid = PydanticObjectId(account_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid account ID format.",
            )

        account = await account_repo.get_by_id_and_user(oid, user.id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )

        if data.name is not None:
            account.name = data.name
        if data.bank_name is not None:
            account.bank_name = data.bank_name
        if data.account_type is not None:
            account.account_type = data.account_type
        if data.balance is not None:
            account.balance = data.balance
        if data.account_number is not None:
            account.account_number = data.account_number
            clean_num = data.account_number.replace(" ", "").replace("-", "")
            account.last_four = clean_num[-4:] if len(clean_num) >= 4 else clean_num.zfill(4)

        account.updated_at = datetime.now(timezone.utc)
        saved = await account_repo.save(account)
        return self._to_response(saved)

    async def delete_account(self, account_id: str, user: User) -> None:
        try:
            oid = PydanticObjectId(account_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid account ID format.",
            )

        account = await account_repo.get_by_id_and_user(oid, user.id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )

        await account_repo.delete(account)


account_service = AccountService()
