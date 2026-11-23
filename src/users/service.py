import hashlib
import secrets
import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError


from src.config import settings
from src.exceptions import Forbidden, Unauthorized, AppException, Conflict
from src.users.models import User, UserSession, utcnow
from src.users.schemas import UserLogin, UserUpdate
from src.users.security import DUMMY_HASH, verify_password, hash_password


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


async def update_profile(
    db: AsyncSession, user: User, data: UserUpdate, current_token: str
) -> User:
    # 1. Konfirmasi password dulu, sebelum menyentuh data apa pun
    if not verify_password(data.current_password, user.hashed_password):
        raise Forbidden("Current password is incorrect", field="current_password")

    changes = data.model_dump(
        exclude={"current_password", "new_password"},
        exclude_unset=True,
        exclude_none=True,
    )
    if not changes and not data.new_password:
        raise AppException("No fields to update")

    # 2. Cek username
    new_username = changes.get("username")
    if new_username and new_username != user.username:
        taken = await db.scalar(
            select(User.id).where(User.username == new_username, User.id != user.id)
        )
        if taken:
            raise Conflict("Username already taken", field="username")

    # 3. Terapkan perubahan
    for key, value in changes.items():
        setattr(user, key, value)

    if data.new_password:
        if verify_password(data.new_password, user.hashed_password):
            raise AppException(
                "New password must be different from current password",
                field="new_password",
            )
        user.hashed_password = hash_password(data.new_password)
        # Cabut semua sesi lain, sesi yang sedang dipakai tetap hidup
        await db.execute(
            update(UserSession)
            .where(
                UserSession.user_id == user.id,
                UserSession.token_hash != hash_token(current_token),
                UserSession.deleted_at.is_(None),
            )
            .values(deleted_at=utcnow())
        )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise Conflict("Username already taken", field="username")

    await db.refresh(user)
    return user
