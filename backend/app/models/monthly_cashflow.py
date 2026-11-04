from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class MonthlyCashflow(Base):
    __tablename__ = "monthly_cashflow"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    month = Column(String(7), nullable=False, index=True)  # YYYY-MM
    opening_balance = Column(Numeric(15, 2), nullable=False)
    actual_inflows = Column(Numeric(15, 2), nullable=False)
    actual_outflows = Column(Numeric(15, 2), nullable=False)
    net_cash_flow = Column(Numeric(15, 2), nullable=False)
    closing_balance = Column(Numeric(15, 2), nullable=False)
    inflow_transactions = Column(Integer, nullable=False)
    outflow_transactions = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default="INR")

    company = relationship("Company", back_populates="monthly_cashflows")

    __table_args__ = (
        UniqueConstraint("company_id", "month", name="uq_company_month"),
    )

    def __repr__(self) -> str:
        return f"<MonthlyCashflow {self.company_id} {self.month}: Net {self.net_cash_flow} {self.currency}>"

