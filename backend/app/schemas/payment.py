from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class PaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Payment amount (must be positive)")
    currency: str = Field(..., min_length=3, max_length=10, description="ISO-style currency code")
    payment_date: date = Field(..., description="Date payment was received")
    payment_method: Optional[str] = Field("BANK_TRANSFER", description="Payment method used")
    reference_number: Optional[str] = Field(None, description="External reference or transaction ID")
    notes: Optional[str] = Field(None, description="Additional notes")

class PaymentResponse(BaseModel):
    payment_id: str
    company_id: str
    invoice_id: str
    payment_date: date
    amount: Decimal
    currency: str
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    cash_transaction_id: str
    idempotency_key: str
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaymentHistoryItem(BaseModel):
    payment_id: str
    payment_date: date
    amount: Decimal
    currency: str
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    source: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class PaymentDetailResponse(BaseModel):
    payment: PaymentResponse
    invoice_id: str
    invoice_amount: Decimal
    invoice_status: str
