import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.utils import utcnow

if TYPE_CHECKING:
    from src.products.models import Product


class ProductMutation(Base):
    __tablename__ = "product_mutations"
    __table_args__ = (
        Index("ix_product_mutations_product_id_created_at", "product_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    mutation_type: Mapped[str] = mapped_column(String(30))
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    stock_before: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    stock_after: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    product: Mapped["Product"] = relationship(lazy="raise")
