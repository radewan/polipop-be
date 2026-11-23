from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class DataResponse(BaseModel, Generic[T]):
    data: T

class ErrorItem(BaseModel):
    field: str | None = None
    message: str

class ErrorResponse(BaseModel):
    errors: list[ErrorItem] | None = None