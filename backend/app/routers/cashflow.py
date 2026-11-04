from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.monthly_cashflow import MonthlyCashflow
from app.schemas.cashflow import MonthlyCashflowResponse

router = APIRouter(prefix="/cashflow", tags=["Cash Flow"])

@router.get("/history", response_model=List[MonthlyCashflowResponse])
def get_cashflow_history(db: Session = Depends(get_db)):
    """Return historical monthly cash-flow records in chronological order."""
    cashflows = (
        db.query(MonthlyCashflow)
        .order_by(MonthlyCashflow.month.asc())
        .all()
    )
    return cashflows

