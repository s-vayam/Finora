from datetime import date, datetime
from sqlalchemy import Column, String, Date, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class ExpenseForecastAssumption(Base):
    __tablename__ = "expense_forecast_assumptions"

    assumption_id = Column(String(50), primary_key=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    monthly_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    effective_start_date = Column(Date, nullable=False)
    effective_end_date = Column(Date, nullable=True)
    description = Column(String(500), nullable=True)
    source = Column(String(50), nullable=False, default="MANUAL")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="expense_assumptions")

    def __repr__(self) -> str:
        return f"<ExpenseForecastAssumption {self.assumption_id}: {self.category} {self.monthly_amount} {self.currency}/mo (active={self.is_active})>"

