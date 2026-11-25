import math
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.product_mutations import service
from src.product_mutations.constants import AnyMutationType
from src.product_mutations.schemas import MutationCreate, MutationRead
from src.schemas import DataResponse, ErrorResponse, PaginatedResponse
from src.users.dependencies import get_current_user
from src.users.models import User

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[MutationRead],
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
)
async def list_mutations(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    product_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None, max_length=100, description="Nama produk"),
    mutation_type: AnyMutationType | None = Query(None),
    date_from: date | None = Query(None, description="YYYY-MM-DD, inklusif"),
    date_to: date | None = Query(None, description="YYYY-MM-DD, inklusif"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_mutations(
        db,
        user,
        page=page,
        per_page=per_page,
        product_id=product_id,
        search=search,
        mutation_type=mutation_type,
        date_from=date_from,
        date_to=date_to,
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


@router.post(
    "",
    response_model=DataResponse[MutationRead],
    status_code=201,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def create_mutation(
    data: MutationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.create_mutation(db, user, data)}
