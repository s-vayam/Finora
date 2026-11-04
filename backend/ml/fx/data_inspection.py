import json
from pathlib import Path
from typing import Dict, Any
import numpy as np
import pandas as pd
from sqlalchemy import select
from app.database import SessionLocal
from app.models.fx_rate_observation import FxRateObservation


def inspect_historical_fx_data() -> Dict[str, Any]:
    session = SessionLocal()
    try:
        query = select(
            FxRateObservation.base_currency,
            FxRateObservation.observation_date,
            FxRateObservation.rate_value,
            FxRateObservation.rate_type
        ).where(
            FxRateObservation.rate_type == "REFERENCE_DAILY",
            FxRateObservation.quote_currency == "INR"
        ).order_by(FxRateObservation.observation_date.asc())

        rows = session.execute(query).all()
        df = pd.DataFrame(rows, columns=["currency", "date", "rate", "rate_type"])
        df["rate"] = df["rate"].astype(float)
        df["date"] = pd.to_datetime(df["date"])

        report = {
            "total_observations": len(df),
            "currencies": {}
        }

        for curr in ["USD", "EUR", "GBP"]:
            sub = df[df["currency"] == curr].sort_values("date").reset_index(drop=True)
            if len(sub) == 0:
                continue

            returns = sub["rate"].pct_change().dropna()
            report["currencies"][f"{curr}/INR"] = {
                "count": len(sub),
                "earliest_date": sub["date"].min().strftime("%Y-%m-%d"),
                "latest_date": sub["date"].max().strftime("%Y-%m-%d"),
                "min_rate": float(sub["rate"].min()),
                "max_rate": float(sub["rate"].max()),
                "mean_rate": float(sub["rate"].mean()),
                "median_rate": float(sub["rate"].median()),
                "daily_volatility_pct": float(returns.std() * 100),
                "max_daily_gain_pct": float(returns.max() * 100),
                "max_daily_loss_pct": float(returns.min() * 100)
            }

        out_path = Path(__file__).parent / "metadata" / "fx_dataset_profile.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report
    finally:
        session.close()


if __name__ == "__main__":
    rep = inspect_historical_fx_data()
    print("FX Data Inspection Report:")
    print(json.dumps(rep, indent=2))

