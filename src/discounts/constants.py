from datetime import datetime
from typing import Literal

from src.utils import utcnow

DiscountScope = Literal["product", "transaction"]
DiscountType = Literal["percentage", "fixed"]
DiscountStatus = Literal["active", "scheduled", "expired", "inactive"]


def compute_status(
    is_active: bool, starts_at: datetime | None, ends_at: datetime | None
) -> DiscountStatus:
    now = utcnow()
    if not is_active:
        return "inactive"
    if starts_at and starts_at > now:
        return "scheduled"
    if ends_at and ends_at < now:
        return "expired"
    return "active"
