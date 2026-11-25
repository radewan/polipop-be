import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from src.product_mutations.constants import (
    DECREASE_TYPES,
    INCREASE_TYPES,
    ManualMutationType,
)

Amount = Annotated[Decimal, Field(max_digits=15, decimal_places=2)]
Notes = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


class MutationCreate(BaseModel):
    product_id: uuid.UUID
    mutation_type: ManualMutationType
    quantity: Amount  # harus didefinisikan SETELAH mutation_type (dipakai validator)
    notes: Notes | None = None
    reference_id: uuid.UUID | None = None

    @field_validator("notes", mode="before")
    @classmethod
    def blank_notes_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("quantity")
    @classmethod
    def check_quantity(cls, value: Decimal, info: ValidationInfo):
        if value == 0:
            raise ValueError("Quantity must not be zero")
        mutation_type = info.data.get("mutation_type")
        if mutation_type in INCREASE_TYPES and value < 0:
            raise ValueError(f"Quantity must be positive for '{mutation_type}'")
        if mutation_type in DECREASE_TYPES and value > 0:
            raise ValueError(f"Quantity must be negative for '{mutation_type}'")
        return value


class MutationProduct(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    unit: str


class MutationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product: MutationProduct
    mutation_type: str
    quantity: Decimal
    stock_before: Decimal
    stock_after: Decimal
    notes: str | None
    reference_id: uuid.UUID | None
    created_at: datetime
