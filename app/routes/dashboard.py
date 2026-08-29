from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.dashboard import AnalyticsResponse, SummaryResponse
from app.schemas.emi import EMIResponse
from app.schemas.transaction import TransactionResponse
from app.services.dashboard import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=SummaryResponse,
    summary="Get financial summary",
    description="Returns aggregate total balances, total income, total expenses, credit card outstanding, and savings percentage.",
)
async def get_summary(
    start_date: Optional[datetime] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date filter (ISO format)"),
    current_user: User = Depends(get_current_user),
) -> SummaryResponse:
    return await dashboard_service.get_summary(
        current_user, start_date=start_date, end_date=end_date
    )


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    summary="Get dashboard analytics",
    description="Returns monthly income vs expense time series and category-wise income & expense breakdowns with percentages.",
)
async def get_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date filter (ISO format)"),
    current_user: User = Depends(get_current_user),
) -> AnalyticsResponse:
    return await dashboard_service.get_analytics(
        current_user, start_date=start_date, end_date=end_date
    )


@router.get(
    "/recent-transactions",
    response_model=List[TransactionResponse],
    summary="Get recent transactions",
    description="Retrieves the most recent transactions for dashboard quick view.",
)
async def get_recent_transactions(
    limit: int = Query(10, ge=1, le=50, description="Number of transactions to return"),
    current_user: User = Depends(get_current_user),
) -> List[TransactionResponse]:
    return await dashboard_service.get_recent_transactions(
        current_user, limit=limit
    )


@router.get(
    "/upcoming-emi",
    response_model=List[EMIResponse],
    summary="Get upcoming EMIs",
    description="Retrieves active EMIs sorted by upcoming payment due date.",
)
async def get_upcoming_emi(
    limit: int = Query(10, ge=1, le=50, description="Number of upcoming EMIs to return"),
    current_user: User = Depends(get_current_user),
) -> List[EMIResponse]:
    return await dashboard_service.get_upcoming_emi(current_user, limit=limit)
