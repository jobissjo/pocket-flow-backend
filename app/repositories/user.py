from typing import Optional
from beanie import PydanticObjectId
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await User.find_one(User.email == email.lower())

    async def get_by_mobile(self, mobile: str) -> Optional[User]:
        if not mobile:
            return None
        return await User.find_one(User.mobile == mobile)


user_repo = UserRepository()
