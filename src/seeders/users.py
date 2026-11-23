from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.users.models import User
from src.users.security import hash_password

USERS = [
    {
        "username": "admin",
        "password": settings.SEED_ADMIN_PASSWORD,
        "full_name": "Administrator",
    },
    {"username": "budi", "password": "password123", "full_name": "Budi Santoso"},
    {"username": "siti", "password": "password123", "full_name": "Siti Rahmawati"},
]


async def seed_users(db: AsyncSession) -> int:
    created = 0
    for item in USERS:
        exists = await db.scalar(
            select(User.id).where(User.username == item["username"])
        )
        if exists:
            continue
        db.add(
            User(
                username=item["username"],
                hashed_password=hash_password(item["password"]),
                full_name=item["full_name"],
            )
        )
        created += 1
    await db.commit()
    return created
