import math
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas import DataResponse, ErrorResponse, PaginatedResponse
from src.transactions import service
from src.transactions.schemas import (
    PreviewRead,
    PreviewRequest,
    TransactionCreate,
    TransactionRead,
    TransactionSummary,
)
from src.users.dependencies import get_current_user
from src.users.models import User

router = APIRouter()

AUTH = {401: {"model": ErrorResponse}}
CART_ERRORS = {
    400: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


@router.post(
    "/preview",
    response_model=DataResponse[PreviewRead],
    responses={**AUTH, **CART_ERRORS},
)
async def preview_transaction(
    data: PreviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    calculation = await service.preview(db, user, data)
    return {"data": PreviewRead.model_validate(calculation, from_attributes=True)}


@router.post(
    "",
    response_model=DataResponse[TransactionRead],
    status_code=201,
    responses={**AUTH, **CART_ERRORS},
)
async def create_transaction(
    data: TransactionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.create_transaction(db, user, data)}


@router.get(
    "",
    response_model=PaginatedResponse[TransactionSummary],
    responses={**AUTH, 400: {"model": ErrorResponse}},
)
async def list_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, max_length=50, description="Nomor transaksi"),
    date_from: date | None = Query(None, description="YYYY-MM-DD, inklusif"),
    date_to: date | None = Query(None, description="YYYY-MM-DD, inklusif"),
    sort_by: Literal["created_at", "total"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_transactions(
        db,
        user,
        page=page,
        per_page=per_page,
        search=search,
        date_from=date_from,
        date_to=date_to,
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
    "/{transaction_id}",
    response_model=DataResponse[TransactionRead],
    responses={**AUTH, 404: {"model": ErrorResponse}},
)
async def get_transaction(
    transaction_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.get_transaction(db, user, transaction_id)}
