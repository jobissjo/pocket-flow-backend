from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PlannedIncomeItemSchema(BaseModel):
    id: Optional[str] = None
    title: str
    amount: float = Field(ge=0)
    is_received: bool = False
    notes: Optional[str] = None


class CategoryBudgetItemSchema(BaseModel):
    category_id: str
    planned_amount: float = Field(ge=0)
    notes: Optional[str] = None


class CustomPlanItemSchema(BaseModel):
    id: Optional[str] = None
    title: str
    planned_amount: float = Field(ge=0)
    category_id: Optional[str] = None
    is_completed: bool = False
    notes: Optional[str] = None


class MonthlyPlanCreate(BaseModel):
    year: int
    month: int = Field(ge=1, le=12)
    planned_income: float = Field(default=0.0, ge=0)
    income_sources: List[PlannedIncomeItemSchema] = Field(default_factory=list)
    category_budgets: List[CategoryBudgetItemSchema] = Field(default_factory=list)
    custom_items: List[CustomPlanItemSchema] = Field(default_factory=list)
    review_notes: Optional[str] = None


class MonthlyPlanUpdate(BaseModel):
    planned_income: Optional[float] = Field(default=None, ge=0)
    income_sources: Optional[List[PlannedIncomeItemSchema]] = None
    category_budgets: Optional[List[CategoryBudgetItemSchema]] = None
    custom_items: Optional[List[CustomPlanItemSchema]] = None
    review_notes: Optional[str] = None


class MonthlyPlanResponse(BaseModel):
    id: str
    user_id: str
    year: int
    month: int
    planned_income: float
    income_sources: List[PlannedIncomeItemSchema] = Field(default_factory=list)
    category_budgets: List[CategoryBudgetItemSchema] = Field(default_factory=list)
    custom_items: List[CustomPlanItemSchema] = Field(default_factory=list)
    review_notes: Optional[str] = None
    total_planned_expenses: float
    net_planned_buffer: float
    funding_status: str  # "surplus" | "deficit"
    income_shortfall: float
    created_at: datetime
    updated_at: datetime


class CategoryComparisonItem(BaseModel):
    category_id: str
    category_name: str
    category_icon: str
    planned_amount: float
    actual_amount: float
    variance: float  # planned - actual (positive = under budget, negative = over budget)
    percentage_used: float
    status: str  # "under_budget" | "on_track" | "over_budget"


class MonthlyPlanComparisonResponse(BaseModel):
    year: int
    month: int
    planned_income: float
    actual_income: float
    income_variance: float  # actual - planned
    planned_expenses: float
    actual_expenses: float
    expense_variance: float  # planned - actual (positive = spent less than planned)
    planned_savings: float  # planned_income - planned_expenses
    actual_savings: float  # actual_income - actual_expenses
    funding_status: str  # "surplus" | "deficit"
    income_shortfall: float  # max(0, planned_expenses - planned_income)
    actual_shortfall_covered: bool
    extra_income_earned: float
    remaining_deficit: float
    what_went_well: List[str] = Field(default_factory=list)
    what_went_wrong: List[str] = Field(default_factory=list)
    category_comparisons: List[CategoryComparisonItem] = Field(default_factory=list)
    custom_items: List[CustomPlanItemSchema] = Field(default_factory=list)
    income_sources: List[PlannedIncomeItemSchema] = Field(default_factory=list)
    review_notes: Optional[str] = None


class CopyPreviousMonthRequest(BaseModel):
    target_year: int
    target_month: int = Field(ge=1, le=12)
    source_year: Optional[int] = None
    source_month: Optional[int] = Field(default=None, ge=1, le=12)
