import asyncio

from src.config import settings
from src.database import SessionLocal, engine
from src.seeders.users import seed_users


async def main() -> None:
    if settings.ENVIRONMENT == "production":
        raise SystemExit("Seeder dinonaktifkan di production.")

    async with SessionLocal() as db:
        created = await seed_users(db)
        print(f"users: {created} dibuat")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
