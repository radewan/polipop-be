import math
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.discounts import service
from src.discounts.constants import DiscountScope, DiscountStatus, DiscountType
from src.discounts.schemas import DiscountCreate, DiscountRead, DiscountUpdate
from src.schemas import DataResponse, ErrorResponse, PaginatedResponse
from src.users.dependencies import get_current_user
from src.users.models import User

router = APIRouter()

AUTH = {401: {"model": ErrorResponse}}
NOT_FOUND = {404: {"model": ErrorResponse}}
WRITE_ERRORS = {
    400: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


@router.get("", response_model=PaginatedResponse[DiscountRead], responses=AUTH)
async def list_discounts(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str | None = Query(
        None, max_length=100, description="Nama diskon atau nama produk"
    ),
    scope: DiscountScope | None = Query(None),
    discount_type: DiscountType | None = Query(None, alias="type"),
    status: DiscountStatus | None = Query(None),
    product_id: uuid.UUID | None = Query(None),
    sort_by: Literal[
        "created_at", "name", "discount_value", "starts_at", "ends_at"
    ] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_discounts(
        db,
        user,
        page=page,
        per_page=per_page,
        search=search,
        scope=scope,
        discount_type=discount_type,
        status=status,
        product_id=product_id,
        sort_by=sort_by,
        order=order,
    )
    return {
        "data": items,
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": math.ceil(total / per_page),
        },
    }


@router.get(
    "/{discount_id}",
    response_model=DataResponse[DiscountRead],
    responses={**AUTH, **NOT_FOUND},
)
async def get_discount(
    discount_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.get_discount(db, user, discount_id)}


@router.post(
    "",
    response_model=DataResponse[DiscountRead],
    status_code=201,
    responses={**AUTH, **WRITE_ERRORS},
)
async def create_discount(
    data: DiscountCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.create_discount(db, user, data)}


@router.patch(
    "/{discount_id}",
    response_model=DataResponse[DiscountRead],
    responses={**AUTH, **NOT_FOUND, **WRITE_ERRORS},
)
async def update_discount(
    discount_id: uuid.UUID,
    data: DiscountUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.update_discount(db, user, discount_id, data)}


@router.delete("/{discount_id}", status_code=204, responses={**AUTH, **NOT_FOUND})
async def delete_discount(
    discount_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_discount(db, user, discount_id)
