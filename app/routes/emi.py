from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_current_user
from app.models.emi import EMIStatus
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.emi import (
    EMICreate,
    EMIMarkPaidResponse,
    EMIResponse,
    EMIUpdate,
)
from app.services.emi import emi_service

router = APIRouter(prefix="/emi", tags=["EMI"])


@router.post(
    "",
    response_model=EMIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an EMI",
    description="Registers an EMI plan with installment counts, due day, and linked account/card.",
)
async def create_emi(
    data: EMICreate,
    current_user: User = Depends(get_current_user),
) -> EMIResponse:
    return await emi_service.create_emi(current_user, data)


@router.get(
    "",
    response_model=List[EMIResponse],
    summary="List all EMIs",
    description="Retrieves EMIs belonging to the user, with calculated next payment dates and statuses.",
)
async def list_emis(
    status: Optional[EMIStatus] = Query(None, description="Filter by status (active/completed/overdue)"),
    current_user: User = Depends(get_current_user),
) -> List[EMIResponse]:
    return await emi_service.list_emis(current_user, status=status)


@router.get(
    "/{emi_id}",
    response_model=EMIResponse,
    summary="Get EMI details",
    description="Retrieves a specific EMI schedule and payment tracking information.",
)
async def get_emi(
    emi_id: str,
    current_user: User = Depends(get_current_user),
) -> EMIResponse:
    return await emi_service.get_emi(emi_id, current_user)


@router.patch(
    "/{emi_id}",
    response_model=EMIResponse,
    summary="Update EMI",
    description="Updates EMI details such as monthly amount or installment progress.",
)
async def update_emi(
    emi_id: str,
    data: EMIUpdate,
    current_user: User = Depends(get_current_user),
) -> EMIResponse:
    return await emi_service.update_emi(emi_id, current_user, data)


@router.delete(
    "/{emi_id}",
    response_model=MessageResponse,
    summary="Delete EMI",
    description="Deletes an EMI tracker.",
)
async def delete_emi(
    emi_id: str,
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await emi_service.delete_emi(emi_id, current_user)
    return MessageResponse(message="EMI deleted successfully.")


@router.post(
    "/{emi_id}/mark-paid",
    response_model=EMIMarkPaidResponse,
    summary="Mark EMI installment as paid",
    description="Increments paid installment count, recalculates next payment date, marks completed if finished, and adjusts linked account balance.",
)
async def mark_emi_paid(
    emi_id: str,
    current_user: User = Depends(get_current_user),
) -> EMIMarkPaidResponse:
    return await emi_service.mark_paid(emi_id, current_user)
