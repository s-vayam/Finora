from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    total: int = Field(..., description="Total count of items matching criteria")
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    items: List[T] = Field(..., description="List of items for current page")

class HealthResponse(BaseModel):
    status: str = Field(..., example="healthy")
    database: str = Field(..., example="connected")
    api_version: str = Field(..., example="v1")
    environment: str = Field(..., example="development")

class SeedStatusResponse(BaseModel):
    seeded: bool = Field(..., description="Whether seed data has been imported")
    dataset_id: Optional[str] = Field(None, description="Dataset identifier")
    import_timestamp: Optional[str] = Field(None, description="Import timestamp if seeded")
    record_counts: dict = Field(default_factory=dict, description="Counts of records per table")

class DateRange(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class DataSummaryResponse(BaseModel):
    total_customers: int
    total_invoices: int
    total_paid_invoices: int
    total_open_invoices: int
    total_expenses: int
    total_cash_transactions: int
    available_historical_months: int
    dataset_date_range: DateRange

