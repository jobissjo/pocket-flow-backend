from datetime import datetime, timezone
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class CreditCard(Document):
    user_id: Indexed(PydanticObjectId)
    card_name: str
    provider: str
    last_four: str
    credit_limit: float
    outstanding_amount: float = 0.0
    billing_date: int  # Day of the month (1-31)
    payment_due_date: int  # Day of the month (1-31)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    class Settings:
        name = "credit_cards"
        use_state_management = True
