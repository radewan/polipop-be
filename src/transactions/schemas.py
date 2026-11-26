import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

Quantity = Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=2)]
Cash = Annotated[Decimal, Field(ge=0, max_digits=15, decimal_places=2)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CartItem(BaseModel):
    product_id: uuid.UUID
    quantity: Quantity


class PreviewRequest(BaseModel):
    items: list[CartItem] = Field(min_length=1, max_length=100)

    @field_validator("items")
    @classmethod
    def no_duplicate_products(cls, items: list[CartItem]):
        seen: set[uuid.UUID] = set()
        for item in items:
            if item.product_id in seen:
                raise ValueError("Each product may appear only once")
            seen.add(item.product_id)
        return items


class TransactionCreate(PreviewRequest):
    cash_received: Cash


class AppliedDiscount(ORM):
    id: uuid.UUID | None
    name: str
    discount_type: str
    discount_value: Decimal
    amount: Decimal


class PricedItem(ORM):
    product_id: uuid.UUID | None
    product_name: str
    unit_price: Decimal
    quantity: Decimal
    discount_type: str | None
    discount_value: Decimal | None
    discount_amount: Decimal
    subtotal: Decimal


class ItemRead(PricedItem):
    id: uuid.UUID


class PreviewRead(ORM):
    items: list[PricedItem]
    subtotal: Decimal
    product_discount_total: Decimal
    transaction_discount_amount: Decimal
    total: Decimal
    discount: AppliedDiscount | None


class TransactionRead(ORM):
    id: uuid.UUID
    transaction_number: str
    items: list[ItemRead]
    subtotal: Decimal
    product_discount_total: Decimal
    transaction_discount_amount: Decimal
    total: Decimal
    cash_received: Decimal
    change_amount: Decimal
    discount: AppliedDiscount | None
    created_at: datetime


class TransactionSummary(ORM):
    id: uuid.UUID
    transaction_number: str
    subtotal: Decimal
    product_discount_total: Decimal
    transaction_discount_amount: Decimal
    total: Decimal
    cash_received: Decimal
    change_amount: Decimal
    item_count: int = 0
    created_at: datetime
