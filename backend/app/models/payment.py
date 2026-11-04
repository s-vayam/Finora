from datetime import datetime
from sqlalchemy import Column, String, Numeric, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String(50), primary_key=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = Column(String(50), ForeignKey("invoices.invoice_id", ondelete="CASCADE"), nullable=False, index=True)
    payment_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), nullable=False)
    payment_method = Column(String(50), nullable=True)
    reference_number = Column(String(100), nullable=True)
    notes = Column(String(500), nullable=True)
    cash_transaction_id = Column(
        String(50),
        ForeignKey("cash_transactions.transaction_id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    idempotency_key = Column(String(100), nullable=False, unique=True, index=True)
    source = Column(String(20), nullable=False, default="MANUAL")  # MANUAL or SEED_BACKFILL
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())

    company = relationship("Company", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payments")
    cash_transaction = relationship("CashTransaction", back_populates="payment")

    def __repr__(self) -> str:
        return f"<Payment {self.payment_id}: {self.amount} {self.currency} for {self.invoice_id}>"
