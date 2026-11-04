from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Date, Numeric, Integer, Boolean, Float, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class FxForecast(Base):
    __tablename__ = "fx_forecasts"

    forecast_id = Column(String(50), primary_key=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    currency_pair = Column(String(10), nullable=False, index=True)
    anchor_rate = Column(Numeric(18, 6), nullable=False)
    anchor_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=False, index=True)
    horizon_sessions = Column(Integer, nullable=False)
    predicted_log_return = Column(Float, nullable=False)
    predicted_rate = Column(Numeric(18, 6), nullable=False)
    percentage_movement = Column(Numeric(8, 4), nullable=False)
    predicted_direction = Column(String(10), nullable=False)  # UP, DOWN, NEUTRAL
    direction_probabilities = Column(JSON, nullable=False)
    prediction_range_80 = Column(JSON, nullable=True)
    prediction_range_95 = Column(JSON, nullable=True)
    model_version = Column(String(20), nullable=False)
    skill_status = Column(String(30), nullable=False)  # TRAINED_AND_VALIDATED, NO_SKILL_VS_BASELINE
    is_validated = Column(Boolean, nullable=False, default=True)
    forecast_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    company = relationship("Company")

    def __repr__(self) -> str:
        return f"<FxForecast {self.forecast_id}: {self.currency_pair} {self.predicted_rate} for {self.target_date}>"

