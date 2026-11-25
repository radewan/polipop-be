import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.types import UTCDateTime
from src.utils import utcnow

if TYPE_CHECKING:
    from src.products.models import Product


class Discount(Base):
    __tablename__ = "discounts"
    __table_args__ = (
        Index(
            "ix_discounts_user_id_scope_active",
            "user_id",
            "discount_scope",
            "is_active",
        ),
        CheckConstraint(
            "discount_scope IN ('product', 'transaction')", name="scope_valid"
        ),
        CheckConstraint("discount_type IN ('percentage', 'fixed')", name="type_valid"),
        CheckConstraint("discount_value > 0", name="value_positive"),
        CheckConstraint(
            "discount_type <> 'percentage' OR discount_value <= 100",
            name="percentage_max",
        ),
        CheckConstraint(
            "(discount_scope = 'product' AND product_id IS NOT NULL "
            "AND min_transaction_amount IS NULL) "
            "OR (discount_scope = 'transaction' AND product_id IS NULL)",
            name="scope_rules",
        ),
        CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR ends_at >= starts_at",
            name="period_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id"), index=True, default=None
    )
    name: Mapped[str] = mapped_column(String(150))
    discount_scope: Mapped[str] = mapped_column(String(20))
    discount_type: Mapped[str] = mapped_column(String(20))
    discount_value: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    min_transaction_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), default=None
    )
    starts_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)
    ends_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)

    product: Mapped["Product | None"] = relationship(lazy="raise")
