from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CreditCardCreate(BaseModel):
    card_name: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(..., min_length=1, max_length=100)
    last_four: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")
    credit_limit: float = Field(..., gt=0)
    outstanding_amount: float = Field(default=0.0, ge=0)
    billing_date: int = Field(..., ge=1, le=31)
    payment_due_date: int = Field(..., ge=1, le=31)


class CreditCardUpdate(BaseModel):
    card_name: Optional[str] = Field(None, min_length=1, max_length=100)
    provider: Optional[str] = Field(None, min_length=1, max_length=100)
    last_four: Optional[str] = Field(None, min_length=4, max_length=4, pattern=r"^\d{4}$")
    credit_limit: Optional[float] = Field(None, gt=0)
    outstanding_amount: Optional[float] = Field(None, ge=0)
    billing_date: Optional[int] = Field(None, ge=1, le=31)
    payment_due_date: Optional[int] = Field(None, ge=1, le=31)


class CreditCardResponse(BaseModel):
    id: str
    user_id: str
    card_name: str
    provider: str
    last_four: str
    credit_limit: float
    outstanding_amount: float
    available_limit: float
    billing_date: int
    payment_due_date: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
