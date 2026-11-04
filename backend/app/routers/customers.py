import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.customer import Customer
from app.models.company import Company
from app.schemas.customer import CustomerResponse, CustomerCreate, CustomerUpdate
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/customers", tags=["Customers"])
UNPROCESSABLE_STATUS = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

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

@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """Retrieve a single customer by ID."""
    customer = db.query(Customer).filter(Customer.customer_id == customer_id.strip()).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer '{customer_id}' not found",
        )
    return customer

@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer master record."""
    # 1. Verify company exists
    company = db.query(Company).filter(Company.company_id == payload.company_id.strip()).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{payload.company_id}' not found",
        )

    # 2. Check customer_name not empty
    name = payload.customer_name.strip()
    if not name:
        raise HTTPException(
            status_code=UNPROCESSABLE_STATUS,
            detail="Customer name cannot be empty",
        )

    # 3. Generate customer_id if not supplied
    if payload.customer_id and payload.customer_id.strip():
        cid = payload.customer_id.strip()
        existing = db.query(Customer).filter(Customer.customer_id == cid).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Customer ID '{cid}' already exists",
            )
    else:
        # Generate clean ID
        count = db.query(func.count(Customer.customer_id)).scalar() or 0
        cid = f"CUST{count + 1:03d}"
        if db.query(Customer).filter(Customer.customer_id == cid).first():
            cid = f"CUST-{uuid.uuid4().hex[:8].upper()}"

    customer = Customer(
        customer_id=cid,
        company_id=payload.company_id.strip(),
        customer_name=name,
        country=payload.country.strip(),
        industry=payload.industry.strip(),
        default_payment_terms_days=payload.default_payment_terms_days,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: str, payload: CustomerUpdate, db: Session = Depends(get_db)):
    """Update customer details."""
    customer = db.query(Customer).filter(Customer.customer_id == customer_id.strip()).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer '{customer_id}' not found",
        )

    if payload.customer_name is not None:
        name = payload.customer_name.strip()
        if not name:
            raise HTTPException(
                status_code=UNPROCESSABLE_STATUS,
                detail="Customer name cannot be empty",
            )
        customer.customer_name = name

    if payload.country is not None:
        customer.country = payload.country.strip()

    if payload.industry is not None:
        customer.industry = payload.industry.strip()

    if payload.default_payment_terms_days is not None:
        customer.default_payment_terms_days = payload.default_payment_terms_days

    db.commit()
    db.refresh(customer)
    return customer
