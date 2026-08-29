from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator
from app.models.transaction import TransactionType


class TransactionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    amount: float = Field(..., gt=0, description="Amount must be positive")
    type: TransactionType
    category_id: str
    account_id: Optional[str] = None
    credit_card_id: Optional[str] = None
    date: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def validate_account_or_card(self):
        if self.account_id and self.credit_card_id:
            raise ValueError("A transaction cannot be associated with both an account and a credit card.")
        if self.type == TransactionType.INCOME and self.credit_card_id:
            raise ValueError("Income transactions cannot be linked to a credit card.")
        if not self.account_id and not self.credit_card_id:
            raise ValueError("A transaction must be associated with either an account or a credit card.")
        return self


class TransactionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    amount: Optional[float] = Field(None, gt=0)
    type: Optional[TransactionType] = None
    category_id: Optional[str] = None
    account_id: Optional[str] = None
    credit_card_id: Optional[str] = None
    date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=500)


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    amount: float
    type: TransactionType
    category_id: str
    category_name: Optional[str] = None
    category_icon: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    credit_card_id: Optional[str] = None
    credit_card_name: Optional[str] = None
    date: datetime
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionFilterParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
    type: Optional[TransactionType] = None
    category_id: Optional[str] = None
    account_id: Optional[str] = None
    credit_card_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_amount: Optional[float] = Field(None, ge=0)
    max_amount: Optional[float] = Field(None, ge=0)
    sort_by: str = Field(default="date", pattern=r"^(date|amount|title|created_at)$")
    sort_order: str = Field(default="desc", pattern=r"^(asc|desc)$")
