from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.monthly_plan import (
    MonthlyPlanResponse,
    MonthlyPlanUpdate,
    MonthlyPlanComparisonResponse,
    CopyPreviousMonthRequest,
)
from app.services.monthly_plan import monthly_plan_service

router = APIRouter(prefix="/monthly-planner", tags=["Monthly Planner"])


@router.get(
    "",
    response_model=MonthlyPlanResponse,
    summary="Get monthly plan",
    description="Retrieves the planned budget and expenses for a given month and year. Returns a template if no plan exists.",
)
async def get_monthly_plan(
    year: int = Query(..., description="Target year (e.g. 2026)"),
    month: int = Query(..., ge=1, le=12, description="Target month (1-12)"),
    current_user: User = Depends(get_current_user),
) -> MonthlyPlanResponse:
    return await monthly_plan_service.get_plan(current_user, year, month)


@router.put(
    "",
    response_model=MonthlyPlanResponse,
    summary="Save or update monthly plan",
    description="Saves planned income streams, category budgets, custom planned items, and retrospective notes.",
)
async def save_monthly_plan(
    data: MonthlyPlanUpdate,
    year: int = Query(..., description="Target year (e.g. 2026)"),
    month: int = Query(..., ge=1, le=12, description="Target month (1-12)"),
    current_user: User = Depends(get_current_user),
) -> MonthlyPlanResponse:
    return await monthly_plan_service.save_plan(current_user, year, month, data)


@router.get(
    "/comparison",
    response_model=MonthlyPlanComparisonResponse,
    summary="Get monthly plan vs actuals comparison",
    description="Calculates planned vs actual spending and income, funding shortfall/deficit status, and generates automated 'what went good' and 'what went wrong' insights.",
)
async def get_monthly_plan_comparison(
    year: int = Query(..., description="Target year (e.g. 2026)"),
    month: int = Query(..., ge=1, le=12, description="Target month (1-12)"),
    current_user: User = Depends(get_current_user),
) -> MonthlyPlanComparisonResponse:
    return await monthly_plan_service.get_comparison(current_user, year, month)


@router.post(
    "/copy-previous",
    response_model=MonthlyPlanResponse,
    summary="Copy budget from previous month",
    description="Clones the category budget allocations and standard income from the previous month to jump-start the current month's plan.",
)
async def copy_previous_month_plan(
    data: CopyPreviousMonthRequest,
    current_user: User = Depends(get_current_user),
) -> MonthlyPlanResponse:
    return await monthly_plan_service.copy_from_previous_month(
        current_user,
        target_year=data.target_year,
        target_month=data.target_month,
        source_year=data.source_year,
        source_month=data.source_month,
    )
