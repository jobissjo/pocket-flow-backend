from datetime import datetime, timezone
from fastapi import HTTPException, status
from beanie import PydanticObjectId

from app.models.user import User
from app.models.account import Account
from app.models.credit_card import CreditCard
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.emi import EMI
from app.repositories.user import user_repo
from app.schemas.user import UserResponse, UserUpdate


class UserService:
    def get_profile(self, user: User) -> UserResponse:
        return UserResponse(
            id=str(user.id),
            email=user.email,
            mobile=user.mobile,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def update_profile(self, user: User, data: UserUpdate) -> UserResponse:
        if data.mobile is not None and data.mobile != user.mobile:
            existing = await user_repo.get_by_mobile(data.mobile)
            if existing and existing.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mobile number already in use by another account.",
                )
            user.mobile = data.mobile

        if data.full_name is not None:
            user.full_name = data.full_name

        user.updated_at = datetime.now(timezone.utc)
        saved = await user_repo.save(user)
        return self.get_profile(saved)

    async def delete_account(self, user: User) -> None:
        user_id = user.id
        # Cascade delete user-owned records
        await Transaction.find(Transaction.user_id == user_id).delete()
        await EMI.find(EMI.user_id == user_id).delete()
        await Account.find(Account.user_id == user_id).delete()
        await CreditCard.find(CreditCard.user_id == user_id).delete()
        await Category.find(Category.user_id == user_id, Category.is_system == False).delete()
        await user_repo.delete(user)


user_service = UserService()
