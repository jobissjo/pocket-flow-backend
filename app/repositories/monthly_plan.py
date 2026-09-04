from datetime import datetime, timezone
from typing import Optional
from beanie import PydanticObjectId
from app.models.monthly_plan import MonthlyPlan
from app.repositories.base import BaseRepository


class MonthlyPlanRepository(BaseRepository[MonthlyPlan]):
    def __init__(self):
        super().__init__(MonthlyPlan)

    async def get_by_user_month_year(
        self, user_id: PydanticObjectId, year: int, month: int
    ) -> Optional[MonthlyPlan]:
        return await MonthlyPlan.find_one(
            MonthlyPlan.user_id == user_id,
            MonthlyPlan.year == year,
            MonthlyPlan.month == month,
        )


monthly_plan_repo = MonthlyPlanRepository()
