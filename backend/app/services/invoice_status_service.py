from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional

from app.models.invoice import Invoice

def calculate_invoice_financials(invoice: Invoice, current_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Calculate dynamic financial metrics and statuses for an invoice
    based on its linked payment records.
    """
    today = current_date or date.today()
    payments = getattr(invoice, "payments", []) or []

    # Safe decimal aggregation
    amount_paid = sum((Decimal(str(p.amount)) for p in payments), Decimal("0.00"))
    invoice_amount = Decimal(str(invoice.invoice_amount))

    # Precision tolerance check
    if abs(invoice_amount - amount_paid) < Decimal("0.005"):
        outstanding_amount = Decimal("0.00")
        payment_status = "PAID"
    elif amount_paid > Decimal("0.00"):
        outstanding_amount = max(Decimal("0.00"), invoice_amount - amount_paid)
        payment_status = "PARTIALLY_PAID"
    else:
        outstanding_amount = invoice_amount
        payment_status = "UNPAID"

    # Due status logic
    if payment_status == "PAID":
        due_status = "SETTLED"
    else:
        if invoice.due_date < today:
            due_status = "OVERDUE"
        elif today <= invoice.due_date <= today + timedelta(days=7):
            due_status = "DUE_SOON"
        else:
            due_status = "UPCOMING"

    latest_payment_date = max((p.payment_date for p in payments), default=None) if payments else None

    return {
        "amount_paid": amount_paid,
        "outstanding_amount": outstanding_amount,
        "payment_status": payment_status,
        "due_status": due_status,
        "latest_payment_date": latest_payment_date,
    }
