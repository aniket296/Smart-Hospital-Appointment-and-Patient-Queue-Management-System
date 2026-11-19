"""Timezone-aware date and time utilities using HOSPITAL_TIMEZONE."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from flask import current_app


def get_hospital_tz() -> ZoneInfo:
    """Return the configured hospital ZoneInfo (default Asia/Kolkata)."""
    tz_name = "Asia/Kolkata"
    try:
        if current_app:
            tz_name = current_app.config.get("HOSPITAL_TIMEZONE", "Asia/Kolkata")
    except RuntimeError:
        pass
    return ZoneInfo(tz_name)


def now_hospital() -> datetime:
    """Return the current timezone-aware datetime in the hospital timezone."""
    return datetime.now(get_hospital_tz())


def now_hospital_naive() -> datetime:
    """Return the current hospital local datetime as a naive datetime for MySQL storage."""
    return now_hospital().replace(tzinfo=None)


def today_hospital() -> date:
    """Return today's date in the hospital timezone."""
    return now_hospital().date()


def current_time_hospital() -> time:
    """Return current time-of-day (HH:MM:SS) in the hospital timezone."""
    now = now_hospital()
    return time(now.hour, now.minute, now.second)
