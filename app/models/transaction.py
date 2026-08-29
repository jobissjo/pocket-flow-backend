from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Transaction(Document):
    user_id: Indexed(PydanticObjectId)
    title: str
    amount: float
    type: TransactionType
    category_id: Indexed(PydanticObjectId)
    account_id: Optional[Indexed(PydanticObjectId)] = None
    credit_card_id: Optional[Indexed(PydanticObjectId)] = None
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    class Settings:
        name = "transactions"
        use_state_management = True
