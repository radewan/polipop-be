import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.categories.models import Category
from src.product_mutations.models import ProductMutation
from src.products.models import Product
from src.users.models import User
from src.utils import utcnow

# Namespace tetap supaya reference_id selalu sama untuk data yang sama
SEED_NAMESPACE = uuid.UUID("6f1d3c52-8a4e-4b7e-9d21-5c0f2a7b9e11")

# username -> daftar mutasi.
# quantity bertanda (+ masuk, - keluar). days_ago = berapa hari yang lalu.
# Stok awal dicatat 30 hari lalu oleh seeder products, jadi days_ago harus < 30.
MUTATIONS: dict[str, list[dict]] = {
    "admin": [
        {
            "product": "Indomie Goreng",
            "type": "sale",
            "quantity": "-30",
            "days_ago": 12,
        },
        {
            "product": "Indomie Goreng",
            "type": "restock",
            "quantity": "50",
            "days_ago": 8,
            "notes": "Belanja mingguan",
        },
        {"product": "Indomie Goreng", "type": "sale", "quantity": "-45", "days_ago": 3},
        {
            "product": "Beras Premium 5 Kg",
            "type": "sale",
            "quantity": "-5",
            "days_ago": 10,
        },
        {
            "product": "Beras Premium 5 Kg",
            "type": "sale",
            "quantity": "-8",
            "days_ago": 6,
        },
        {
            "product": "Beras Premium 5 Kg",
            "type": "restock",
            "quantity": "20",
            "days_ago": 2,
        },
        {"product": "Telur Ayam", "type": "sale", "quantity": "-4.5", "days_ago": 9},
        {
            "product": "Telur Ayam",
            "type": "damaged",
            "quantity": "-1.5",
            "days_ago": 5,
            "notes": "Telur pecah",
        },
        {"product": "Telur Ayam", "type": "restock", "quantity": "10", "days_ago": 1},
        {
            "product": "Air Mineral 600 ml",
            "type": "sale",
            "quantity": "-60",
            "days_ago": 11,
        },
        {
            "product": "Air Mineral 600 ml",
            "type": "restock",
            "quantity": "100",
            "days_ago": 7,
        },
        {
            "product": "Air Mineral 600 ml",
            "type": "sale",
            "quantity": "-80",
            "days_ago": 2,
        },
        {"product": "Teh Botol", "type": "sale", "quantity": "-20", "days_ago": 6},
        {
            "product": "Teh Botol",
            "type": "adjustment",
            "quantity": "-3",
            "days_ago": 4,
            "notes": "Koreksi stok opname",
        },
        {
            "product": "Baterai AA (isi 4)",
            "type": "damaged",
            "quantity": "-2",
            "days_ago": 7,
            "notes": "Kemasan rusak",
        },
        {
            "product": "Baterai AA (isi 4)",
            "type": "return",
            "quantity": "1",
            "days_ago": 3,
            "notes": "Retur pelanggan",
        },
        {"product": "Pulpen Hitam", "type": "sale", "quantity": "-40", "days_ago": 5},
        {"product": "Pulpen Hitam", "type": "restock", "quantity": "60", "days_ago": 1},
        {
            "product": "Kaos Polos Hitam",
            "type": "adjustment",
            "quantity": "2",
            "days_ago": 8,
            "notes": "Ditemukan di gudang",
        },
        {
            "product": "Kaos Polos Hitam",
            "type": "sale",
            "quantity": "-6",
            "days_ago": 4,
        },
    ],
    "budi": [
        {"product": "Roti Tawar", "type": "sale", "quantity": "-8", "days_ago": 6},
        {"product": "Roti Tawar", "type": "restock", "quantity": "15", "days_ago": 3},
        {"product": "Kopi Sachet", "type": "sale", "quantity": "-120", "days_ago": 9},
        {"product": "Kopi Sachet", "type": "restock", "quantity": "200", "days_ago": 4},
        {
            "product": "Keripik Kentang",
            "type": "damaged",
            "quantity": "-3",
            "days_ago": 5,
            "notes": "Kedaluwarsa",
        },
    ],
    "siti": [
        {"product": "Kemeja Putih", "type": "sale", "quantity": "-3", "days_ago": 7},
        {
            "product": "Kemeja Putih",
            "type": "return",
            "quantity": "1",
            "days_ago": 4,
            "notes": "Salah ukuran",
        },
        {"product": "Lipstik Matte", "type": "sale", "quantity": "-10", "days_ago": 6},
        {
            "product": "Lipstik Matte",
            "type": "restock",
            "quantity": "20",
            "days_ago": 2,
        },
    ],
}


def _reference_id(username: str, item: dict) -> uuid.UUID:
    key = f"seed:{username}:{item['product']}:{item['type']}:{item['days_ago']}:{item['quantity']}"
    return uuid.uuid5(SEED_NAMESPACE, key)


async def seed_product_mutations(db: AsyncSession) -> int:
    now = utcnow()

    users = await db.scalars(
        select(User).where(
            User.username.in_(MUTATIONS.keys()),
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

        entries = [
            (_reference_id(user.username, item), item)
            for item in MUTATIONS[user.username]
        ]
        existing = set(
            await db.scalars(
                select(ProductMutation.reference_id).where(
                    ProductMutation.reference_id.in_([ref for ref, _ in entries])
                )
            )
        )

        # Proses dari yang paling lama supaya rantai stock_before -> stock_after berurutan
        for ref, item in sorted(entries, key=lambda e: -e[1]["days_ago"]):
            if ref in existing:
                continue

            product = products.get(item["product"].lower())
            if not product:
                continue  # produk belum ada, jalankan seeder products dulu

            quantity = Decimal(item["quantity"])
            stock_before = product.stock
            stock_after = stock_before + quantity
            if stock_after < 0:
                continue  # lindungi dari stok negatif

            product.stock = stock_after
            db.add(
                ProductMutation(
                    product_id=product.id,
                    mutation_type=item["type"],
                    quantity=quantity,
                    stock_before=stock_before,
                    stock_after=stock_after,
                    notes=item.get("notes"),
                    reference_id=ref,
                    created_at=now - timedelta(days=item["days_ago"]),
                )
            )
            created += 1

    await db.commit()
    return created
