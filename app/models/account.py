from datetime import datetime, timezone
from enum import Enum
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class AccountType(str, Enum):
    SAVINGS = "savings"
    CURRENT = "current"
    SALARY = "salary"
    CASH = "cash"
    OTHER = "other"


class Account(Document):
    user_id: Indexed(PydanticObjectId)
    name: str
    bank_name: str
    account_type: AccountType = AccountType.SAVINGS
    account_number: str
    last_four: str
    balance: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    class Settings:
        name = "accounts"
        use_state_management = True
