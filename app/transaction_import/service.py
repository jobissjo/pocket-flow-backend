import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, UploadFile, status
from beanie import PydanticObjectId

from app.core.config import settings
from app.models.transaction import TransactionType
from app.models.transaction_import import TransactionImport, TransactionImportStatus
from app.models.user import User
from app.schemas.transaction import TransactionCreate
from app.services.transaction import transaction_service
from app.transaction_import.extractor import get_extractor
from app.transaction_import.matcher import entity_matcher
from app.transaction_import.repository import transaction_import_repo
from app.transaction_import.schemas import (
    ExtractedTransaction,
    TransactionDraft,
    TransactionImportConfirmRequest,
    TransactionImportResponse,
    TransactionItemDraft,
)
from app.transaction_import.validator import transaction_import_validator

logger = logging.getLogger(__name__)


class TransactionImportService:
    """Service to orchestrate image upload, AI extraction, entity matching, drafting, and confirmation."""

    async def _populate_response(self, record: TransactionImport) -> TransactionImportResponse:
        draft = None
        if record.normalized_draft:
            try:
                draft = TransactionDraft.model_validate(record.normalized_draft)
            except Exception as e:
                logger.error(f"Error parsing draft from import record {record.id}: {e}")

        return TransactionImportResponse(
            id=str(record.id),
            user_id=str(record.user_id),
            file_name=record.file_name,
            status=record.status,
            source_type=record.source_type,
            draft=draft,
            raw_extraction=record.raw_extraction,
            created_transaction_id=str(record.created_transaction_id) if record.created_transaction_id else None,
            warnings=record.warnings or [],
            error_message=record.error_message,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def process_image_upload(
        self, user: User, file: UploadFile
    ) -> TransactionImportResponse:
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        content_type = file.content_type or "image/jpeg"

        # 1. Security & file validation
        is_valid, err_msg = transaction_import_validator.validate_image_file(content, content_type)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg or "Invalid file.",
            )

        # 2. Persist image file locally
        user_dir = os.path.join(settings.UPLOAD_DIR, str(user.id))
        os.makedirs(user_dir, exist_ok=True)

        ext = os.path.splitext(file.filename or "")[1] or ".jpg"
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        storage_path = os.path.join(user_dir, unique_filename)

        with open(storage_path, "wb") as f:
            f.write(content)

        # 3. Create initial import record
        import_record = TransactionImport(
            user_id=user.id,
            file_name=file.filename or unique_filename,
            storage_path=storage_path,
            mime_type=content_type,
            file_size=len(content),
            status=TransactionImportStatus.PROCESSING,
        )
        import_record = await transaction_import_repo.create(import_record)

        # 4. Perform AI Vision Extraction
        extractor = get_extractor()
        try:
            extracted: ExtractedTransaction = await extractor.extract(content, content_type)
        except Exception as e:
            logger.error(f"Extractor failed with exception: {e}")
            import_record.status = TransactionImportStatus.FAILED
            import_record.error_message = f"AI extraction failed: {str(e)}"
            await transaction_import_repo.save(import_record)
            return await self._populate_response(import_record)

        if extracted.source_type == "unsupported":
            import_record.status = TransactionImportStatus.FAILED
            import_record.source_type = extracted.source_type
            import_record.error_message = (
                extracted.unsupported_reason
                or "The uploaded image is unsupported (e.g. multi-transaction statement or non-financial photo)."
            )
            import_record.raw_extraction = extracted.model_dump()
            await transaction_import_repo.save(import_record)
            return await self._populate_response(import_record)

        # 5. Entity Matching
        trans_type = (
            TransactionType.INCOME
            if extracted.transaction_type == "income"
            else TransactionType.EXPENSE
        )

        matched_account = None
        matched_card = None

        if extracted.payment_method == "card":
            matched_card = await entity_matcher.match_credit_card(
                user.id, extracted.account_name, extracted.reference_id
            )
            if matched_card.status == "not_found":
                matched_account = await entity_matcher.match_account(
                    user.id, extracted.account_name, extracted.reference_id, extracted.payment_method
                )
        else:
            matched_account = await entity_matcher.match_account(
                user.id, extracted.account_name, extracted.reference_id, extracted.payment_method
            )
            if matched_account.status == "not_found":
                matched_card = await entity_matcher.match_credit_card(
                    user.id, extracted.account_name, extracted.reference_id
                )

        items_str = ", ".join(i.name for i in extracted.items) if extracted.items else None
        matched_category = await entity_matcher.match_category(
            user.id,
            extracted.category_name,
            extracted.merchant_name,
            items_str,
            trans_type=trans_type,
        )

        matched_merchant = await entity_matcher.match_merchant(
            user.id, extracted.merchant_name
        )

        # 6. Parse Date
        tx_datetime = datetime.now(timezone.utc).replace(tzinfo=None)
        if extracted.transaction_date:
            try:
                date_str = extracted.transaction_date
                time_str = extracted.transaction_time or "12:00:00"
                tx_datetime = datetime.fromisoformat(f"{date_str}T{time_str}")
            except Exception:
                try:
                    tx_datetime = datetime.strptime(extracted.transaction_date, "%Y-%m-%d")
                except Exception:
                    pass

        # 7. Validation & Warning Collection
        all_warnings: List[str] = []

        math_warnings = transaction_import_validator.validate_math_and_totals(extracted)
        all_warnings.extend(math_warnings)

        is_duplicate, dup_id, dup_title, dup_warnings = await transaction_import_validator.check_duplicates(
            user.id,
            extracted.amount,
            extracted.reference_id,
            extracted.merchant_name,
            tx_datetime,
        )
        all_warnings.extend(dup_warnings)

        if matched_account and matched_account.status in ["not_found", "ambiguous", "needs_confirmation"]:
            if not matched_card or matched_card.status in ["not_found", "ambiguous", "needs_confirmation"]:
                all_warnings.append("Could not automatically identify account or credit card. Please select one.")

        if matched_category and matched_category.status in ["not_found", "needs_confirmation"]:
            all_warnings.append("Please verify or choose the appropriate category.")

        if extracted.confidence < 0.6:
            all_warnings.append("Low AI extraction confidence. Please carefully review all fields.")

        # 8. Build Draft
        title = extracted.merchant_name or extracted.description or "Imported Receipt"
        if len(title) > 150:
            title = title[:150]

        item_drafts = [
            TransactionItemDraft(
                name=i.name,
                quantity=i.quantity,
                unit_price=i.unit_price,
                amount=i.amount,
            )
            for i in extracted.items
        ]

        notes_parts = []
        if extracted.reference_id:
            notes_parts.append(f"Ref ID: {extracted.reference_id}")
        if extracted.description and extracted.description != title:
            notes_parts.append(extracted.description)
        if extracted.items:
            items_summary = "; ".join(
                f"{item.name} (x{item.quantity or 1}: ₹{item.amount or item.unit_price or 0})"
                for item in extracted.items[:5]
            )
            notes_parts.append(f"Items: {items_summary}")

        notes = " | ".join(notes_parts) if notes_parts else None
        if notes and len(notes) > 500:
            notes = notes[:497] + "..."

        draft = TransactionDraft(
            transaction_type=trans_type,
            title=title,
            amount=extracted.amount,
            currency=extracted.currency or "INR",
            merchant=matched_merchant,
            account=matched_account if (matched_account and matched_account.matched_id) else None,
            credit_card=matched_card if (matched_card and matched_card.matched_id) else None,
            category=matched_category if (matched_category and matched_category.matched_id) else None,
            transaction_date=tx_datetime,
            payment_method=extracted.payment_method,
            reference_id=extracted.reference_id,
            notes=notes,
            items=item_drafts,
            warnings=all_warnings,
            confidence=extracted.confidence,
            is_duplicate=is_duplicate,
            possible_duplicate_id=dup_id,
            possible_duplicate_title=dup_title,
        )

        # 9. Update import record to REVIEW
        import_record.status = TransactionImportStatus.REVIEW
        import_record.source_type = extracted.source_type
        import_record.raw_extraction = extracted.model_dump()
        import_record.normalized_draft = draft.model_dump(mode="json")
        import_record.warnings = all_warnings
        import_record.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        await transaction_import_repo.save(import_record)
        return await self._populate_response(import_record)

    async def get_import(self, user: User, import_id: str) -> TransactionImportResponse:
        try:
            oid = PydanticObjectId(import_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid import ID format.",
            )

        record = await transaction_import_repo.get_by_id_and_user(oid, user.id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction import record not found.",
            )

        return await self._populate_response(record)

    async def list_imports(
        self, user: User, limit: int = 20, skip: int = 0
    ) -> List[TransactionImportResponse]:
        records = await transaction_import_repo.list_by_user(user.id, limit=limit, skip=skip)
        return [await self._populate_response(rec) for rec in records]

    async def confirm_import(
        self,
        user: User,
        import_id: str,
        confirm_data: TransactionImportConfirmRequest,
    ) -> TransactionImportResponse:
        try:
            oid = PydanticObjectId(import_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid import ID format.",
            )

        record = await transaction_import_repo.get_by_id_and_user(oid, user.id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction import record not found.",
            )

        if record.status == TransactionImportStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This import has already been confirmed.",
            )

        # Create financial transaction with confirmed/edited values
        tx_create = TransactionCreate(
            title=confirm_data.title,
            amount=confirm_data.amount,
            type=confirm_data.type,
            category_id=confirm_data.category_id,
            account_id=confirm_data.account_id,
            credit_card_id=confirm_data.credit_card_id,
            date=confirm_data.date,
            notes=confirm_data.notes,
        )

        tx_response = await transaction_service.create_transaction(user, tx_create)

        # Update import record
        record.status = TransactionImportStatus.CONFIRMED
        record.created_transaction_id = PydanticObjectId(tx_response.id)
        record.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await transaction_import_repo.save(record)

        return await self._populate_response(record)

    async def reject_import(self, user: User, import_id: str) -> TransactionImportResponse:
        try:
            oid = PydanticObjectId(import_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid import ID format.",
            )

        record = await transaction_import_repo.get_by_id_and_user(oid, user.id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction import record not found.",
            )

        record.status = TransactionImportStatus.REJECTED
        record.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await transaction_import_repo.save(record)

        return await self._populate_response(record)


transaction_import_service = TransactionImportService()
