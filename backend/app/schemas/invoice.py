from datetime import date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.payment import PaymentResponse

class InvoiceBase(BaseModel):
    invoice_id: str
    company_id: str
    customer_id: str
    invoice_date: date
    due_date: date
    actual_payment_date: Optional[date] = None
    payment_terms_days: int
    invoice_amount: Decimal
    currency: str
    status: str
    historical_invoice_count: Optional[int] = None
    historical_late_rate: Optional[Decimal] = None

class InvoiceResponse(InvoiceBase):
    amount_paid: Decimal = Decimal("0.00")
    outstanding_amount: Decimal = Decimal("0.00")
    payment_status: str = "UNPAID"
    due_status: str = "UPCOMING"

    model_config = ConfigDict(from_attributes=True)

class InvoiceCreate(BaseModel):
    company_id: str = Field(..., description="ID of company issuing invoice")
    customer_id: str = Field(..., description="ID of customer receiving invoice")
    invoice_date: date = Field(..., description="Date invoice is issued")
    due_date: date = Field(..., description="Date invoice is due for payment")
    payment_terms_days: int = Field(30, ge=0, description="Payment terms in days")
    invoice_amount: Decimal = Field(..., gt=0, description="Invoice total amount")
    currency: str = Field("INR", min_length=3, max_length=10, description="Currency code")
    invoice_id: Optional[str] = Field(None, description="Optional custom invoice identifier")

class InvoiceUpdate(BaseModel):
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    payment_terms_days: Optional[int] = Field(None, ge=0)
    invoice_amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=10)
    customer_id: Optional[str] = None

class InvoiceDetailResponse(BaseModel):
    invoice_id: str
    company_id: str
    customer_id: str
    customer_name: Optional[str] = None
    customer_country: Optional[str] = None
    invoice_date: date
    due_date: date
    actual_payment_date: Optional[date] = None
    payment_terms_days: int
    invoice_amount: Decimal
    currency: str
    status: str
    amount_paid: Decimal
    outstanding_amount: Decimal
    latest_payment_date: Optional[date] = None
    payment_status: str
    due_status: str
    payments: List[PaymentResponse] = []

    model_config = ConfigDict(from_attributes=True)
