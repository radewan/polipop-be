from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.categories.models import Category
from src.discounts.models import Discount
from src.products.models import Product
from src.users.models import User
from src.utils import utcnow

# starts_days / ends_days: selisih hari dari sekarang (negatif = masa lalu)
# Aturan: tiap produk hanya boleh punya satu diskon aktif.
DISCOUNTS: dict[str, list[dict]] = {
    "admin": [
        {
            "name": "Diskon Indomie",
            "scope": "product",
            "product": "Indomie Goreng",
            "type": "percentage",
            "value": "10",
        },
        {
            "name": "Diskon Air Mineral",
            "scope": "product",
            "product": "Air Mineral 600 ml",
            "type": "fixed",
            "value": "500",
            "starts_days": -3,
            "ends_days": 7,
        },
        {
            "name": "Diskon Kaos Lama",
            "scope": "product",
            "product": "Kaos Polos Hitam",
            "type": "percentage",
            "value": "25",
            "starts_days": -30,
            "ends_days": -10,
        },
        {
            "name": "Diskon Pulpen",
            "scope": "product",
            "product": "Pulpen Hitam",
            "type": "percentage",
            "value": "5",
            "active": False,
        },
        {
            "name": "Promo Hemat",
            "scope": "transaction",
            "type": "fixed",
            "value": "5000",
            "min_amount": "100000",
        },
        {
            "name": "Promo Akhir Bulan",
            "scope": "transaction",
            "type": "percentage",
            "value": "15",
            "min_amount": "200000",
            "ends_days": 5,
        },
        {
            "name": "Promo Tahun Baru",
            "scope": "transaction",
            "type": "percentage",
            "value": "20",
            "min_amount": "300000",
            "starts_days": 30,
            "ends_days": 37,
        },
    ],
    "budi": [
        {
            "name": "Diskon Kopi Sachet",
            "scope": "product",
            "product": "Kopi Sachet",
            "type": "percentage",
            "value": "5",
        },
        {
            "name": "Promo Belanja Hemat",
            "scope": "transaction",
            "type": "fixed",
            "value": "3000",
            "min_amount": "50000",
        },
    ],
    "siti": [
        {
            "name": "Diskon Kemeja",
            "scope": "product",
            "product": "Kemeja Putih",
            "type": "percentage",
            "value": "15",
        },
        {
            "name": "Promo Fashion",
            "scope": "transaction",
            "type": "percentage",
            "value": "10",
            "min_amount": "150000",
        },
    ],
}


async def seed_discounts(db: AsyncSession) -> int:
    now = utcnow()

    users = await db.scalars(
        select(User).where(
            User.username.in_(DISCOUNTS.keys()),
            User.deleted_at.is_(None),
        )
    )

    created = 0
    for user in users:
        products = {
            product.name.lower(): product
            for product in await db.scalars(
                select(Product)
                .join(Product.category)
                .where(Category.user_id == user.id, Product.deleted_at.is_(None))
            )
        }
        existing = {
            name.lower()
            for name in await db.scalars(
                select(Discount.name).where(
                    Discount.user_id == user.id, Discount.deleted_at.is_(None)
                )
            )
        }

        for item in DISCOUNTS[user.username]:
            if item["name"].lower() in existing:
                continue

            product = None
            if item["scope"] == "product":
                product = products.get(item["product"].lower())
                if not product:
                    continue  # produk belum ada, jalankan seeder products dulu

            db.add(
                Discount(
                    user_id=user.id,
                    product_id=product.id if product else None,
                    name=item["name"],
                    discount_scope=item["scope"],
                    discount_type=item["type"],
                    discount_value=Decimal(item["value"]),
                    min_transaction_amount=(
                        Decimal(item["min_amount"]) if "min_amount" in item else None
                    ),
                    starts_at=(
                        now + timedelta(days=item["starts_days"])
                        if "starts_days" in item
                        else None
                    ),
                    ends_at=(
                        now + timedelta(days=item["ends_days"])
                        if "ends_days" in item
                        else None
                    ),
                    is_active=item.get("active", True),
                )
            )
            existing.add(item["name"].lower())
            created += 1

    await db.commit()
    return created
