import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db
from app.routers import (
    health_router,
    metadata_router,
    customers_router,
    invoices_router,
    expenses_router,
    transactions_router,
    cashflow_router,
    payments_router,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("finora")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events."""
    logger.info("Starting up Finora API...")
    init_db()
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down Finora API...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="REST API backend for Finora — AI Financial Co-Pilot for International Trade (Phase 1).",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized Error Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning("HTTP %d error on %s: %s", exc.status_code, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "path": request.url.path},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
        content={
            "detail": "Request validation failed",
            "errors": exc.errors(),
            "path": request.url.path,
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server error on %s: %s", request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error occurred", "path": request.url.path},
    )

# Include Routers under API_V1_PREFIX
v1_prefix = settings.API_V1_PREFIX  # /api/v1
app.include_router(health_router, prefix=v1_prefix)
app.include_router(metadata_router, prefix=v1_prefix)
app.include_router(customers_router, prefix=v1_prefix)
app.include_router(invoices_router, prefix=v1_prefix)
app.include_router(expenses_router, prefix=v1_prefix)
app.include_router(transactions_router, prefix=v1_prefix)
app.include_router(cashflow_router, prefix=v1_prefix)
app.include_router(payments_router, prefix=v1_prefix)

# Root endpoint redirecting or pointing to docs
@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to Finora API",
        "version": "1.0.0",
        "docs": "/docs",
        "api_v1": settings.API_V1_PREFIX,
    }
