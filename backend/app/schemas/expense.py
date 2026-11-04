from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ExpenseBase(BaseModel):
    expense_id: str
    company_id: str
    expense_date: date
    due_date: date
    actual_payment_date: Optional[date] = None
    category: str
    amount: Decimal
    currency: str
    status: str
    linked_invoice_id: Optional[str] = None

class ExpenseResponse(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)

