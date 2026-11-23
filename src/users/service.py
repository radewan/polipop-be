import hashlib
import secrets
import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.exceptions import Unauthorized
from src.users.models import User, UserSession, utcnow
from src.users.schemas import UserLogin
from src.users.security import DUMMY_HASH, verify_password


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_session(db: AsyncSession, user_id: uuid.UUID, ttl: timedelta) -> str:
    token = secrets.token_urlsafe(48)
    db.add(
        UserSession(
            user_id=user_id,
            token_hash=hash_token(token),
            expires_at=utcnow() + ttl,
        )
    )
    await db.commit()
    return token


async def login(db: AsyncSession, data: UserLogin) -> tuple[User, str, timedelta]:
    user = await db.scalar(
        select(User).where(User.username == data.username, User.deleted_at.is_(None))
    )
    hashed = user.hashed_password if user else DUMMY_HASH
    valid = verify_password(data.password, hashed)
    if not user or not valid:
        raise Unauthorized("Invalid username or password")

    ttl = (
        timedelta(days=settings.SESSION_TTL_REMEMBER_DAYS)
        if data.remember_me
        else timedelta(hours=settings.SESSION_TTL_SHORT_HOURS)
    )
    token = await create_session(db, user.id, ttl)
    return user, token, ttl


async def get_active_session(db: AsyncSession, token: str) -> UserSession | None:
    return await db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_token(token),
            UserSession.deleted_at.is_(None),
            UserSession.expires_at > utcnow(),
        )
    )


async def logout(db: AsyncSession, token: str) -> None:
    await db.execute(
        update(UserSession)
        .where(
            UserSession.token_hash == hash_token(token),
            UserSession.deleted_at.is_(None),
        )
        .values(deleted_at=utcnow())
    )
    await db.commit()
