from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class ExpensePayment(Base):
    __tablename__ = "expense_payments"

    payment_id = Column(String(50), primary_key=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    expense_id = Column(String(50), ForeignKey("expenses.expense_id", ondelete="CASCADE"), nullable=False, index=True)
    payment_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    payment_method = Column(String(50), nullable=False, default="BANK_TRANSFER")
    reference_number = Column(String(100), nullable=True)
    notes = Column(String(500), nullable=True)
    cash_transaction_id = Column(
        String(50),
        ForeignKey("cash_transactions.transaction_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    idempotency_key = Column(String(100), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), server_default=func.now())

    company = relationship("Company")
    expense = relationship("Expense", back_populates="payments")
    cash_transaction = relationship("CashTransaction")

    def __repr__(self) -> str:
        return f"<ExpensePayment {self.payment_id}: {self.amount} {self.currency} for {self.expense_id}>"

