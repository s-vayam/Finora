import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fx_rate_observation import FxRateObservation
from app.schemas.fx import (
    FxRateResponse,
    FxForecastRequest,
    FxForecastResponse,
    FxExposureResponse,
    FxQuotaStatus,
)
from app.services.fx_provider_service import FxProviderService
from app.services.fx_forecasting_service import FxForecastingService
from ml.fx.model_registry import FxModelRegistry

router = APIRouter(prefix="/fx", tags=["Foreign Exchange & FX Risk"])

provider_service = FxProviderService()
forecasting_service = FxForecastingService()
registry = FxModelRegistry.get_instance()


@router.get("/pairs", summary="List supported FX currency pairs")
def list_supported_pairs():
    return {
        "base_currency": "INR",
        "supported_pairs": [
            {
                "pair": "USD/INR",
                "base": "USD",
                "quote": "INR",
                "unit": 1,
                "description": "US Dollar to Indian Rupee",
                "models_available": registry.is_model_available("USD"),
                "skill_status": registry.get_skill_status("USD")
            },
            {
                "pair": "EUR/INR",
                "base": "EUR",
                "quote": "INR",
                "unit": 1,
                "description": "Euro to Indian Rupee",
                "models_available": registry.is_model_available("EUR"),
                "skill_status": registry.get_skill_status("EUR")
            },
            {
                "pair": "GBP/INR",
                "base": "GBP",
                "quote": "INR",
                "unit": 1,
                "description": "British Pound to Indian Rupee",
                "models_available": registry.is_model_available("GBP"),
                "skill_status": registry.get_skill_status("GBP")
            },
        ],
        "other_known_currencies": ["JPY", "AED", "IDR"],
        "attribution_notice": "Historical reference rates from Reserve Bank of India (RBI) / FBIL archive (CC0 1.0 Public Domain)."
    }


@router.get("/rates/current", response_model=List[FxRateResponse], summary="Current indicative FX quotes")
def get_current_rates(
    pairs: Optional[List[str]] = Query(default=None, description="e.g. USD/INR,EUR/INR"),
    db: Session = Depends(get_db)
):
    return provider_service.get_current_rates(db, pairs=pairs)


@router.get("/rates/history", summary="Historical reference FX observations")
def get_rate_history(
    pair: str = Query("USD/INR", description="Currency pair e.g. USD/INR"),
    start_date: Optional[datetime.date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[datetime.date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    parts = pair.upper().split("/")
    base_curr = parts[0]
    quote_curr = parts[1] if len(parts) > 1 else "INR"

    conditions = [
        FxRateObservation.base_currency == base_curr,
        FxRateObservation.quote_currency == quote_curr,
        FxRateObservation.rate_type == "REFERENCE_DAILY"
    ]
    if start_date:
        conditions.append(FxRateObservation.observation_date >= start_date)
    if end_date:
        conditions.append(FxRateObservation.observation_date <= end_date)

    total = db.scalar(
        select(func.count(FxRateObservation.id)).where(and_(*conditions))
    ) or 0

    obs = db.scalars(
        select(FxRateObservation)
        .where(and_(*conditions))
        .order_by(FxRateObservation.observation_date.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    items = [
        {
            "id": o.id,
            "currency_pair": f"{o.base_currency}/{o.quote_currency}",
            "observation_date": o.observation_date,
            "rate_value": float(o.rate_value),
            "original_rate_value": float(o.original_rate_value),
            "original_unit": o.original_unit,
            "provider": o.provider,
            "rate_type": o.rate_type,
            "source": o.source,
        }
        for o in obs
    ]

    return {
        "currency_pair": f"{base_curr}/{quote_curr}",
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items
    }


@router.get("/models/status", summary="FX ML models status")
def get_models_status():
    status_data = {}
    for curr in ["USD", "EUR", "GBP"]:
        meta = registry.get_metadata(curr)
        status_data[f"{curr}/INR"] = {
            "model_ready": registry.is_model_available(curr),
            "skill_status": registry.get_skill_status(curr),
            "test_sample_count": meta.get("sample_count_test", 0),
            "regression_model": meta.get("overall_regression", {}),
            "classification_model": meta.get("overall_classification", {})
        }
    return {
        "model_version": "1.0.0",
        "feature_schema_version": "1.0.0",
        "currencies": status_data
    }


@router.get("/models/metrics", summary="FX ML model evaluation metrics by horizon")
def get_models_metrics(
    pair: Optional[str] = Query(None, description="e.g. USD/INR, EUR/INR, GBP/INR")
):
    if pair:
        curr = pair.split("/")[0].upper()
        if not registry.is_model_available(curr):
            raise HTTPException(status_code=404, detail=f"No models trained for {pair}")
        return registry.get_metadata(curr)

    return {
        "USD/INR": registry.get_metadata("USD"),
        "EUR/INR": registry.get_metadata("EUR"),
        "GBP/INR": registry.get_metadata("GBP"),
    }


@router.post("/forecast", response_model=FxForecastResponse, summary="Generate predictive FX forecast")
def generate_fx_forecast(
    req: FxForecastRequest,
    db: Session = Depends(get_db)
):
    return forecasting_service.generate_forecast(db, req)


@router.get("/forecasts/history", response_model=List[FxForecastResponse], summary="List persisted FX forecasts")
def list_forecast_history(
    company_id: str = Query("FINORA_DEMO", description="Company ID"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    return forecasting_service.list_forecast_history(db, company_id=company_id, limit=limit)


@router.get("/forecasts/{forecast_id}", response_model=FxForecastResponse, summary="Get FX forecast by ID")
def get_forecast_by_id(
    forecast_id: str,
    db: Session = Depends(get_db)
):
    fc = forecasting_service.get_forecast_by_id(db, forecast_id)
    if not fc:
        raise HTTPException(status_code=404, detail=f"Forecast with ID '{forecast_id}' not found.")
    return fc


@router.get("/exposure", response_model=FxExposureResponse, summary="Calculate FX exposure and predicted impact")
def get_fx_exposure(
    company_id: str = Query("FINORA_DEMO", description="Company ID"),
    as_of_date: Optional[datetime.date] = Query(None, description="As of date"),
    db: Session = Depends(get_db)
):
    return forecasting_service.calculate_fx_exposure(db, company_id=company_id, as_of_date=as_of_date)
