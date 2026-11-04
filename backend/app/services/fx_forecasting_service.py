import datetime
import logging
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, List
import pandas as pd
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.fx_rate_observation import FxRateObservation
from app.models.fx_forecast import FxForecast
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.expense import Expense
from app.schemas.fx import (
    FxForecastRequest,
    FxForecastResponse,
    FxExposureItem,
    FxExposureResponse,
)
from app.services.trading_calendar import (
    convert_target_date_to_sessions,
    add_trading_sessions,
)
from ml.fx.model_registry import FxModelRegistry

logger = logging.getLogger("finora.fx_forecasting")

SUPPORTED_PAIRS = ["USD/INR", "EUR/INR", "GBP/INR"]
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP"]
MAX_REFERENCE_AGE_DAYS = 7


class FxForecastingService:
    def __init__(self):
        self.registry = FxModelRegistry.get_instance()

    def generate_forecast(self, db: Session, req: FxForecastRequest) -> FxForecastResponse:
        # Parse currency pair
        pair = req.currency_pair.strip().upper()
        if pair not in SUPPORTED_PAIRS:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported currency pair '{pair}'. Supported pairs: {SUPPORTED_PAIRS}"
            )
        base_curr, quote_curr = pair.split("/")

        # Check model readiness
        if not self.registry.is_model_available(base_curr):
            raise HTTPException(
                status_code=503,
                detail=f"FX predictive models for {pair} are not initialized or trained."
            )

        # Retrieve historical reference observations
        query = select(
            FxRateObservation.observation_date,
            FxRateObservation.rate_value
        ).where(
            and_(
                FxRateObservation.base_currency == base_curr,
                FxRateObservation.quote_currency == quote_curr,
                FxRateObservation.rate_type == "REFERENCE_DAILY"
            )
        ).order_by(FxRateObservation.observation_date.asc())

        if req.as_of_date:
            query = query.where(FxRateObservation.observation_date <= req.as_of_date)

        rows = db.execute(query).all()
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No historical reference rate observations available for {pair}."
            )

        df_hist = pd.DataFrame(rows, columns=["date", "rate"])
        df_hist["date"] = pd.to_datetime(df_hist["date"])
        df_hist["rate"] = df_hist["rate"].astype(float)

        anchor_date = df_hist.iloc[-1]["date"].date()
        anchor_rate = Decimal(str(round(df_hist.iloc[-1]["rate"], 6)))

        # Freshness check on anchor rate
        now_date = datetime.datetime.now(datetime.timezone.utc).date()
        age_days = (now_date - anchor_date).days
        freshness_warning = None
        if age_days > MAX_REFERENCE_AGE_DAYS:
            freshness_warning = f"Anchor reference rate is {age_days} days old (latest available: {anchor_date})."

        # Determine target date and horizon sessions
        if req.target_date:
            try:
                horizon_sessions = convert_target_date_to_sessions(anchor_date, req.target_date)
                target_date = req.target_date
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))
        elif req.horizon_sessions:
            if req.horizon_sessions < 1 or req.horizon_sessions > 30:
                raise HTTPException(
                    status_code=422,
                    detail=f"horizon_sessions must be between 1 and 30, got {req.horizon_sessions}."
                )
            horizon_sessions = req.horizon_sessions
            target_date = add_trading_sessions(anchor_date, horizon_sessions)
        else:
            # Default to 10 trading sessions (~2 calendar weeks)
            horizon_sessions = 10
            target_date = add_trading_sessions(anchor_date, horizon_sessions)

        # Run ML inference
        pred_dict = self.registry.predict(base_curr, df_hist, horizon_sessions)

        # Fetch separate latest indicative live rate
        latest_live = db.scalars(
            select(FxRateObservation).where(
                and_(
                    FxRateObservation.base_currency == base_curr,
                    FxRateObservation.quote_currency == quote_curr,
                    FxRateObservation.rate_type == "INDICATIVE_LIVE"
                )
            ).order_by(FxRateObservation.fetched_at.desc()).limit(1)
        ).first()

        live_rate = latest_live.rate_value if latest_live else None
        live_ts = latest_live.fetched_at if latest_live else None

        forecast_id = str(uuid.uuid4())
        skill_status = pred_dict["skill_status"]
        is_val = (skill_status == "TRAINED_AND_VALIDATED")

        # Persist forecast run
        forecast_record = FxForecast(
            forecast_id=forecast_id,
            company_id=req.company_id,
            currency_pair=pair,
            anchor_rate=anchor_rate,
            anchor_date=anchor_date,
            target_date=target_date,
            horizon_sessions=horizon_sessions,
            predicted_log_return=pred_dict["predicted_log_return"],
            predicted_rate=pred_dict["predicted_rate"],
            percentage_movement=Decimal(str(pred_dict["percentage_movement"])),
            predicted_direction=pred_dict["predicted_direction"],
            direction_probabilities=pred_dict["direction_probabilities"],
            prediction_range_80=[str(x) for x in pred_dict["prediction_range_80"]],
            prediction_range_95=[str(x) for x in pred_dict["prediction_range_95"]],
            model_version=pred_dict["model_version"],
            skill_status=skill_status,
            is_validated=is_val,
            forecast_metadata={
                "age_days": age_days,
                "feature_schema_version": pred_dict["feature_schema_version"],
                "live_indicative_rate": float(live_rate) if live_rate else None
            }
        )
        db.add(forecast_record)
        db.commit()

        return FxForecastResponse(
            forecast_id=forecast_id,
            company_id=req.company_id,
            currency_pair=pair,
            anchor_rate=anchor_rate,
            anchor_date=anchor_date,
            target_date=target_date,
            horizon_sessions=horizon_sessions,
            predicted_rate=pred_dict["predicted_rate"],
            percentage_movement=Decimal(str(pred_dict["percentage_movement"])),
            predicted_direction=pred_dict["predicted_direction"],
            direction_probabilities=pred_dict["direction_probabilities"],
            prediction_range_80=pred_dict["prediction_range_80"],
            prediction_range_95=pred_dict["prediction_range_95"],
            latest_indicative_rate=live_rate,
            latest_indicative_timestamp=live_ts,
            model_version=pred_dict["model_version"],
            skill_status=skill_status,
            is_validated=is_val,
            freshness_warning=freshness_warning,
            attribution="Forecast generated from Reserve Bank of India / FBIL reference rates archive."
        )

    def get_forecast_by_id(self, db: Session, forecast_id: str) -> Optional[FxForecastResponse]:
        record = db.scalars(
            select(FxForecast).where(FxForecast.forecast_id == forecast_id)
        ).first()
        if not record:
            return None

        # Fetch latest indicative live rate
        base_curr = record.currency_pair.split("/")[0]
        latest_live = db.scalars(
            select(FxRateObservation).where(
                and_(
                    FxRateObservation.base_currency == base_curr,
                    FxRateObservation.rate_type == "INDICATIVE_LIVE"
                )
            ).order_by(FxRateObservation.fetched_at.desc()).limit(1)
        ).first()

        p_80 = [Decimal(str(x)) for x in record.prediction_range_80] if record.prediction_range_80 else None
        p_95 = [Decimal(str(x)) for x in record.prediction_range_95] if record.prediction_range_95 else None

        return FxForecastResponse(
            forecast_id=record.forecast_id,
            company_id=record.company_id,
            currency_pair=record.currency_pair,
            anchor_rate=record.anchor_rate,
            anchor_date=record.anchor_date,
            target_date=record.target_date,
            horizon_sessions=record.horizon_sessions,
            predicted_rate=record.predicted_rate,
            percentage_movement=record.percentage_movement,
            predicted_direction=record.predicted_direction,
            direction_probabilities=record.direction_probabilities,
            prediction_range_80=p_80,
            prediction_range_95=p_95,
            latest_indicative_rate=latest_live.rate_value if latest_live else None,
            latest_indicative_timestamp=latest_live.fetched_at if latest_live else None,
            model_version=record.model_version,
            skill_status=record.skill_status,
            is_validated=record.is_validated,
            freshness_warning=None,
            attribution="Forecast generated from Reserve Bank of India / FBIL reference rates archive."
        )

    def list_forecast_history(self, db: Session, company_id: str, limit: int = 50) -> List[FxForecastResponse]:
        records = db.scalars(
            select(FxForecast)
            .where(FxForecast.company_id == company_id)
            .order_by(FxForecast.created_at.desc())
            .limit(limit)
        ).all()

        results = []
        for r in records:
            p_80 = [Decimal(str(x)) for x in r.prediction_range_80] if r.prediction_range_80 else None
            p_95 = [Decimal(str(x)) for x in r.prediction_range_95] if r.prediction_range_95 else None
            results.append(
                FxForecastResponse(
                    forecast_id=r.forecast_id,
                    company_id=r.company_id,
                    currency_pair=r.currency_pair,
                    anchor_rate=r.anchor_rate,
                    anchor_date=r.anchor_date,
                    target_date=r.target_date,
                    horizon_sessions=r.horizon_sessions,
                    predicted_rate=r.predicted_rate,
                    percentage_movement=r.percentage_movement,
                    predicted_direction=r.predicted_direction,
                    direction_probabilities=r.direction_probabilities,
                    prediction_range_80=p_80,
                    prediction_range_95=p_95,
                    latest_indicative_rate=None,
                    latest_indicative_timestamp=None,
                    model_version=r.model_version,
                    skill_status=r.skill_status,
                    is_validated=r.is_validated,
                    attribution="Forecast generated from Reserve Bank of India / FBIL reference rates archive."
                )
            )
        return results

    def calculate_fx_exposure(
        self,
        db: Session,
        company_id: str,
        as_of_date: Optional[datetime.date] = None
    ) -> FxExposureResponse:
        calc_date = as_of_date or datetime.datetime.now(datetime.timezone.utc).date()

        # 1. Outstanding Receivables from Invoices
        # Exclude PAID and CANCELLED
        invoices = db.scalars(
            select(Invoice).where(
                and_(
                    Invoice.company_id == company_id,
                    Invoice.status.notin_(["PAID", "CANCELLED"]),
                    Invoice.currency != "INR"
                )
            )
        ).all()

        receivables_by_curr: Dict[str, Decimal] = {}
        for inv in invoices:
            # Calculate outstanding balance: invoice_amount - sum(payments)
            paid_sum = db.scalar(
                select(func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
                .where(Payment.invoice_id == inv.invoice_id)
            ) or Decimal("0.00")
            outstanding = max(Decimal("0.00"), inv.invoice_amount - paid_sum)
            if outstanding > Decimal("0.00"):
                c = inv.currency.upper()
                receivables_by_curr[c] = receivables_by_curr.get(c, Decimal("0.00")) + outstanding

        # 2. Outstanding Payables from Expenses
        # Exclude PAID
        expenses = db.scalars(
            select(Expense).where(
                and_(
                    Expense.company_id == company_id,
                    Expense.status != "PAID",
                    Expense.currency != "INR"
                )
            )
        ).all()

        payables_by_curr: Dict[str, Decimal] = {}
        for exp in expenses:
            c = exp.currency.upper()
            payables_by_curr[c] = payables_by_curr.get(c, Decimal("0.00")) + exp.amount

        # All foreign currencies present
        all_foreign_currencies = set(receivables_by_curr.keys()).union(set(payables_by_curr.keys()))

        supported_items: List[FxExposureItem] = []
        unsupported_items: List[FxExposureItem] = []
        total_net_impact = Decimal("0.00")

        for curr in sorted(all_foreign_currencies):
            rec_amt = receivables_by_curr.get(curr, Decimal("0.00"))
            pay_amt = payables_by_curr.get(curr, Decimal("0.00"))
            net_exp = rec_amt - pay_amt

            if curr in SUPPORTED_CURRENCIES:
                # Retrieve latest reference benchmark rate
                bench_obs = db.scalars(
                    select(FxRateObservation).where(
                        and_(
                            FxRateObservation.base_currency == curr,
                            FxRateObservation.quote_currency == "INR",
                            FxRateObservation.rate_type == "REFERENCE_DAILY"
                        )
                    ).order_by(FxRateObservation.observation_date.desc()).limit(1)
                ).first()

                benchmark_rate = bench_obs.rate_value if bench_obs else Decimal("85.00")

                # Run standard 10-session forecast for predicted rate
                predicted_rate = benchmark_rate
                try:
                    f_req = FxForecastRequest(
                        company_id=company_id,
                        currency_pair=f"{curr}/INR",
                        horizon_sessions=10
                    )
                    f_res = self.generate_forecast(db, f_req)
                    predicted_rate = f_res.predicted_rate
                except Exception as e:
                    logger.warning(f"Could not generate forecast for exposure calculation ({curr}): {e}")

                rate_delta = predicted_rate - benchmark_rate
                # Exporter receivables benefit when rate rises: rec_amt * delta
                rec_impact = round(rec_amt * rate_delta, 2)
                # Importer payables suffer when rate rises: -pay_amt * delta
                pay_impact = round(-pay_amt * rate_delta, 2)
                net_impact = rec_impact + pay_impact
                total_net_impact += net_impact

                supported_items.append(
                    FxExposureItem(
                        currency=curr,
                        receivable_amount=round(rec_amt, 2),
                        payable_amount=round(pay_amt, 2),
                        net_exposure=round(net_exp, 2),
                        benchmark_rate=round(benchmark_rate, 4),
                        predicted_rate=round(predicted_rate, 4),
                        estimated_receivable_impact=rec_impact,
                        estimated_payable_impact=pay_impact,
                        net_estimated_impact=net_impact,
                        status="ESTIMATED_UNREALIZED"
                    )
                )
            else:
                unsupported_items.append(
                    FxExposureItem(
                        currency=curr,
                        receivable_amount=round(rec_amt, 2),
                        payable_amount=round(pay_amt, 2),
                        net_exposure=round(net_exp, 2),
                        benchmark_rate=Decimal("0.00"),
                        predicted_rate=None,
                        estimated_receivable_impact=Decimal("0.00"),
                        estimated_payable_impact=Decimal("0.00"),
                        net_estimated_impact=Decimal("0.00"),
                        status="UNSUPPORTED_CURRENCY"
                    )
                )

        return FxExposureResponse(
            company_id=company_id,
            as_of_date=calc_date,
            base_currency="INR",
            supported_exposures=supported_items,
            unsupported_exposures=unsupported_items,
            total_net_estimated_impact=round(total_net_impact, 2)
        )

