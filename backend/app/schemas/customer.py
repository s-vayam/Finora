from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class CustomerBase(BaseModel):
    customer_id: str
    company_id: str
    customer_name: str
    country: str
    industry: str
    default_payment_terms_days: int

class CustomerCreate(BaseModel):
    company_id: str = Field(..., description="ID of company customer belongs to")
    customer_name: str = Field(..., min_length=1, description="Customer or organization name")
    country: str = Field(..., min_length=1, description="Customer country")
    industry: str = Field(..., min_length=1, description="Industry sector")
    default_payment_terms_days: int = Field(30, ge=0, description="Default payment terms in days")
    customer_id: Optional[str] = Field(None, description="Optional custom customer ID")

class CustomerUpdate(BaseModel):
    customer_name: Optional[str] = Field(None, min_length=1)
    country: Optional[str] = Field(None, min_length=1)
    industry: Optional[str] = Field(None, min_length=1)
    default_payment_terms_days: Optional[int] = Field(None, ge=0)

class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
