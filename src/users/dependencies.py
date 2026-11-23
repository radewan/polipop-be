from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.exceptions import Unauthorized
from src.users import service
from src.users.models import User


async def get_current_user(
    session_token: str | None = Cookie(default=None, alias=settings.COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not session_token:
        raise Unauthorized("Not authenticated")
    session = await service.get_active_session(db, session_token)
    if not session:
        raise Unauthorized("Session expired or invalid")
    user = await db.get(User, session.user_id)
    if not user or user.deleted_at is not None:
        raise Unauthorized("Not authenticated")
    return user
