from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=False)
    industry = Column(String(100), nullable=False)
    default_payment_terms_days = Column(Integer, nullable=False, default=30)

    company = relationship("Company", back_populates="customers")
    invoices = relationship("Invoice", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer {self.customer_id}: {self.customer_name}>"

