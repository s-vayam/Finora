import datetime
from typing import Set

# Gazetted Indian Financial Market Holidays (RBI / NSE / BSE) for 2025 and 2026
INDIAN_MARKET_HOLIDAYS: Set[datetime.date] = {
    # 2025
    datetime.date(2025, 1, 26),  # Republic Day
    datetime.date(2025, 2, 26),  # Mahashivratri
    datetime.date(2025, 3, 14),  # Holi
    datetime.date(2025, 3, 31),  # Id-Ul-Fitr
    datetime.date(2025, 4, 10),  # Mahavir Jayanti
    datetime.date(2025, 4, 14),  # Dr. Ambedkar Jayanti
    datetime.date(2025, 4, 18),  # Good Friday
    datetime.date(2025, 5, 1),   # Maharashtra Day
    datetime.date(2025, 6, 7),   # Bakri Id
    datetime.date(2025, 8, 15),  # Independence Day
    datetime.date(2025, 8, 27),  # Ganesh Chaturthi
    datetime.date(2025, 10, 2),  # Gandhi Jayanti / Dussehra
    datetime.date(2025, 10, 21), # Diwali Laxmi Pujan
    datetime.date(2025, 10, 22), # Diwali Balipratipada
    datetime.date(2025, 11, 5),  # Guru Nanak Jayanti
    datetime.date(2025, 12, 25), # Christmas
    # 2026
    datetime.date(2026, 1, 26),  # Republic Day
    datetime.date(2026, 2, 17),  # Mahashivratri
    datetime.date(2026, 3, 3),   # Holi
    datetime.date(2026, 3, 20),  # Id-Ul-Fitr
    datetime.date(2026, 3, 31),  # Mahavir Jayanti
    datetime.date(2026, 4, 3),   # Good Friday
    datetime.date(2026, 4, 14),  # Dr. Ambedkar Jayanti
    datetime.date(2026, 5, 1),   # Maharashtra Day
    datetime.date(2026, 5, 27),  # Bakri Id
    datetime.date(2026, 8, 15),  # Independence Day
    datetime.date(2026, 9, 14),  # Ganesh Chaturthi
    datetime.date(2026, 10, 2),  # Gandhi Jayanti
    datetime.date(2026, 10, 20), # Dussehra
    datetime.date(2026, 11, 8),  # Diwali Laxmi Pujan
    datetime.date(2026, 11, 10), # Diwali Balipratipada
    datetime.date(2026, 11, 24), # Guru Nanak Jayanti
    datetime.date(2026, 12, 25), # Christmas
}


def is_trading_day(d: datetime.date) -> bool:
    """Returns True if date is a weekday (Mon-Fri) and not an Indian market holiday."""
    if d.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False
    if d in INDIAN_MARKET_HOLIDAYS:
        return False
    return True


def count_trading_sessions(start_date: datetime.date, end_date: datetime.date) -> int:
    """
    Counts trading sessions strictly between start_date (exclusive) and end_date (inclusive).
    """
    if end_date <= start_date:
        return 0

    cur = start_date + datetime.timedelta(days=1)
    sessions = 0
    while cur <= end_date:
        if is_trading_day(cur):
            sessions += 1
        cur += datetime.timedelta(days=1)
    return sessions


def add_trading_sessions(start_date: datetime.date, sessions: int) -> datetime.date:
    """
    Calculates the calendar date that falls exactly `sessions` trading days after `start_date`.
    """
    if sessions <= 0:
        return start_date

    cur = start_date
    added = 0
    while added < sessions:
        cur += datetime.timedelta(days=1)
        if is_trading_day(cur):
            added += 1
    return cur


def convert_target_date_to_sessions(as_of_date: datetime.date, target_date: datetime.date) -> int:
    """
    Converts a target calendar date to future trading sessions from as_of_date.
    Validates that the horizon is within [1, 30] trading sessions.
    """
    if target_date <= as_of_date:
        raise ValueError(f"Target date {target_date} must be strictly after as-of date {as_of_date}")

    sessions = count_trading_sessions(as_of_date, target_date)
    if sessions < 1:
        raise ValueError(f"No trading sessions between {as_of_date} and {target_date} (e.g. weekend or holiday).")
    if sessions > 30:
        raise ValueError(f"Target date {target_date} corresponds to {sessions} trading sessions, which exceeds the maximum supported horizon of 30 trading sessions.")

    return sessions

