import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    field_validator,
)

from src.storage import image_url

ProductName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]
Unit = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
]
Barcode = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]
Amount = Annotated[Decimal, Field(ge=0, max_digits=15, decimal_places=2)]


def _blank_to_none(value):
    # "" atau "   " pada barcode/image dianggap null
    if isinstance(value, str) and not value.strip():
        return None
    return value


class ProductCreate(BaseModel):
    category_id: uuid.UUID
    name: ProductName
    barcode: Barcode | None = None
    price: Amount
    stock: Amount = Decimal("0")
    unit: Unit

    _blank = field_validator("barcode", mode="before")(_blank_to_none)


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # stock (dan field asing) ditolak

    category_id: uuid.UUID | None = None
    name: ProductName | None = None
    barcode: Barcode | None = None
    price: Amount | None = None
    unit: Unit | None = None

    _blank = field_validator("barcode", mode="before")(_blank_to_none)

    @field_validator("category_id", "name", "price", "unit")
    @classmethod
    def not_null(cls, value):
        # Field wajib boleh tidak dikirim, tapi tidak boleh dikirim sebagai null
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class CategoryBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: CategoryBrief
    name: str
    barcode: str | None
    image: str | None
    price: Decimal
    stock: Decimal
    unit: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("image")
    def serialize_image(self, value: str | None) -> str | None:
        return image_url(value)
