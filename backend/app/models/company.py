from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Company(Base):
    __tablename__ = "companies"

    company_id = Column(String(50), primary_key=True, index=True)
    company_name = Column(String(255), nullable=False)
    base_currency = Column(String(10), nullable=False, default="INR")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())

    customers = relationship("Customer", back_populates="company", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="company", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="company", cascade="all, delete-orphan")
    cash_transactions = relationship("CashTransaction", back_populates="company", cascade="all, delete-orphan")
    monthly_cashflows = relationship("MonthlyCashflow", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Company {self.company_id}: {self.company_name}>"

