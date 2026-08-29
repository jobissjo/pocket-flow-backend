from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_current_user
from app.models.transaction import TransactionType
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionFilterParams,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.transaction import transaction_service

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create transaction",
    description="Records an income or expense transaction, updating linked account balance or credit card outstanding.",
)
async def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    return await transaction_service.create_transaction(current_user, data)


@router.get(
    "",
    response_model=PaginatedResponse[TransactionResponse],
    summary="List transactions with filters and pagination",
    description="Retrieves a paginated list of transactions filtered by type, category, account, date range, or search keyword.",
)
async def list_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in title or notes"),
    type: Optional[TransactionType] = Query(None, description="Filter by income or expense"),
    category: Optional[str] = Query(None, description="Filter by Category ID"),
    account: Optional[str] = Query(None, description="Filter by Account ID"),
    credit_card: Optional[str] = Query(None, description="Filter by Credit Card ID"),
    start_date: Optional[datetime] = Query(None, description="Filter from start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter to end date (ISO format)"),
    min_amount: Optional[float] = Query(None, ge=0, description="Minimum transaction amount"),
    max_amount: Optional[float] = Query(None, ge=0, description="Maximum transaction amount"),
    sort_by: str = Query("date", pattern=r"^(date|amount|title|created_at)$"),
    sort_order: str = Query("desc", pattern=r"^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[TransactionResponse]:
    params = TransactionFilterParams(
        page=page,
        limit=limit,
        search=search,
        type=type,
        category_id=category,
        account_id=account,
        credit_card_id=credit_card,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await transaction_service.list_transactions(current_user, params)


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get transaction details",
    description="Retrieves a specific transaction by its ID.",
)
async def get_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    return await transaction_service.get_transaction(transaction_id, current_user)


@router.patch(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Update transaction",
    description="Updates transaction details and adjusts balances accordingly.",
)
async def update_transaction(
    transaction_id: str,
    data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    return await transaction_service.update_transaction(
        transaction_id, current_user, data
    )


@router.delete(
    "/{transaction_id}",
    response_model=MessageResponse,
    summary="Delete transaction",
    description="Deletes a transaction and reverses its effect on account balance or credit card outstanding.",
)
async def delete_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await transaction_service.delete_transaction(transaction_id, current_user)
    return MessageResponse(message="Transaction deleted successfully.")
