import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.categories import service
from src.categories.schemas import CategoryCreate, CategoryRead, CategoryUpdate
from src.database import get_db
from src.schemas import DataResponse, ErrorResponse, PaginatedResponse
from src.users.dependencies import get_current_user
from src.users.models import User

router = APIRouter()

AUTH_ERRORS = {401: {"model": ErrorResponse}}


@router.get("", response_model=PaginatedResponse[CategoryRead], responses=AUTH_ERRORS)
async def list_categories(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_categories(db, user, page, per_page, search)
    return {
        "data": items,
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": math.ceil(total / per_page),
        },
    }


@router.post(
    "",
    response_model=DataResponse[CategoryRead],
    status_code=201,
    responses={**AUTH_ERRORS, 409: {"model": ErrorResponse}},
)
async def create_category(
    data: CategoryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.create_category(db, user, data)}


@router.put(
    "/{category_id}",
    response_model=DataResponse[CategoryRead],
    responses={
        **AUTH_ERRORS,
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.update_category(db, user, category_id, data)}


@router.delete(
    "/{category_id}",
    status_code=204,
    responses={**AUTH_ERRORS, 404: {"model": ErrorResponse}},
)
async def delete_category(
    category_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_category(db, user, category_id)
