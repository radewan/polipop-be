from decimal import ROUND_CEILING, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.categories.models import Category
from src.products.models import Product
from src.transactions import service
from src.transactions.models import Transaction
from src.transactions.schemas import CartItem, PreviewRequest, TransactionCreate
from src.users.models import User

# username -> daftar keranjang, tiap keranjang berisi (nama produk, jumlah)
TRANSACTIONS: dict[str, list[list[tuple[str, str]]]] = {
    "admin": [
        [
            ("Indomie Goreng", "10"),
            ("Air Mineral 600 ml", "6"),
            ("Beras Premium 5 Kg", "2"),
        ],
        [
            ("Indomie Goreng", "10"),
            ("Air Mineral 600 ml", "6"),
            ("Beras Premium 5 Kg", "3"),
        ],
        [("Teh Botol", "5"), ("Pulpen Hitam", "10"), ("Telur Ayam", "2.5")],
    ],
    "budi": [
        [("Roti Tawar", "4"), ("Kopi Sachet", "20")],
        [("Keripik Kentang", "3"), ("Mie Instan Soto", "10"), ("Susu UHT 250 ml", "6")],
    ],
    "siti": [
        [("Kemeja Putih", "2"), ("Lipstik Matte", "3")],
        [("Rok Plisket", "1"), ("Sabun Cuci Muka", "2"), ("Jepit Rambut", "5")],
    ],
}

ROUND_TO = Decimal("50000")  # uang tunai dibulatkan ke atas ke kelipatan ini


async def seed_transactions(db: AsyncSession) -> int:
    users = list(
        await db.scalars(
            select(User).where(
                User.username.in_(TRANSACTIONS.keys()), User.deleted_at.is_(None)
            )
        )
    )

    created = 0
    for user in users:
        if await db.scalar(
            select(Transaction.id).where(Transaction.user_id == user.id).limit(1)
        ):
            continue  # sudah punya transaksi

        products = {
            product.name.lower(): product.id
            for product in await db.scalars(
                select(Product)
                .join(Product.category)
                .where(Category.user_id == user.id, Product.deleted_at.is_(None))
            )
        }

        for cart in TRANSACTIONS[user.username]:
            items = [
                CartItem(product_id=products[name.lower()], quantity=Decimal(qty))
                for name, qty in cart
                if name.lower() in products
            ]
            if len(items) != len(cart):
                continue  # produk belum ada, jalankan seeder products dulu

            calc = await service.preview(db, user, PreviewRequest(items=items))
            cash = (calc.total / ROUND_TO).to_integral_value(
                rounding=ROUND_CEILING
            ) * ROUND_TO
            await service.create_transaction(
                db, user, TransactionCreate(items=items, cash_received=cash)
            )
            created += 1

    return created
