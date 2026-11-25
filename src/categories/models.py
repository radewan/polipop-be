import uuid
from datetime import datetime

from alembic.environment import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.utils import utcnow
from src.database import Base
from src.types import UTCDateTime
from src.types import UTCDateTime


if TYPE_CHECKING:
    from src.products.models import Product


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), default=None
    )

    products: Mapped[list["Product"]] = relationship(back_populates="category", lazy="raise")
