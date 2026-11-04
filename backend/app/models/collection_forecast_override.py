from datetime import date, datetime
from sqlalchemy import Column, String, Date, Boolean, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import relationship
from app.database import Base


class CollectionForecastOverride(Base):
    __tablename__ = "collection_forecast_overrides"

    override_id = Column(String(50), primary_key=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = Column(String(50), ForeignKey("invoices.invoice_id", ondelete="CASCADE"), nullable=False, index=True)
    expected_collection_date = Column(Date, nullable=False)
    expected_amount = Column(Numeric(15, 2), nullable=True)
    recovery_probability = Column(Numeric(5, 4), nullable=False, default=1.0)
    commitment_source = Column(String(100), nullable=False, default="CUSTOMER_COMMITMENT")
    notes = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="collection_overrides")
    invoice = relationship("Invoice", back_populates="collection_overrides")

    def __repr__(self) -> str:
        return f"<CollectionForecastOverride {self.override_id}: Invoice {self.invoice_id} -> {self.expected_collection_date} (active={self.is_active})>"

