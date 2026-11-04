from datetime import date
import math
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.cash_transaction import CashTransaction
from app.schemas.cashflow import CashTransactionResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/transactions", tags=["Cash Transactions"])

@router.get("", response_model=PaginatedResponse[CashTransactionResponse])
def list_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type (INFLOW or OUTFLOW)"),
    start_date: Optional[date] = Query(None, description="Filter transactions on or after this date"),
    end_date: Optional[date] = Query(None, description="Filter transactions on or before this date"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated cash transactions with type and date range filters."""
    query = db.query(CashTransaction)

    if transaction_type:
        query = query.filter(func.upper(CashTransaction.transaction_type) == transaction_type.strip().upper())
    if start_date:
        query = query.filter(CashTransaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(CashTransaction.transaction_date <= end_date)

    total = query.with_entities(func.count(CashTransaction.transaction_id)).scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    transactions = (
        query.order_by(CashTransaction.transaction_date.desc(), CashTransaction.transaction_id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=transactions,
    )

