import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.types import UTCDateTime
from src.utils import utcnow


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_id_created_at", "user_id", "created_at"),
        CheckConstraint(
            "subtotal >= 0 AND product_discount_total >= 0 "
            "AND transaction_discount_amount >= 0 AND cash_received >= 0",
            name="amounts_non_negative",
        ),
        CheckConstraint("total >= 0", name="total_non_negative"),
        CheckConstraint("change_amount >= 0", name="change_non_negative"),
        CheckConstraint(
            "subtotal - product_discount_total - transaction_discount_amount = total",
            name="total_formula",
        ),
        CheckConstraint("cash_received - total = change_amount", name="change_formula"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    discount_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("discounts.id", ondelete="SET NULL"), default=None
    )
    transaction_number: Mapped[str] = mapped_column(String(50), unique=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    product_discount_total: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    transaction_discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    cash_received: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    change_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    # Snapshot diskon transaksi (NULL jika tidak ada diskon)
    discount_name: Mapped[str | None] = mapped_column(String(150), default=None)
    discount_type: Mapped[str | None] = mapped_column(String(20), default=None)
    discount_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), default=None)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow
    )

    items: Mapped[list["TransactionItem"]] = relationship(
        lazy="raise", order_by="TransactionItem.product_name"
    )

    @property
    def discount(self) -> dict | None:
        if self.discount_name is None:
            return None
        return {
            "id": self.discount_id,
            "name": self.discount_name,
            "discount_type": self.discount_type,
            "discount_value": self.discount_value,
            "amount": self.transaction_discount_amount,
        }


class TransactionItem(Base):
    __tablename__ = "transaction_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("discount_amount >= 0", name="discount_non_negative"),
        CheckConstraint("subtotal >= 0", name="subtotal_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True, default=None
    )
    product_name: Mapped[str] = mapped_column(String(150))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    discount_type: Mapped[str | None] = mapped_column(String(20), default=None)
    discount_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), default=None)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
