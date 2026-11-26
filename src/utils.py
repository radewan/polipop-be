from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from src.config import settings


def utcnow() -> datetime:
    return datetime.now(UTC)


def day_start_utc(day: date) -> datetime:
    """Awal hari di APP_TIMEZONE, dinyatakan dalam UTC."""
    local = datetime.combine(day, time.min, tzinfo=ZoneInfo(settings.APP_TIMEZONE))
    return local.astimezone(UTC)
