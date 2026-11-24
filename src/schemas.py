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

class PageMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: PageMeta