from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.account import AccountType


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Account display name")
    bank_name: str = Field(..., min_length=1, max_length=100, description="Bank or provider name")
    account_type: AccountType = Field(default=AccountType.SAVINGS)
    account_number: str = Field(..., min_length=4, max_length=50, description="Account number")
    balance: float = Field(default=0.0, description="Initial balance")


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    bank_name: Optional[str] = Field(None, min_length=1, max_length=100)
    account_type: Optional[AccountType] = None
    account_number: Optional[str] = Field(None, min_length=4, max_length=50)
    balance: Optional[float] = None


class AccountResponse(BaseModel):
    id: str
    user_id: str
    name: str
    bank_name: str
    account_type: AccountType
    last_four: str
    balance: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
