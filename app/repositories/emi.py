from typing import List, Optional
from beanie import PydanticObjectId
from app.models.emi import EMI, EMIStatus
from app.repositories.base import BaseRepository


class EMIRepository(BaseRepository[EMI]):
    def __init__(self):
        super().__init__(EMI)

    async def get_by_id_and_user(
        self, emi_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> Optional[EMI]:
        return await EMI.find_one(
            EMI.id == emi_id,
            EMI.user_id == user_id,
        )

    async def list_by_user(
        self, user_id: PydanticObjectId, status: Optional[EMIStatus] = None
    ) -> List[EMI]:
        query = {"user_id": user_id}
        if status:
            query["status"] = status.value
        return await EMI.find(query).sort(EMI.due_day).to_list()

    async def get_active_emis(self, user_id: PydanticObjectId) -> List[EMI]:
        return await EMI.find(
            EMI.user_id == user_id,
            EMI.status == EMIStatus.ACTIVE,
        ).sort(EMI.due_day).to_list()


emi_repo = EMIRepository()
