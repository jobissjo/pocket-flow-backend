from typing import List
from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.core.dependencies import get_current_user
from app.models.user import User
from app.transaction_import.schemas import (
    TransactionImportConfirmRequest,
    TransactionImportResponse,
)
from app.transaction_import.service import transaction_import_service

router = APIRouter(prefix="/transaction-imports", tags=["Transaction Imports"])


@router.post(
    "/image",
    response_model=TransactionImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload image for AI transaction extraction",
    description="Uploads a receipt, bill, invoice, UPI screenshot, or payment proof. AI extracts structured details and creates a draft for review.",
)
async def upload_transaction_image(
    file: UploadFile = File(..., description="Image file (JPEG, PNG, WEBP, HEIC, etc.)"),
    current_user: User = Depends(get_current_user),
) -> TransactionImportResponse:
    return await transaction_import_service.process_image_upload(current_user, file)


@router.get(
    "/{import_id}",
    response_model=TransactionImportResponse,
    summary="Get transaction import draft",
    description="Retrieves the transaction import record and draft by ID for user review.",
)
async def get_transaction_import(
    import_id: str,
    current_user: User = Depends(get_current_user),
) -> TransactionImportResponse:
    return await transaction_import_service.get_import(current_user, import_id)


@router.get(
    "",
    response_model=List[TransactionImportResponse],
    summary="List transaction imports",
    description="Retrieves a list of recent transaction import attempts for the current user.",
)
async def list_transaction_imports(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    skip: int = Query(0, ge=0, description="Items to skip"),
    current_user: User = Depends(get_current_user),
) -> List[TransactionImportResponse]:
    return await transaction_import_service.list_imports(current_user, limit=limit, skip=skip)


@router.post(
    "/{import_id}/confirm",
    response_model=TransactionImportResponse,
    summary="Confirm transaction import draft",
    description="Validates user-reviewed transaction data, creates the final financial transaction, adjusts account balances, and links it to the import record.",
)
async def confirm_transaction_import(
    import_id: str,
    data: TransactionImportConfirmRequest,
    current_user: User = Depends(get_current_user),
) -> TransactionImportResponse:
    return await transaction_import_service.confirm_import(current_user, import_id, data)


@router.post(
    "/{import_id}/reject",
    response_model=TransactionImportResponse,
    summary="Reject transaction import draft",
    description="Rejects and cancels a transaction import draft.",
)
async def reject_transaction_import(
    import_id: str,
    current_user: User = Depends(get_current_user),
) -> TransactionImportResponse:
    return await transaction_import_service.reject_import(current_user, import_id)
