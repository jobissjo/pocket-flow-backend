from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.schemas.transaction import TransactionResponse
from app.schemas.emi import EMIResponse


class SummaryResponse(BaseModel):
    total_balance: float
    total_income: float
    total_expenses: float
    total_credit_card_outstanding: float
    net_savings: float
    savings_percentage: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class TimeSeriesDataPoint(BaseModel):
    period: str  # e.g., "2026-01" or "2026-01-15"
    income: float
    expense: float
    net: float


class CategoryBreakdownItem(BaseModel):
    category_id: str
    category_name: str
    category_icon: str
    amount: float
    percentage: float


class AnalyticsResponse(BaseModel):
    income_vs_expense: List[TimeSeriesDataPoint]
    expense_breakdown: List[CategoryBreakdownItem]
    income_breakdown: List[CategoryBreakdownItem]
