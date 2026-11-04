from pydantic import BaseModel, ConfigDict

class CustomerBase(BaseModel):
    customer_id: str
    company_id: str
    customer_name: str
    country: str
    industry: str
    default_payment_terms_days: int

class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

