from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.schemas import DataResponse, ErrorResponse
from src.users import service
from src.users.dependencies import get_current_user
from src.users.models import User
from src.users.schemas import UserLogin, UserRead, UserUpdate

router = APIRouter()

COOKIE_OPTS = dict(
    httponly=True,
    secure=settings.COOKIE_SECURE,
    samesite="lax",
    path="/",
)


@router.post(
    "/login",
    response_model=DataResponse[UserRead],
    responses={401: {"model": ErrorResponse}},
)
async def login(
    data: UserLogin, response: Response, db: AsyncSession = Depends(get_db)
):
    user, token, ttl = await service.login(db, data)
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=int(ttl.total_seconds()) if data.remember_me else None,
        **COOKIE_OPTS,
    )
    return {"data": user}


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=settings.COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    if session_token:
        await service.logout(db, session_token)
    response.delete_cookie(settings.COOKIE_NAME, **COOKIE_OPTS)


@router.get(
    "/me",
    response_model=DataResponse[UserRead],
    responses={401: {"model": ErrorResponse}},
)
async def me(user: User = Depends(get_current_user)):
    return {"data": user}


@router.patch(
    "/me",
    response_model=DataResponse[UserRead],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    session_token: str | None = Cookie(default=None, alias=settings.COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await service.update_profile(db, user, data, session_token)}
