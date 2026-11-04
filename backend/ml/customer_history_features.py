"""
Customer Historical Feature Engineering Module (Stage 3B).

Computes leakage-safe customer payment behavior metrics for both
offline model training (using chronological bisect on cleared invoices)
and online inference (querying Finora database tables).
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


def compute_offline_customer_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute customer historical behavior features without data leakage.

    For each invoice posted at `posting_date_dt`, uses strictly cleared
    invoices for that customer where `clear_date_dt <= posting_date_dt`,
    explicitly excluding the current invoice itself.

    Returns:
        DataFrame with columns:
            cust_prev_invoice_count, cust_prev_late_rate,
            cust_prev_ontime_rate, cust_prev_avg_delay,
            cust_prev_max_delay, is_cold_start
    """
    df_work = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_work["posting_date_dt"]):
        df_work["posting_date_dt"] = pd.to_datetime(df_work["posting_date_dt"])
    if not pd.api.types.is_datetime64_any_dtype(df_work["clear_date_dt"]):
        df_work["clear_date_dt"] = pd.to_datetime(df_work["clear_date_dt"])

    cust_events = defaultdict(list)
    for doc_id, cust, c_date, is_late, delay in zip(
        df_work["doc_id"],
        df_work["cust_number"],
        df_work["clear_date_dt"],
        df_work["is_late"],
        df_work["payment_delay_days"],
    ):
        cust_events[cust].append((c_date, doc_id, int(is_late), float(delay)))

    # Sort events per customer by clear_date
    cust_data = {}
    for cust, events in cust_events.items():
        events.sort(key=lambda x: x[0])
        dates = [x[0] for x in events]
        doc_to_idx = {x[1]: i for i, x in enumerate(events)}
        delays = [x[3] for x in events]
        lates = [x[2] for x in events]
        n = len(events)
        cum_late = np.zeros(n + 1, dtype=np.int32)
        cum_delay = np.zeros(n + 1, dtype=np.float64)
        for i in range(n):
            cum_late[i + 1] = cum_late[i] + lates[i]
            cum_delay[i + 1] = cum_delay[i] + delays[i]
        cust_data[cust] = (dates, doc_to_idx, delays, lates, cum_late, cum_delay)

    hist_records = []
    for doc_id, cust, p_date in zip(
        df_work["doc_id"], df_work["cust_number"], df_work["posting_date_dt"]
    ):
        if cust not in cust_data:
            hist_records.append({
                "cust_prev_invoice_count": 0,
                "cust_prev_late_rate": 0.0,
                "cust_prev_ontime_rate": 1.0,
                "cust_prev_avg_delay": 0.0,
                "cust_prev_max_delay": 0.0,
                "is_cold_start": 1,
            })
            continue

        dates, doc_to_idx, delays, lates, cum_late, cum_delay = cust_data[cust]
        idx = bisect_right(dates, p_date)
        self_idx = doc_to_idx.get(doc_id, -1)

        # If current invoice cleared before or on its posting_date, exclude it
        if 0 <= self_idx < idx:
            cnt = idx - 1
            late_sum = cum_late[idx] - lates[self_idx]
            delay_sum = cum_delay[idx] - delays[self_idx]
            valid_delays = [delays[k] for k in range(idx) if k != self_idx]
            max_delay = max(valid_delays) if valid_delays else 0.0
        else:
            cnt = idx
            late_sum = cum_late[idx]
            delay_sum = cum_delay[idx]
            max_delay = max(delays[:idx]) if idx > 0 else 0.0

        if cnt == 0:
            hist_records.append({
                "cust_prev_invoice_count": 0,
                "cust_prev_late_rate": 0.0,
                "cust_prev_ontime_rate": 1.0,
                "cust_prev_avg_delay": 0.0,
                "cust_prev_max_delay": 0.0,
                "is_cold_start": 1,
            })
        else:
            late_rate = float(late_sum / cnt)
            hist_records.append({
                "cust_prev_invoice_count": int(cnt),
                "cust_prev_late_rate": late_rate,
                "cust_prev_ontime_rate": float(1.0 - late_rate),
                "cust_prev_avg_delay": float(delay_sum / cnt),
                "cust_prev_max_delay": float(max_delay),
                "is_cold_start": 0,
            })

    return pd.DataFrame(hist_records, index=df.index)


def compute_live_customer_history(
    prior_payments: List[Dict[str, Any]],
    as_of_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Compute customer historical behavior features from live database records.

    Args:
        prior_payments: List of dicts, each with keys:
            'payment_date': date,
            'due_date': date
        as_of_date: Optional cutoff date. Only payments on or before this
            date are included.

    Returns:
        Dict conforming to DEFAULT_CUSTOMER_HISTORY schema.
    """
    valid_events = []
    for item in prior_payments:
        p_date = item["payment_date"]
        d_date = item["due_date"]
        if as_of_date is not None and p_date > as_of_date:
            continue
        delay = (p_date - d_date).days
        is_late = 1 if delay > 0 else 0
        valid_events.append((delay, is_late))

    cnt = len(valid_events)
    if cnt == 0:
        return {
            "cust_prev_invoice_count": 0,
            "cust_prev_late_rate": 0.0,
            "cust_prev_ontime_rate": 1.0,
            "cust_prev_avg_delay": 0.0,
            "cust_prev_max_delay": 0.0,
            "is_cold_start": 1,
        }

    delays = [e[0] for e in valid_events]
    lates = [e[1] for e in valid_events]
    late_sum = sum(lates)
    delay_sum = sum(delays)
    late_rate = late_sum / cnt

    return {
        "cust_prev_invoice_count": cnt,
        "cust_prev_late_rate": float(late_rate),
        "cust_prev_ontime_rate": float(1.0 - late_rate),
        "cust_prev_avg_delay": float(delay_sum / cnt),
        "cust_prev_max_delay": float(max(delays)),
        "is_cold_start": 0,
    }
