from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from beanie import PydanticObjectId

from app.models.account import Account
from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.repositories.account import account_repo
from app.repositories.category import category_repo
from app.repositories.credit_card import credit_card_repo
from app.repositories.transaction import transaction_repo
from app.schemas.common import PaginatedResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionFilterParams,
    TransactionResponse,
    TransactionUpdate,
)


class TransactionService:
    async def _populate_response(
        self, tx: Transaction, user: User
    ) -> TransactionResponse:
        category_name = None
        category_icon = None
        account_name = None
        card_name = None

        if tx.category_id:
            category = await category_repo.get_accessible_by_id(tx.category_id, user.id)
            if category:
                category_name = category.name
                category_icon = category.icon

        if tx.account_id:
            account = await account_repo.get_by_id_and_user(tx.account_id, user.id)
            if account:
                account_name = account.name

        if tx.credit_card_id:
            card = await credit_card_repo.get_by_id_and_user(tx.credit_card_id, user.id)
            if card:
                card_name = card.card_name

        return TransactionResponse(
            id=str(tx.id),
            user_id=str(tx.user_id),
            title=tx.title,
            amount=tx.amount,
            type=tx.type,
            category_id=str(tx.category_id),
            category_name=category_name,
            category_icon=category_icon,
            account_id=str(tx.account_id) if tx.account_id else None,
            account_name=account_name,
            credit_card_id=str(tx.credit_card_id) if tx.credit_card_id else None,
            credit_card_name=card_name,
            date=tx.date,
            notes=tx.notes,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
        )

    async def _apply_financial_effect(
        self,
        user_id: PydanticObjectId,
        trans_type: TransactionType,
        amount: float,
        account_id: Optional[PydanticObjectId],
        credit_card_id: Optional[PydanticObjectId],
        reverse: bool = False,
    ) -> None:
        multiplier = -1 if reverse else 1

        if account_id:
            if trans_type == TransactionType.EXPENSE:
                # Expense decreases balance
                await account_repo.update_balance(account_id, user_id, -amount * multiplier)
            elif trans_type == TransactionType.INCOME:
                # Income increases balance
                await account_repo.update_balance(account_id, user_id, amount * multiplier)

        elif credit_card_id:
            if trans_type == TransactionType.EXPENSE:
                # Expense increases outstanding amount
                await credit_card_repo.update_outstanding(credit_card_id, user_id, amount * multiplier)

    async def create_transaction(
        self, user: User, data: TransactionCreate
    ) -> TransactionResponse:
        # Validate Category
        try:
            cat_oid = PydanticObjectId(data.category_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID format.",
            )

        cat = await category_repo.get_accessible_by_id(cat_oid, user.id)
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected category does not exist.",
            )

        # Validate Account if provided
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
                    detail="Selected bank account does not exist.",
                )

        # Validate Credit Card if provided
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
                    detail="Selected credit card does not exist.",
                )

        # Create Transaction
        tx = Transaction(
            user_id=user.id,
            title=data.title,
            amount=data.amount,
            type=data.type,
            category_id=cat_oid,
            account_id=acc_oid,
            credit_card_id=card_oid,
            date=data.date,
            notes=data.notes,
        )
        saved_tx = await transaction_repo.create(tx)

        # Apply financial effect to Account or Credit Card
        await self._apply_financial_effect(
            user_id=user.id,
            trans_type=data.type,
            amount=data.amount,
            account_id=acc_oid,
            credit_card_id=card_oid,
            reverse=False,
        )

        return await self._populate_response(saved_tx, user)

    async def get_transaction(
        self, transaction_id: str, user: User
    ) -> TransactionResponse:
        try:
            oid = PydanticObjectId(transaction_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transaction ID format.",
            )

        tx = await transaction_repo.get_by_id_and_user(oid, user.id)
        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )
        return await self._populate_response(tx, user)

    async def list_transactions(
        self, user: User, params: TransactionFilterParams
    ) -> PaginatedResponse[TransactionResponse]:
        items, total, total_pages = await transaction_repo.list_filtered(user.id, params)
        responses = [await self._populate_response(tx, user) for tx in items]
        return PaginatedResponse(
            items=responses,
            total=total,
            page=params.page,
            limit=params.limit,
            total_pages=total_pages,
        )

    async def update_transaction(
        self, transaction_id: str, user: User, data: TransactionUpdate
    ) -> TransactionResponse:
        try:
            oid = PydanticObjectId(transaction_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transaction ID format.",
            )

        tx = await transaction_repo.get_by_id_and_user(oid, user.id)
        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )

        # Step 1: Revert old financial effect
        await self._apply_financial_effect(
            user_id=user.id,
            trans_type=tx.type,
            amount=tx.amount,
            account_id=tx.account_id,
            credit_card_id=tx.credit_card_id,
            reverse=True,
        )

        # Step 2: Apply field updates & validate references
        if data.title is not None:
            tx.title = data.title
        if data.amount is not None:
            tx.amount = data.amount
        if data.type is not None:
            tx.type = data.type
        if data.date is not None:
            tx.date = data.date
        if data.notes is not None:
            tx.notes = data.notes

        if data.category_id is not None:
            cat_oid = PydanticObjectId(data.category_id)
            cat = await category_repo.get_accessible_by_id(cat_oid, user.id)
            if not cat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected category does not exist.",
                )
            tx.category_id = cat_oid

        if data.account_id is not None:
            acc_oid = PydanticObjectId(data.account_id)
            acc = await account_repo.get_by_id_and_user(acc_oid, user.id)
            if not acc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected bank account does not exist.",
                )
            tx.account_id = acc_oid
            tx.credit_card_id = None

        if data.credit_card_id is not None:
            card_oid = PydanticObjectId(data.credit_card_id)
            card = await credit_card_repo.get_by_id_and_user(card_oid, user.id)
            if not card:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected credit card does not exist.",
                )
            tx.credit_card_id = card_oid
            tx.account_id = None

        tx.updated_at = datetime.now(timezone.utc)
        saved_tx = await transaction_repo.save(tx)

        # Step 3: Apply new financial effect
        await self._apply_financial_effect(
            user_id=user.id,
            trans_type=saved_tx.type,
            amount=saved_tx.amount,
            account_id=saved_tx.account_id,
            credit_card_id=saved_tx.credit_card_id,
            reverse=False,
        )

        return await self._populate_response(saved_tx, user)

    async def delete_transaction(self, transaction_id: str, user: User) -> None:
        try:
            oid = PydanticObjectId(transaction_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transaction ID format.",
            )

        tx = await transaction_repo.get_by_id_and_user(oid, user.id)
        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )

        # Revert financial effect
        await self._apply_financial_effect(
            user_id=user.id,
            trans_type=tx.type,
            amount=tx.amount,
            account_id=tx.account_id,
            credit_card_id=tx.credit_card_id,
            reverse=True,
        )

        await transaction_repo.delete(tx)


transaction_service = TransactionService()
