import asyncio

from src.config import settings
from src.database import SessionLocal, engine
from src.seeders.categories import seed_categories
from src.seeders.products import seed_products
from src.seeders.users import seed_users


async def main() -> None:
    if settings.ENVIRONMENT == "production":
        raise SystemExit("Seeder dinonaktifkan di production.")

    try:
        async with SessionLocal() as db:
            created = await seed_users(db)
            print(f"users: {created} dibuat")

            created = await seed_categories(db)
            print(f"categories: {created} dibuat")

            created = await seed_products(db)
            print(f"products: {created} dibuat")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
