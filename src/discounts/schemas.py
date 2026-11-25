import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    computed_field,
    field_validator,
)

from src.config import settings
from src.discounts.constants import (
    DiscountScope,
    DiscountStatus,
    DiscountType,
    compute_status,
)

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]
Amount = Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=2)]


def _to_utc(value: datetime) -> datetime:
    # Tanpa zona waktu dianggap waktu lokal aplikasi (APP_TIMEZONE)
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo(settings.APP_TIMEZONE))
    return value.astimezone(UTC)


UTCInput = Annotated[datetime, AfterValidator(_to_utc)]


class DiscountCreate(BaseModel):
    # Urutan field penting: validator membaca field yang didefinisikan sebelumnya
    name: Name
    discount_scope: DiscountScope
    product_id: uuid.UUID | None = Field(default=None, validate_default=True)
    discount_type: DiscountType
    discount_value: Amount
    min_transaction_amount: Amount | None = None
    starts_at: UTCInput | None = None
    ends_at: UTCInput | None = None
    is_active: bool = True

    @field_validator("product_id")
    @classmethod
    def check_product_id(cls, value, info: ValidationInfo):
        scope = info.data.get("discount_scope")
        if scope == "product" and value is None:
            raise ValueError("product_id is required for product discounts")
        if scope == "transaction" and value is not None:
            raise ValueError("product_id must be empty for transaction discounts")
        return value

    @field_validator("discount_value")
    @classmethod
    def check_value(cls, value: Decimal, info: ValidationInfo):
        if info.data.get("discount_type") == "percentage" and value > 100:
            raise ValueError("Percentage must not exceed 100")
        return value

    @field_validator("min_transaction_amount")
    @classmethod
    def check_min_amount(cls, value, info: ValidationInfo):
        if info.data.get("discount_scope") == "product" and value is not None:
            raise ValueError(
                "min_transaction_amount must be empty for product discounts"
            )
        return value

    @field_validator("ends_at")
    @classmethod
    def check_period(cls, value, info: ValidationInfo):
        starts_at = info.data.get("starts_at")
        if value and starts_at and value < starts_at:
            raise ValueError("ends_at must not be before starts_at")
        return value


class DiscountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # discount_scope dan product_id ditolak

    name: Name | None = None
    discount_type: DiscountType | None = None
    discount_value: Amount | None = None
    min_transaction_amount: Amount | None = None  # null = kosongkan
    starts_at: UTCInput | None = None  # null = tanpa batas awal
    ends_at: UTCInput | None = None  # null = tanpa batas akhir
    is_active: bool | None = None

    @field_validator("name", "discount_type", "discount_value", "is_active")
    @classmethod
    def not_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class DiscountProduct(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    price: Decimal
    unit: str


class DiscountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    discount_scope: DiscountScope
    product: DiscountProduct | None
    discount_type: DiscountType
    discount_value: Decimal
    min_transaction_amount: Decimal | None
    starts_at: datetime | None
    ends_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def status(self) -> DiscountStatus:
        return compute_status(self.is_active, self.starts_at, self.ends_at)
