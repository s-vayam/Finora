import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.customer import Customer
from app.schemas.customer import CustomerResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.get("", response_model=PaginatedResponse[CustomerResponse])
def list_customers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated list of customers."""
    total = db.query(func.count(Customer.customer_id)).scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    customers = (
        db.query(Customer)
        .order_by(Customer.customer_id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=customers,
    )

