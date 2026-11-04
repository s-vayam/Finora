from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict

class CashTransactionBase(BaseModel):
    transaction_id: str
    company_id: str
    transaction_date: date
    transaction_type: str
    category: str
    amount: Decimal
    currency: str
    linked_invoice_id: Optional[str] = None
    counterparty_id: Optional[str] = None
    description: str

class CashTransactionResponse(CashTransactionBase):
    model_config = ConfigDict(from_attributes=True)

class MonthlyCashflowBase(BaseModel):
    id: int
    company_id: str
    month: str
    opening_balance: Decimal
    actual_inflows: Decimal
    actual_outflows: Decimal
    net_cash_flow: Decimal
    closing_balance: Decimal
    inflow_transactions: int
    outflow_transactions: int
    currency: str

class MonthlyCashflowResponse(MonthlyCashflowBase):
    model_config = ConfigDict(from_attributes=True)

