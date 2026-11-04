from datetime import date, datetime
from sqlalchemy import Column, String, Date, Integer, Numeric, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class CashflowForecastRun(Base):
    __tablename__ = "cashflow_forecast_runs"

    forecast_id = Column(String(50), primary_key=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    as_of_date = Column(Date, nullable=False, index=True)
    horizon_days = Column(Integer, nullable=False)
    base_currency = Column(String(10), nullable=False, default="INR")
    opening_balance = Column(Numeric(15, 2), nullable=False)
    forecast_method_version = Column(String(50), nullable=False, default="v1.0.0")
    payment_model_version = Column(String(50), nullable=False, default="v1.0.0")
    data_freshness_status = Column(String(50), nullable=False)
    forecast_reliability = Column(String(50), nullable=False)
    forecast_type = Column(String(50), nullable=False, default="BASELINE")
    forecast_payload = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    company = relationship("Company", back_populates="forecast_runs")

    def __repr__(self) -> str:
        return f"<CashflowForecastRun {self.forecast_id}: {self.company_id} horizon={self.horizon_days}d ({self.forecast_type})>"

