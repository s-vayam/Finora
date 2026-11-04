from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class FxScenarioRun(Base):
    __tablename__ = "fx_scenario_runs"

    scenario_id = Column(String(50), primary_key=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    currency_pair = Column(String(10), nullable=False, index=True)
    benchmark_rate = Column(Numeric(18, 6), nullable=False)
    scenario_rate = Column(Numeric(18, 6), nullable=False)
    percentage_change = Column(Numeric(8, 4), nullable=False)
    receivable_exposure = Column(Numeric(15, 2), nullable=False)
    payable_exposure = Column(Numeric(15, 2), nullable=False)
    estimated_receivable_impact = Column(Numeric(15, 2), nullable=False)
    estimated_payable_impact = Column(Numeric(15, 2), nullable=False)
    net_estimated_impact = Column(Numeric(15, 2), nullable=False)
    source = Column(String(50), nullable=False, default="SIMULATED")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    company = relationship("Company")

    def __repr__(self) -> str:
        return f"<FxScenarioRun {self.scenario_id}: {self.currency_pair} change={self.percentage_change}% impact={self.net_estimated_impact}>"

