from datetime import datetime
from typing import List, Optional
from beanie import PydanticObjectId

from app.models.category import CategoryType
from app.models.transaction import TransactionType
from app.models.user import User
from app.repositories.account import account_repo
from app.repositories.category import category_repo
from app.repositories.credit_card import credit_card_repo
from app.repositories.emi import emi_repo
from app.repositories.transaction import transaction_repo
from app.schemas.dashboard import (
    AnalyticsResponse,
    CategoryBreakdownItem,
    SummaryResponse,
    TimeSeriesDataPoint,
)
from app.schemas.emi import EMIResponse
from app.schemas.transaction import TransactionResponse
from app.services.emi import emi_service
from app.services.transaction import transaction_service


class DashboardService:
    async def get_summary(
        self,
        user: User,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> SummaryResponse:
        total_balance = await account_repo.get_total_balance(user.id)
        total_outstanding = await credit_card_repo.get_total_outstanding(user.id)
        totals = await transaction_repo.get_summary_totals(
            user.id, start_date=start_date, end_date=end_date
        )

        income = totals.get("income", 0.0)
        expenses = totals.get("expense", 0.0)
        net_savings = income - expenses
        savings_percentage = round((net_savings / income * 100), 2) if income > 0 else 0.0

        return SummaryResponse(
            total_balance=round(total_balance, 2),
            total_income=round(income, 2),
            total_expenses=round(expenses, 2),
            total_credit_card_outstanding=round(total_outstanding, 2),
            net_savings=round(net_savings, 2),
            savings_percentage=savings_percentage,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_analytics(
        self,
        user: User,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> AnalyticsResponse:
        # Time series
        time_series_raw = await transaction_repo.get_income_expense_time_series(
            user.id, start_date=start_date, end_date=end_date
        )
        time_series = [TimeSeriesDataPoint(**p) for p in time_series_raw]

        # Expense breakdown
        expense_agg = await transaction_repo.get_category_breakdown(
            user.id, TransactionType.EXPENSE, start_date, end_date
        )
        total_exp = sum(float(item["total"]) for item in expense_agg)
        expense_breakdown: List[CategoryBreakdownItem] = []
        for item in expense_agg:
            cat_id = item["_id"]
            cat = await category_repo.get_accessible_by_id(cat_id, user.id)
            cat_name = cat.name if cat else "Uncategorized"
            cat_icon = cat.icon if cat else "tag"
            amt = float(item["total"])
            pct = round((amt / total_exp * 100), 2) if total_exp > 0 else 0.0
            expense_breakdown.append(
                CategoryBreakdownItem(
                    category_id=str(cat_id),
                    category_name=cat_name,
                    category_icon=cat_icon,
                    amount=round(amt, 2),
                    percentage=pct,
                )
            )

        # Income breakdown
        income_agg = await transaction_repo.get_category_breakdown(
            user.id, TransactionType.INCOME, start_date, end_date
        )
        total_inc = sum(float(item["total"]) for item in income_agg)
        income_breakdown: List[CategoryBreakdownItem] = []
        for item in income_agg:
            cat_id = item["_id"]
            cat = await category_repo.get_accessible_by_id(cat_id, user.id)
            cat_name = cat.name if cat else "Uncategorized"
            cat_icon = cat.icon if cat else "tag"
            amt = float(item["total"])
            pct = round((amt / total_inc * 100), 2) if total_inc > 0 else 0.0
            income_breakdown.append(
                CategoryBreakdownItem(
                    category_id=str(cat_id),
                    category_name=cat_name,
                    category_icon=cat_icon,
                    amount=round(amt, 2),
                    percentage=pct,
                )
            )

        return AnalyticsResponse(
            income_vs_expense=time_series,
            expense_breakdown=expense_breakdown,
            income_breakdown=income_breakdown,
        )

    async def get_recent_transactions(
        self, user: User, limit: int = 10
    ) -> List[TransactionResponse]:
        txs = await transaction_repo.get_recent(user.id, limit=limit)
        return [await transaction_service._populate_response(tx, user) for tx in txs]

    async def get_upcoming_emi(
        self, user: User, limit: int = 10
    ) -> List[EMIResponse]:
        active_emis = await emi_repo.get_active_emis(user.id)
        responses = [emi_service._to_response(e) for e in active_emis]
        # Sort by upcoming next payment date
        upcoming = [r for r in responses if r.next_payment_date is not None]
        upcoming.sort(key=lambda x: x.next_payment_date)
        return upcoming[:limit]


dashboard_service = DashboardService()
