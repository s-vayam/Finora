from sqlalchemy import Column, String, Integer, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id = Column(String(50), primary_key=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="RESTRICT"), nullable=False, index=True)
    invoice_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=False, index=True)
    actual_payment_date = Column(Date, nullable=True)
    payment_terms_days = Column(Integer, nullable=False)
    invoice_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="INR", index=True)
    status = Column(String(50), nullable=False, index=True)
    historical_invoice_count = Column(Integer, nullable=True)
    historical_late_rate = Column(Numeric(6, 4), nullable=True)

    company = relationship("Company", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")
    expenses = relationship("Expense", back_populates="linked_invoice")
    transactions = relationship("CashTransaction", back_populates="linked_invoice")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan", order_by="Payment.payment_date.asc()")
    predictions = relationship("MLPrediction", back_populates="invoice", cascade="all, delete-orphan", order_by="MLPrediction.prediction_timestamp.desc()")

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_id}: {self.invoice_amount} {self.currency} ({self.status})>"

