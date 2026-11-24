import math
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.products import service
from src.products.schemas import ProductCreate, ProductRead, ProductUpdate
from src.schemas import DataResponse, ErrorResponse, PaginatedResponse
from src.users.dependencies import get_current_user
from src.users.models import User

router = APIRouter()

AUTH = {401: {"model": ErrorResponse}}
NOT_FOUND = {404: {"model": ErrorResponse}}
CONFLICT = {409: {"model": ErrorResponse}}

IMAGE_ERRORS = {
    **AUTH,
    **NOT_FOUND,
    413: {"model": ErrorResponse},
    415: {"model": ErrorResponse},
}


@router.get("", response_model=PaginatedResponse[ProductRead], responses=AUTH)
async def list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str | None = Query(
        None, max_length=100, description="Nama produk, kategori, atau barcode"
    ),
    category_id: uuid.UUID | None = Query(None),
    sort_by: Literal["name", "price", "stock", "created_at"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_products(
        db,
        user,
        page=page,
        per_page=per_page,
        search=search,
        category_id=category_id,
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
    "/{product_id}",
    response_model=DataResponse[ProductRead],
    responses={**AUTH, **NOT_FOUND},
)
async def get_product(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.get_product(db, user, product_id)}


@router.post(
    "",
    response_model=DataResponse[ProductRead],
    status_code=201,
    responses={**AUTH, **CONFLICT, 400: {"model": ErrorResponse}},
)
async def create_product(
    data: ProductCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.create_product(db, user, data)}


@router.patch(
    "/{product_id}",
    response_model=DataResponse[ProductRead],
    responses={**AUTH, **NOT_FOUND, **CONFLICT, 400: {"model": ErrorResponse}},
)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.update_product(db, user, product_id, data)}


@router.delete("/{product_id}", status_code=204, responses={**AUTH, **NOT_FOUND})
async def delete_product(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_product(db, user, product_id)


@router.put(
    "/{product_id}/image",
    response_model=DataResponse[ProductRead],
    responses=IMAGE_ERRORS,
)
async def upload_product_image(
    product_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.set_image(db, user, product_id, file)}


@router.delete("/{product_id}/image", status_code=204, responses={**AUTH, **NOT_FOUND})
async def delete_product_image(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.remove_image(db, user, product_id)
