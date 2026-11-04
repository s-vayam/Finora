from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Column, String, Date, Numeric, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.database import Base


class CashBalanceSnapshot(Base):
    __tablename__ = "cash_balance_snapshots"

    snapshot_id = Column(String(50), primary_key=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    as_of_date = Column(Date, nullable=False, index=True)
    balance_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    minimum_cash_threshold = Column(Numeric(15, 2), nullable=True)
    source = Column(String(50), nullable=False, default="MANUAL")
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="cash_balance_snapshots")

    __table_args__ = (
        UniqueConstraint("company_id", "as_of_date", "currency", name="uq_cash_snapshot_company_date_curr"),
    )

    def __repr__(self) -> str:
        return f"<CashBalanceSnapshot {self.snapshot_id}: {self.balance_amount} {self.currency} as of {self.as_of_date}>"

