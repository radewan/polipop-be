import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.types import UTCDateTime
from src.types import UTCDateTime
from src.utils import utcnow

if TYPE_CHECKING:
    from src.categories.models import Category


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(150))
    barcode: Mapped[str | None] = mapped_column(String(50), default=None)
    image: Mapped[str | None] = mapped_column(String(255), default=None)
    price: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    stock: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    unit: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), default=None
    )

    category: Mapped["Category"] = relationship(back_populates="products", lazy="raise")
