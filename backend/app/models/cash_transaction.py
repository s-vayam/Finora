from sqlalchemy import Column, String, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class CashTransaction(Base):
    __tablename__ = "cash_transactions"

    transaction_id = Column(String(50), primary_key=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False, index=True)  # INFLOW / OUTFLOW
    category = Column(String(100), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    linked_invoice_id = Column(String(50), ForeignKey("invoices.invoice_id", ondelete="SET NULL"), nullable=True, index=True)
    counterparty_id = Column(String(50), nullable=True, index=True)
    description = Column(String(500), nullable=False, default="")

    company = relationship("Company", back_populates="cash_transactions")
    linked_invoice = relationship("Invoice", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<CashTransaction {self.transaction_id}: {self.transaction_type} {self.amount} {self.currency}>"
