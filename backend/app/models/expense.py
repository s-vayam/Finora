from sqlalchemy import Column, String, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Expense(Base):
    __tablename__ = "expenses"

    expense_id = Column(String(50), primary_key=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    expense_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=False, index=True)
    actual_payment_date = Column(Date, nullable=True)
    category = Column(String(100), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(String(50), nullable=False, index=True)
    linked_invoice_id = Column(String(50), ForeignKey("invoices.invoice_id", ondelete="SET NULL"), nullable=True, index=True)

    company = relationship("Company", back_populates="expenses")
    linked_invoice = relationship("Invoice", back_populates="expenses")

    def __repr__(self) -> str:
        return f"<Expense {self.expense_id}: {self.category} {self.amount} {self.currency}>"

