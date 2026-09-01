from datetime import datetime, timedelta
import logging
from typing import List, Optional, Tuple
from beanie import PydanticObjectId

from app.core.config import settings
from app.models.transaction import Transaction
from app.transaction_import.schemas import ExtractedTransaction

logger = logging.getLogger(__name__)

# Valid image magic signatures
IMAGE_SIGNATURES = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
]


class TransactionImportValidator:
    """Validates files, totals, and checks for duplicates."""

    def validate_image_file(self, content: bytes, content_type: str) -> Tuple[bool, Optional[str]]:
        """Validate file size and magic bytes to ensure safe image uploads."""
        max_bytes = settings.MAX_UPLOAD_IMAGE_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            return False, f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_IMAGE_SIZE_MB}MB."

        if len(content) < 12:
            return False, "Uploaded file is too small or corrupted."

        # Check WEBP signature: RIFF....WEBP
        if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return True, None

        # Check HEIC/HEIF signature: ftyp box
        if len(content) > 12 and content[4:8] == b"ftyp":
            brand = content[8:12]
            if brand in [b"heic", b"heix", b"hevc", b"mif1", b"msf1"]:
                return True, None

        # Check standard signatures
        for sig, _ in IMAGE_SIGNATURES:
            if content.startswith(sig):
                return True, None

        # If content-type is image/* and passes basic check
        if content_type.startswith("image/"):
            return True, None

        return False, "Invalid image format. Supported formats: JPEG, PNG, WEBP, HEIC, GIF."

    def validate_math_and_totals(self, extraction: ExtractedTransaction) -> List[str]:
        """Verify math consistency among subtotal, tax, discount, line items, and final total."""
        warnings: List[str] = []

        if extraction.amount is None or extraction.amount <= 0:
            warnings.append("Transaction total amount could not be reliably determined.")

        # Check subtotal + tax - discount ≈ total
        if extraction.subtotal is not None and extraction.amount is not None:
            subtotal = extraction.subtotal
            tax = extraction.tax or 0.0
            discount = extraction.discount or 0.0
            calculated_total = round(subtotal + tax - discount, 2)

            if abs(calculated_total - extraction.amount) > 1.0:
                warnings.append(
                    f"Receipt totals mismatch: Subtotal ({subtotal}) + Tax ({tax}) - Discount ({discount}) = {calculated_total}, but total is {extraction.amount}."
                )

        # Check line items sum vs subtotal/total
        if extraction.items:
            item_sum = sum(i.amount for i in extraction.items if i.amount is not None)
            if item_sum > 0:
                compare_target = extraction.subtotal if extraction.subtotal is not None else extraction.amount
                if compare_target and abs(item_sum - compare_target) > 2.0:
                    warnings.append(
                        f"Sum of itemized lines ({round(item_sum, 2)}) differs from receipt amount ({compare_target})."
                    )

        return warnings

    async def check_duplicates(
        self,
        user_id: PydanticObjectId,
        amount: Optional[float],
        ref_id: Optional[str],
        merchant: Optional[str],
        tx_date: Optional[datetime],
    ) -> Tuple[bool, Optional[str], Optional[str], List[str]]:
        """Check for possible duplicate transactions in database."""
        warnings: List[str] = []

        if not amount:
            return False, None, None, warnings

        # 1. Exact match by reference ID in notes / title
        if ref_id and len(ref_id) >= 6:
            matching_ref = await Transaction.find_one(
                Transaction.user_id == user_id,
                {"$or": [
                    {"notes": {"$regex": ref_id, "$options": "i"}},
                    {"title": {"$regex": ref_id, "$options": "i"}},
                ]},
            )
            if matching_ref:
                warn = f"Duplicate detected: Reference ID '{ref_id}' matches existing transaction '{matching_ref.title}' (ID: {matching_ref.id})."
                warnings.append(warn)
                return True, str(matching_ref.id), matching_ref.title, warnings

        # 2. Match by user, exact amount and date proximity (+/- 3 days)
        if tx_date:
            start_window = tx_date - timedelta(days=3)
            end_window = tx_date + timedelta(days=3)
            query = {
                "user_id": user_id,
                "amount": amount,
                "date": {"$gte": start_window, "$lte": end_window},
            }
        else:
            query = {
                "user_id": user_id,
                "amount": amount,
            }

        candidates = await Transaction.find(query).limit(5).to_list()
        for cand in candidates:
            # Check if merchant matches title or notes
            if merchant and (merchant.lower() in cand.title.lower() or (cand.notes and merchant.lower() in cand.notes.lower())):
                warn = f"Possible duplicate: Similar transaction '{cand.title}' for amount {amount} found on {cand.date.strftime('%Y-%m-%d')}."
                warnings.append(warn)
                return True, str(cand.id), cand.title, warnings

        if candidates and not merchant:
            cand = candidates[0]
            warn = f"Possible duplicate: Existing transaction '{cand.title}' for the same amount ({amount}) recorded around this date."
            warnings.append(warn)
            return True, str(cand.id), cand.title, warnings

        return False, None, None, warnings


transaction_import_validator = TransactionImportValidator()
