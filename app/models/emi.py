from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class EMIStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class EMI(Document):
    user_id: Indexed(PydanticObjectId)
    name: str
    total_amount: float
    monthly_emi_amount: float
    total_installments: int
    paid_installments: int = 0
    start_date: datetime
    due_day: int  # Day of the month (1-31)
    account_id: Optional[Indexed(PydanticObjectId)] = None
    credit_card_id: Optional[Indexed(PydanticObjectId)] = None
    category_id: Optional[Indexed(PydanticObjectId)] = None
    status: EMIStatus = EMIStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    class Settings:
        name = "emis"
        use_state_management = True
