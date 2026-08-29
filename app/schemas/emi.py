from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator
from app.models.emi import EMIStatus


class EMICreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    total_amount: float = Field(..., gt=0)
    monthly_emi_amount: float = Field(..., gt=0)
    total_installments: int = Field(..., ge=1)
    paid_installments: int = Field(default=0, ge=0)
    start_date: datetime = Field(default_factory=datetime.now)
    due_day: int = Field(..., ge=1, le=31)
    account_id: Optional[str] = None
    credit_card_id: Optional[str] = None
    category_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_account_or_card(self):
        if self.account_id and self.credit_card_id:
            raise ValueError("An EMI cannot be linked to both an account and a credit card.")
        if self.paid_installments > self.total_installments:
            raise ValueError("Paid installments cannot exceed total installments.")
        return self


class EMIUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    total_amount: Optional[float] = Field(None, gt=0)
    monthly_emi_amount: Optional[float] = Field(None, gt=0)
    total_installments: Optional[int] = Field(None, ge=1)
    paid_installments: Optional[int] = Field(None, ge=0)
    start_date: Optional[datetime] = None
    due_day: Optional[int] = Field(None, ge=1, le=31)
    account_id: Optional[str] = None
    credit_card_id: Optional[str] = None
    category_id: Optional[str] = None
    status: Optional[EMIStatus] = None


class EMIResponse(BaseModel):
    id: str
    user_id: str
    name: str
    total_amount: float
    monthly_emi_amount: float
    total_installments: int
    paid_installments: int
    remaining_installments: int
    next_payment_date: Optional[datetime] = None
    start_date: datetime
    due_day: int
    account_id: Optional[str] = None
    credit_card_id: Optional[str] = None
    category_id: Optional[str] = None
    status: EMIStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EMIMarkPaidResponse(BaseModel):
    message: str
    emi: EMIResponse
