from datetime import datetime, timezone
import calendar
from typing import Dict, List, Optional
from beanie import PydanticObjectId
from fastapi import HTTPException, status

from app.models.monthly_plan import (
    MonthlyPlan,
    PlannedIncomeItem,
    CategoryBudgetItem,
    CustomPlanItem,
)
from app.models.transaction import TransactionType
from app.models.user import User
from app.repositories.category import category_repo
from app.repositories.monthly_plan import monthly_plan_repo
from app.repositories.transaction import transaction_repo
from app.schemas.monthly_plan import (
    PlannedIncomeItemSchema,
    CategoryBudgetItemSchema,
    CustomPlanItemSchema,
    MonthlyPlanCreate,
    MonthlyPlanUpdate,
    MonthlyPlanResponse,
    CategoryComparisonItem,
    MonthlyPlanComparisonResponse,
)


class MonthlyPlanService:
    def _compute_metrics(self, plan: MonthlyPlan) -> Dict[str, float]:
        cat_budget_total = sum(cb.planned_amount for cb in plan.category_budgets)
        custom_items_total = sum(ci.planned_amount for ci in plan.custom_items)
        total_planned_expenses = round(cat_budget_total + custom_items_total, 2)

        # Planned income from explicit sources or fallback to planned_income
        if plan.income_sources and len(plan.income_sources) > 0:
            effective_planned_income = sum(src.amount for src in plan.income_sources)
        else:
            effective_planned_income = plan.planned_income
        effective_planned_income = round(effective_planned_income, 2)

        net_buffer = round(effective_planned_income - total_planned_expenses, 2)
        income_shortfall = round(max(0.0, total_planned_expenses - effective_planned_income), 2)
        funding_status = "deficit" if income_shortfall > 0 else "surplus"

        return {
            "effective_planned_income": effective_planned_income,
            "total_planned_expenses": total_planned_expenses,
            "net_planned_buffer": net_buffer,
            "funding_status": funding_status,
            "income_shortfall": income_shortfall,
        }

    def _to_response(self, plan: MonthlyPlan) -> MonthlyPlanResponse:
        metrics = self._compute_metrics(plan)
        return MonthlyPlanResponse(
            id=str(plan.id) if plan.id else "",
            user_id=str(plan.user_id),
            year=plan.year,
            month=plan.month,
            planned_income=metrics["effective_planned_income"],
            income_sources=[
                PlannedIncomeItemSchema(
                    id=src.id,
                    title=src.title,
                    amount=src.amount,
                    is_received=src.is_received,
                    notes=src.notes,
                )
                for src in plan.income_sources
            ],
            category_budgets=[
                CategoryBudgetItemSchema(
                    category_id=str(cb.category_id),
                    planned_amount=cb.planned_amount,
                    notes=cb.notes,
                )
                for cb in plan.category_budgets
            ],
            custom_items=[
                CustomPlanItemSchema(
                    id=ci.id,
                    title=ci.title,
                    planned_amount=ci.planned_amount,
                    category_id=str(ci.category_id) if ci.category_id else None,
                    is_completed=ci.is_completed,
                    notes=ci.notes,
                )
                for ci in plan.custom_items
            ],
            review_notes=plan.review_notes,
            total_planned_expenses=metrics["total_planned_expenses"],
            net_planned_buffer=metrics["net_planned_buffer"],
            funding_status=metrics["funding_status"],
            income_shortfall=metrics["income_shortfall"],
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )

    async def get_plan(self, user: User, year: int, month: int) -> MonthlyPlanResponse:
        plan = await monthly_plan_repo.get_by_user_month_year(user.id, year, month)
        if not plan:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            plan = MonthlyPlan(
                user_id=user.id,
                year=year,
                month=month,
                planned_income=0.0,
                income_sources=[],
                category_budgets=[],
                custom_items=[],
                review_notes=None,
                created_at=now,
                updated_at=now,
            )
        return self._to_response(plan)

    async def save_plan(
        self, user: User, year: int, month: int, data: MonthlyPlanUpdate
    ) -> MonthlyPlanResponse:
        plan = await monthly_plan_repo.get_by_user_month_year(user.id, year, month)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if not plan:
            plan = MonthlyPlan(
                user_id=user.id,
                year=year,
                month=month,
                planned_income=0.0,
                income_sources=[],
                category_budgets=[],
                custom_items=[],
                review_notes=None,
                created_at=now,
                updated_at=now,
            )

        if data.planned_income is not None:
            plan.planned_income = data.planned_income

        if data.income_sources is not None:
            plan.income_sources = [
                PlannedIncomeItem(
                    id=src.id or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"),
                    title=src.title,
                    amount=src.amount,
                    is_received=src.is_received,
                    notes=src.notes,
                )
                for src in data.income_sources
            ]
            # Keep planned_income synced
            plan.planned_income = sum(src.amount for src in plan.income_sources)

        if data.category_budgets is not None:
            plan.category_budgets = [
                CategoryBudgetItem(
                    category_id=PydanticObjectId(cb.category_id),
                    planned_amount=cb.planned_amount,
                    notes=cb.notes,
                )
                for cb in data.category_budgets
            ]

        if data.custom_items is not None:
            plan.custom_items = [
                CustomPlanItem(
                    id=ci.id or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"),
                    title=ci.title,
                    planned_amount=ci.planned_amount,
                    category_id=PydanticObjectId(ci.category_id) if ci.category_id else None,
                    is_completed=ci.is_completed,
                    notes=ci.notes,
                )
                for ci in data.custom_items
            ]

        if data.review_notes is not None:
            plan.review_notes = data.review_notes

        plan.updated_at = now
        await monthly_plan_repo.save(plan)

        return self._to_response(plan)

    async def get_comparison(
        self, user: User, year: int, month: int
    ) -> MonthlyPlanComparisonResponse:
        plan = await monthly_plan_repo.get_by_user_month_year(user.id, year, month)
        if not plan:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            plan = MonthlyPlan(
                user_id=user.id,
                year=year,
                month=month,
                planned_income=0.0,
                income_sources=[],
                category_budgets=[],
                custom_items=[],
                review_notes=None,
                created_at=now,
                updated_at=now,
            )

        metrics = self._compute_metrics(plan)
        planned_income = metrics["effective_planned_income"]
        planned_expenses = metrics["total_planned_expenses"]
        income_shortfall = metrics["income_shortfall"]
        funding_status = metrics["funding_status"]

        # Date range for target month
        last_day = calendar.monthrange(year, month)[1]
        start_date = datetime(year, month, 1, 0, 0, 0)
        end_date = datetime(year, month, last_day, 23, 59, 59, 999999)

        # Actual transactions in this month
        totals = await transaction_repo.get_summary_totals(
            user.id, start_date=start_date, end_date=end_date
        )
        actual_income = round(totals.get("income", 0.0), 2)
        actual_expenses = round(totals.get("expense", 0.0), 2)

        income_variance = round(actual_income - planned_income, 2)
        expense_variance = round(planned_expenses - actual_expenses, 2)
        planned_savings = round(planned_income - planned_expenses, 2)
        actual_savings = round(actual_income - actual_expenses, 2)

        # Deficit bridging calculations
        extra_income_earned = round(max(0.0, actual_income - planned_income), 2)
        actual_shortfall_covered = actual_income >= planned_expenses if funding_status == "deficit" else True
        remaining_deficit = round(max(0.0, planned_expenses - actual_income), 2) if funding_status == "deficit" else 0.0

        # Category Breakdown
        actual_category_agg = await transaction_repo.get_category_breakdown(
            user.id, TransactionType.EXPENSE, start_date=start_date, end_date=end_date
        )
        actual_by_cat: Dict[str, float] = {}
        for item in actual_category_agg:
            cat_str = str(item["_id"])
            actual_by_cat[cat_str] = round(float(item["total"]), 2)

        # Build comparison list
        category_comparisons: List[CategoryComparisonItem] = []
        processed_cats = set()

        # 1. Budgeted categories
        for cb in plan.category_budgets:
            cat_id_str = str(cb.category_id)
            processed_cats.add(cat_id_str)
            cat_doc = await category_repo.get_accessible_by_id(cb.category_id, user.id)
            cat_name = cat_doc.name if cat_doc else "Other Expense"
            cat_icon = cat_doc.icon if cat_doc else "tag"

            act_amt = actual_by_cat.get(cat_id_str, 0.0)
            diff = round(cb.planned_amount - act_amt, 2)
            pct = round((act_amt / cb.planned_amount * 100), 1) if cb.planned_amount > 0 else (100.0 if act_amt > 0 else 0.0)

            if act_amt > cb.planned_amount:
                cat_status = "over_budget"
            elif act_amt >= 0.85 * cb.planned_amount:
                cat_status = "on_track"
            else:
                cat_status = "under_budget"

            category_comparisons.append(
                CategoryComparisonItem(
                    category_id=cat_id_str,
                    category_name=cat_name,
                    category_icon=cat_icon,
                    planned_amount=round(cb.planned_amount, 2),
                    actual_amount=act_amt,
                    variance=diff,
                    percentage_used=pct,
                    status=cat_status,
                )
            )

        # 2. Unbudgeted categories that had actual spending
        for cat_id_str, act_amt in actual_by_cat.items():
            if cat_id_str not in processed_cats:
                cat_doc = await category_repo.get_accessible_by_id(PydanticObjectId(cat_id_str), user.id)
                cat_name = cat_doc.name if cat_doc else "Unbudgeted Expense"
                cat_icon = cat_doc.icon if cat_doc else "alert-circle"

                category_comparisons.append(
                    CategoryComparisonItem(
                        category_id=cat_id_str,
                        category_name=cat_name,
                        category_icon=cat_icon,
                        planned_amount=0.0,
                        actual_amount=act_amt,
                        variance=round(-act_amt, 2),
                        percentage_used=100.0 if act_amt > 0 else 0.0,
                        status="over_budget",
                    )
                )

        # Generate "What went well" & "What went wrong" highlights
        what_went_well: List[str] = []
        what_went_wrong: List[str] = []

        # Savings / Deficit feedback
        if funding_status == "deficit":
            if actual_shortfall_covered:
                what_went_well.append(
                    f"Deficit Bridged: Successfully funded this month's planned deficit of ₹{income_shortfall:,.2f} through extra earnings/savings!"
                )
            else:
                what_went_wrong.append(
                    f"Funding Deficit Gap: Started month with ₹{income_shortfall:,.2f} planned deficit; ₹{remaining_deficit:,.2f} still remains uncovered."
                )

        if income_variance > 0:
            what_went_well.append(
                f"Income Boost: Earned ₹{income_variance:,.2f} more than your planned income target!"
            )
        elif income_variance < 0 and planned_income > 0:
            what_went_wrong.append(
                f"Income Lag: Actual income fell short of plan by ₹{abs(income_variance):,.2f}."
            )

        if actual_savings > 0:
            what_went_well.append(
                f"Net Savings: Achieved positive net savings of ₹{actual_savings:,.2f} for the month."
            )
        elif actual_savings < 0:
            what_went_wrong.append(
                f"Cash Burn: Monthly expenses exceeded income by ₹{abs(actual_savings):,.2f}."
            )

        # Under budget wins (any category with positive variance)
        under_budget_cats = [c for c in category_comparisons if c.planned_amount > 0 and c.variance > 0]
        under_budget_cats.sort(key=lambda c: c.variance, reverse=True)
        for cat in under_budget_cats[:3]:
            what_went_well.append(
                f"Under Budget on {cat.category_name}: Saved ₹{cat.variance:,.2f} (used {cat.percentage_used:.0f}% of ₹{cat.planned_amount:,.2f} limit)."
            )

        # Completed planned items
        completed_items = [ci for ci in plan.custom_items if ci.is_completed]
        if completed_items:
            what_went_well.append(
                f"Milestones Achieved: Completed {len(completed_items)} planned goal(s) ({', '.join(ci.title for ci in completed_items[:2])})."
            )

        # Over budget flags
        over_budget_cats = [c for c in category_comparisons if c.status == "over_budget"]
        over_budget_cats.sort(key=lambda c: abs(c.variance), reverse=True)
        for cat in over_budget_cats[:3]:
            if cat.planned_amount > 0:
                overspend = abs(cat.variance)
                what_went_wrong.append(
                    f"Overspent on {cat.category_name}: Exceeded budget by ₹{overspend:,.2f} ({cat.percentage_used:.0f}% spent)."
                )
            else:
                what_went_wrong.append(
                    f"Unbudgeted Expense: Spent ₹{cat.actual_amount:,.2f} on {cat.category_name} without an allocation."
                )

        if not what_went_well:
            what_went_well.append("Stayed on track with planned timeline.")
        if not what_went_wrong:
            what_went_wrong.append("No major budget overruns detected this month!")

        return MonthlyPlanComparisonResponse(
            year=year,
            month=month,
            planned_income=planned_income,
            actual_income=actual_income,
            income_variance=income_variance,
            planned_expenses=planned_expenses,
            actual_expenses=actual_expenses,
            expense_variance=expense_variance,
            planned_savings=planned_savings,
            actual_savings=actual_savings,
            funding_status=funding_status,
            income_shortfall=income_shortfall,
            actual_shortfall_covered=actual_shortfall_covered,
            extra_income_earned=extra_income_earned,
            remaining_deficit=remaining_deficit,
            what_went_well=what_went_well,
            what_went_wrong=what_went_wrong,
            category_comparisons=category_comparisons,
            custom_items=[
                CustomPlanItemSchema(
                    id=ci.id,
                    title=ci.title,
                    planned_amount=ci.planned_amount,
                    category_id=str(ci.category_id) if ci.category_id else None,
                    is_completed=ci.is_completed,
                    notes=ci.notes,
                )
                for ci in plan.custom_items
            ],
            income_sources=[
                PlannedIncomeItemSchema(
                    id=src.id,
                    title=src.title,
                    amount=src.amount,
                    is_received=src.is_received,
                    notes=src.notes,
                )
                for src in plan.income_sources
            ],
            review_notes=plan.review_notes,
        )

    async def copy_from_previous_month(
        self,
        user: User,
        target_year: int,
        target_month: int,
        source_year: Optional[int] = None,
        source_month: Optional[int] = None,
    ) -> MonthlyPlanResponse:
        if source_year is None or source_month is None:
            if target_month == 1:
                source_year = target_year - 1
                source_month = 12
            else:
                source_year = target_year
                source_month = target_month - 1

        source_plan = await monthly_plan_repo.get_by_user_month_year(
            user.id, source_year, source_month
        )

        if not source_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No plan found for previous month ({source_month}/{source_year}) to copy from.",
            )

        target_plan = await monthly_plan_repo.get_by_user_month_year(
            user.id, target_year, target_month
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if not target_plan:
            target_plan = MonthlyPlan(
                user_id=user.id,
                year=target_year,
                month=target_month,
                planned_income=source_plan.planned_income,
                income_sources=[
                    PlannedIncomeItem(
                        id=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + str(i),
                        title=s.title,
                        amount=s.amount,
                        is_received=False,
                        notes=s.notes,
                    )
                    for i, s in enumerate(source_plan.income_sources)
                ],
                category_budgets=[
                    CategoryBudgetItem(
                        category_id=cb.category_id,
                        planned_amount=cb.planned_amount,
                        notes=cb.notes,
                    )
                    for cb in source_plan.category_budgets
                ],
                custom_items=[],
                review_notes=None,
                created_at=now,
                updated_at=now,
            )
        else:
            target_plan.planned_income = source_plan.planned_income
            target_plan.income_sources = [
                PlannedIncomeItem(
                    id=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + str(i),
                    title=s.title,
                    amount=s.amount,
                    is_received=False,
                    notes=s.notes,
                )
                for i, s in enumerate(source_plan.income_sources)
            ]
            target_plan.category_budgets = [
                CategoryBudgetItem(
                    category_id=cb.category_id,
                    planned_amount=cb.planned_amount,
                    notes=cb.notes,
                )
                for cb in source_plan.category_budgets
            ]
            target_plan.updated_at = now

        await monthly_plan_repo.save(target_plan)
        return self._to_response(target_plan)


monthly_plan_service = MonthlyPlanService()
