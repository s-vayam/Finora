from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict

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
    model_config = ConfigDict(from_attributes=True)

