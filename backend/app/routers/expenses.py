import math
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.expense import Expense
from app.schemas.expense import ExpenseResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/expenses", tags=["Expenses"])

@router.get("", response_model=PaginatedResponse[ExpenseResponse])
def list_expenses(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by expense category"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated expenses with optional category filter."""
    query = db.query(Expense)

    if category:
        query = query.filter(func.upper(Expense.category) == category.strip().upper())

    total = query.with_entities(func.count(Expense.expense_id)).scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    expenses = (
        query.order_by(Expense.expense_date.desc(), Expense.expense_id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=expenses,
    )

