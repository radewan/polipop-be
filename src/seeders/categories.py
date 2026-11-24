from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.categories.models import Category
from src.users.models import User

# username -> daftar nama kategori
CATEGORIES: dict[str, list[str]] = {
    "admin": ["Makanan", "Minuman", "Elektronik", "Pakaian", "Alat Tulis"],
    "budi": ["Makanan", "Minuman", "Snack"],
    "siti": ["Pakaian", "Kosmetik", "Aksesoris"],
}


async def seed_categories(db: AsyncSession) -> int:
    users = await db.scalars(
        select(User).where(
            User.username.in_(CATEGORIES.keys()),
            User.deleted_at.is_(None),
        )
    )

    created = 0
    for user in users:
        existing = set(
            await db.scalars(
                select(Category.name).where(
                    Category.user_id == user.id,
                    Category.deleted_at.is_(None),
                )
            )
        )
        existing_lower = {name.lower() for name in existing}

        for name in CATEGORIES[user.username]:
            if name.lower() in existing_lower:
                continue
            db.add(Category(user_id=user.id, name=name))
            existing_lower.add(name.lower())
            created += 1

    await db.commit()
    return created
