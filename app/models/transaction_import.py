from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class TransactionImportStatus(str, Enum):
    PROCESSING = "processing"
    REVIEW = "review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    FAILED = "failed"


class TransactionImport(Document):
    user_id: Indexed(PydanticObjectId)
    file_name: str
    storage_path: str
    mime_type: str
    file_size: int
    status: TransactionImportStatus = TransactionImportStatus.PROCESSING
    source_type: Optional[str] = None
    raw_extraction: Optional[Dict[str, Any]] = None
    normalized_draft: Optional[Dict[str, Any]] = None
    warnings: List[str] = Field(default_factory=list)
    created_transaction_id: Optional[Indexed(PydanticObjectId)] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    class Settings:
        name = "transaction_imports"
        use_state_management = True
