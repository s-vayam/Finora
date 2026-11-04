from app.routers.health import router as health_router
from app.routers.metadata import router as metadata_router
from app.routers.customers import router as customers_router
from app.routers.invoices import router as invoices_router
from app.routers.expenses import router as expenses_router
from app.routers.transactions import router as transactions_router
from app.routers.cashflow import router as cashflow_router

__all__ = [
    "health_router",
    "metadata_router",
    "customers_router",
    "invoices_router",
    "expenses_router",
    "transactions_router",
    "cashflow_router",
]

