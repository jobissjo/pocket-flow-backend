from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator

from app.models.transaction import TransactionType
from app.models.transaction_import import TransactionImportStatus


class ExtractedLineItem(BaseModel):
    name: str = Field(..., description="Line item name or description")
    quantity: Optional[float] = Field(None, description="Item quantity if available")
    unit_price: Optional[float] = Field(None, description="Price per unit if available")
    amount: Optional[float] = Field(None, description="Total amount for this line item")


class ExtractedTransaction(BaseModel):
    transaction_type: Literal["expense", "income", "refund", "transfer", "unknown"] = "expense"
    amount: Optional[float] = Field(None, description="Final total transaction amount")
    currency: Optional[str] = Field("INR", description="Currency code (e.g. INR, USD)")
    merchant_name: Optional[str] = Field(None, description="Name of the merchant, payee, or billing entity")
    account_name: Optional[str] = Field(None, description="Bank, account name or last 4 digits visible")
    category_name: Optional[str] = Field(None, description="Suggested transaction category")
    transaction_date: Optional[str] = Field(None, description="Transaction date in YYYY-MM-DD format")
    transaction_time: Optional[str] = Field(None, description="Transaction time in HH:MM:SS format")
    payment_method: Literal["upi", "card", "cash", "bank_transfer", "wallet", "unknown"] = "unknown"
    reference_id: Optional[str] = Field(None, description="UPI reference ID, UTR, invoice #, or transaction ID")
    description: Optional[str] = Field(None, description="Brief description or purpose of payment")
    subtotal: Optional[float] = Field(None, description="Subtotal before taxes/discounts")
    tax: Optional[float] = Field(None, description="Taxes (GST/VAT) amount")
    discount: Optional[float] = Field(None, description="Discount amount")
    source_type: Literal[
        "receipt",
        "invoice",
        "payment_screenshot",
        "bank_payment",
        "card_payment",
        "atm_receipt",
        "other",
        "unsupported",
    ] = "other"
    items: List[ExtractedLineItem] = Field(default_factory=list, description="Line items if visible")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Overall extraction confidence")
    field_confidences: Dict[str, float] = Field(default_factory=dict, description="Field-level confidence scores")
    unsupported_reason: Optional[str] = Field(None, description="Reason if image is unsupported (e.g. multi-statement, non-financial)")


class EntityMatch(BaseModel):
    extracted_name: Optional[str] = None
    matched_id: Optional[str] = None
    matched_name: Optional[str] = None
    confidence: float = 0.0
    status: Literal["matched", "not_found", "ambiguous", "needs_confirmation"] = "not_found"
    possible_matches: List[Dict[str, Any]] = Field(default_factory=list)


class TransactionItemDraft(BaseModel):
    name: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class TransactionDraft(BaseModel):
    transaction_type: TransactionType = TransactionType.EXPENSE
    title: str = "Imported Transaction"
    amount: Optional[float] = None
    currency: Optional[str] = "INR"
    merchant: Optional[EntityMatch] = None
    account: Optional[EntityMatch] = None
    credit_card: Optional[EntityMatch] = None
    category: Optional[EntityMatch] = None
    transaction_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None
    items: List[TransactionItemDraft] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    is_duplicate: bool = False
    possible_duplicate_id: Optional[str] = None
    possible_duplicate_title: Optional[str] = None


class TransactionImportResponse(BaseModel):
    id: str
    user_id: str
    file_name: str
    status: TransactionImportStatus
    source_type: Optional[str] = None
    draft: Optional[TransactionDraft] = None
    raw_extraction: Optional[Dict[str, Any]] = None
    created_transaction_id: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionImportConfirmRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    amount: float = Field(..., gt=0, description="Amount must be positive")
    type: TransactionType = TransactionType.EXPENSE
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
