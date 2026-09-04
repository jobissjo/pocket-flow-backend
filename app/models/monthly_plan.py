from datetime import datetime, timezone
from typing import List, Optional
from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field


class PlannedIncomeItem(BaseModel):
    id: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"))
    title: str
    amount: float
    is_received: bool = False
    notes: Optional[str] = None


class CategoryBudgetItem(BaseModel):
    category_id: PydanticObjectId
    planned_amount: float
    notes: Optional[str] = None


class CustomPlanItem(BaseModel):
    id: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"))
    title: str
    planned_amount: float
    category_id: Optional[PydanticObjectId] = None
    is_completed: bool = False
    notes: Optional[str] = None


class MonthlyPlan(Document):
    user_id: Indexed(PydanticObjectId)
    year: int
    month: int  # 1 to 12
    planned_income: float = 0.0
    income_sources: List[PlannedIncomeItem] = Field(default_factory=list)
    category_budgets: List[CategoryBudgetItem] = Field(default_factory=list)
    custom_items: List[CustomPlanItem] = Field(default_factory=list)
    review_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    class Settings:
        name = "monthly_plans"
        use_state_management = True
