import calendar
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from beanie import PydanticObjectId

from app.models.account import Account
from app.models.credit_card import CreditCard
from app.models.emi import EMI, EMIStatus
from app.models.user import User
from app.repositories.account import account_repo
from app.repositories.credit_card import credit_card_repo
from app.repositories.emi import emi_repo
from app.schemas.emi import (
    EMICreate,
    EMIMarkPaidResponse,
    EMIResponse,
    EMIUpdate,
)


class EMIService:
    def _calculate_next_payment_date(
        self, start_date: datetime, due_day: int, paid_installments: int, total_installments: int
    ) -> Optional[datetime]:
        if paid_installments >= total_installments:
            return None

        # Determine year and month of next installment
        month_offset = paid_installments
        start_year = start_date.year
        start_month = start_date.month

        total_months = (start_year * 12 + (start_month - 1)) + month_offset
        next_year = total_months // 12
        next_month = (total_months % 12) + 1

        # Handle max days in the month (e.g. Feb 28/29 or 30 vs 31)
        max_day = calendar.monthrange(next_year, next_month)[1]
        valid_day = min(due_day, max_day)

        return datetime(
            year=next_year,
            month=next_month,
            day=valid_day,
            hour=12,
            minute=0,
            second=0,
        )

    def _determine_status(
        self, emi: EMI, next_payment_date: Optional[datetime]
    ) -> EMIStatus:
        if emi.paid_installments >= emi.total_installments:
            return EMIStatus.COMPLETED

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        date_to_compare = (
            next_payment_date.replace(tzinfo=None) if next_payment_date else None
        )
        if date_to_compare and date_to_compare < now:
            return EMIStatus.OVERDUE

        return emi.status if emi.status != EMIStatus.COMPLETED else EMIStatus.ACTIVE

    def _to_response(self, emi: EMI) -> EMIResponse:
        remaining = max(0, emi.total_installments - emi.paid_installments)
        next_date = self._calculate_next_payment_date(
            emi.start_date, emi.due_day, emi.paid_installments, emi.total_installments
        )
        current_status = self._determine_status(emi, next_date)

        return EMIResponse(
            id=str(emi.id),
            user_id=str(emi.user_id),
            name=emi.name,
            total_amount=emi.total_amount,
            monthly_emi_amount=emi.monthly_emi_amount,
            total_installments=emi.total_installments,
            paid_installments=emi.paid_installments,
            remaining_installments=remaining,
            next_payment_date=next_date,
            start_date=emi.start_date,
            due_day=emi.due_day,
            account_id=str(emi.account_id) if emi.account_id else None,
            credit_card_id=str(emi.credit_card_id) if emi.credit_card_id else None,
            category_id=str(emi.category_id) if emi.category_id else None,
            status=current_status,
            created_at=emi.created_at,
            updated_at=emi.updated_at,
        )

    async def create_emi(self, user: User, data: EMICreate) -> EMIResponse:
        acc_oid = None
        if data.account_id:
            try:
                acc_oid = PydanticObjectId(data.account_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid account ID format.",
                )
            acc = await account_repo.get_by_id_and_user(acc_oid, user.id)
            if not acc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Linked bank account does not exist.",
                )

        card_oid = None
        if data.credit_card_id:
            try:
                card_oid = PydanticObjectId(data.credit_card_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid credit card ID format.",
                )
            card = await credit_card_repo.get_by_id_and_user(card_oid, user.id)
            if not card:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Linked credit card does not exist.",
                )

        cat_oid = None
        if data.category_id:
            try:
                cat_oid = PydanticObjectId(data.category_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid category ID format.",
                )

        initial_status = (
            EMIStatus.COMPLETED
            if data.paid_installments >= data.total_installments
            else EMIStatus.ACTIVE
        )

        emi = EMI(
            user_id=user.id,
            name=data.name,
            total_amount=data.total_amount,
            monthly_emi_amount=data.monthly_emi_amount,
            total_installments=data.total_installments,
            paid_installments=data.paid_installments,
            start_date=data.start_date,
            due_day=data.due_day,
            account_id=acc_oid,
            credit_card_id=card_oid,
            category_id=cat_oid,
            status=initial_status,
        )
        saved = await emi_repo.create(emi)
        return self._to_response(saved)

    async def list_emis(
        self, user: User, status: Optional[EMIStatus] = None
    ) -> List[EMIResponse]:
        emis = await emi_repo.list_by_user(user.id, status)
        return [self._to_response(e) for e in emis]

    async def get_emi(self, emi_id: str, user: User) -> EMIResponse:
        try:
            oid = PydanticObjectId(emi_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid EMI ID format.",
            )

        emi = await emi_repo.get_by_id_and_user(oid, user.id)
        if not emi:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="EMI not found.",
            )
        return self._to_response(emi)

    async def update_emi(
        self, emi_id: str, user: User, data: EMIUpdate
    ) -> EMIResponse:
        try:
            oid = PydanticObjectId(emi_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid EMI ID format.",
            )

        emi = await emi_repo.get_by_id_and_user(oid, user.id)
        if not emi:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="EMI not found.",
            )

        if data.name is not None:
            emi.name = data.name
        if data.total_amount is not None:
            emi.total_amount = data.total_amount
        if data.monthly_emi_amount is not None:
            emi.monthly_emi_amount = data.monthly_emi_amount
        if data.total_installments is not None:
            emi.total_installments = data.total_installments
        if data.paid_installments is not None:
            emi.paid_installments = data.paid_installments
        if data.start_date is not None:
            emi.start_date = data.start_date
        if data.due_day is not None:
            emi.due_day = data.due_day
        if data.status is not None:
            emi.status = data.status

        if emi.paid_installments >= emi.total_installments:
            emi.status = EMIStatus.COMPLETED

        if data.account_id is not None:
            acc_oid = PydanticObjectId(data.account_id)
            emi.account_id = acc_oid
            emi.credit_card_id = None
        if data.credit_card_id is not None:
            card_oid = PydanticObjectId(data.credit_card_id)
            emi.credit_card_id = card_oid
            emi.account_id = None

        emi.updated_at = datetime.now(timezone.utc)
        saved = await emi_repo.save(emi)
        return self._to_response(saved)

    async def delete_emi(self, emi_id: str, user: User) -> None:
        try:
            oid = PydanticObjectId(emi_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid EMI ID format.",
            )

        emi = await emi_repo.get_by_id_and_user(oid, user.id)
        if not emi:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="EMI not found.",
            )
        await emi_repo.delete(emi)

    async def mark_paid(self, emi_id: str, user: User) -> EMIMarkPaidResponse:
        try:
            oid = PydanticObjectId(emi_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid EMI ID format.",
            )

        emi = await emi_repo.get_by_id_and_user(oid, user.id)
        if not emi:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="EMI not found.",
            )

        if emi.paid_installments >= emi.total_installments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All installments for this EMI have already been paid.",
            )

        # Increment paid installments
        emi.paid_installments += 1
        if emi.paid_installments >= emi.total_installments:
            emi.status = EMIStatus.COMPLETED
            message = "Final EMI installment marked as paid. EMI marked as completed!"
        else:
            emi.status = EMIStatus.ACTIVE
            message = f"Installment {emi.paid_installments} of {emi.total_installments} marked as paid successfully."

        emi.updated_at = datetime.now(timezone.utc)
        saved = await emi_repo.save(emi)

        # Apply financial adjustment if linked to an account or card
        if emi.account_id:
            await account_repo.update_balance(
                emi.account_id, user.id, -emi.monthly_emi_amount
            )
        elif emi.credit_card_id:
            await credit_card_repo.update_outstanding(
                emi.credit_card_id, user.id, emi.monthly_emi_amount
            )

        return EMIMarkPaidResponse(
            message=message,
            emi=self._to_response(saved),
        )


emi_service = EMIService()
