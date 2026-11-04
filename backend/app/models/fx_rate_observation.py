from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Column, String, Date, Numeric, Integer, Boolean, DateTime, func, UniqueConstraint, Index
from app.database import Base


class FxRateObservation(Base):
    __tablename__ = "fx_rate_observations"

    id = Column(String(50), primary_key=True, index=True)
    base_currency = Column(String(10), nullable=False, index=True)
    quote_currency = Column(String(10), nullable=False, default="INR", index=True)
    rate_type = Column(String(30), nullable=False, index=True)  # REFERENCE_DAILY, INDICATIVE_LIVE
    rate_value = Column(Numeric(18, 6), nullable=False)  # Normalized: INR per 1 unit of foreign currency
    original_rate_value = Column(Numeric(18, 6), nullable=False)
    original_unit = Column(Integer, nullable=False, default=1)
    provider = Column(String(50), nullable=False, index=True)  # RBI_FBIL_ARCHIVE, EXCHANGERATE_DEV
    provider_effective_at = Column(DateTime, nullable=True)
    observation_date = Column(Date, nullable=False, index=True)
    fetched_at = Column(DateTime, nullable=False)
    market_session = Column(String(50), nullable=True)
    source = Column(String(255), nullable=True)
    is_stale = Column(Boolean, nullable=False, default=False)
    is_derived = Column(Boolean, nullable=False, default=False)
    data_delay_seconds = Column(Integer, nullable=False, default=0)
    source_notice = Column(String(500), nullable=True)
    observation_key = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_fx_obs_pair_date_type", "base_currency", "quote_currency", "observation_date", "rate_type"),
    )

    def __repr__(self) -> str:
        return f"<FxRateObservation {self.base_currency}/{self.quote_currency} {self.rate_value} on {self.observation_date} ({self.rate_type})>"

