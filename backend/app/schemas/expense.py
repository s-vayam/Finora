from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class ExpenseBase(BaseModel):
    expense_id: str
    company_id: str
    expense_date: date
    due_date: date
    actual_payment_date: Optional[date] = None
    category: str
    amount: Decimal
    amount_paid: Decimal = Decimal("0.00")
    currency: str
    status: str
    linked_invoice_id: Optional[str] = None

class ExpenseResponse(ExpenseBase):
    outstanding_amount: Optional[Decimal] = None
    payment_status: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ExpensePaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    payment_date: date = Field(..., description="Payment execution date")
    payment_method: str = Field("BANK_TRANSFER", max_length=50, description="Payment method: WIRE, BANK_TRANSFER, ACH, CARD, CHECK")
    reference_number: Optional[str] = Field(None, max_length=100, description="Bank or payment reference number")
    notes: Optional[str] = Field(None, max_length=500, description="Payment notes or description")
    currency: Optional[str] = Field("INR", max_length=10, description="Payment currency matching expense")

class ExpensePaymentResponse(BaseModel):
    payment_id: str
    company_id: str
    expense_id: str
    payment_date: date
    amount: Decimal
    currency: str
    payment_method: str
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    cash_transaction_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ExpenseDetailResponse(ExpenseResponse):
    payments: List[ExpensePaymentResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)
