from decimal import Decimal
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.categories.models import Category
from src.product_mutations.constants import INITIAL_TYPE
from src.product_mutations.models import ProductMutation
from src.products.models import Product
from src.users.models import User

# username -> nama kategori -> daftar produk
# Nama kategori harus sama dengan yang ada di src/seeders/categories.py
PRODUCTS: dict[str, dict[str, list[dict]]] = {
    "admin": {
        "Makanan": [
            {
                "name": "Indomie Goreng",
                "barcode": "899100000001",
                "price": "3500",
                "stock": "120",
                "unit": "pcs",
            },
            {
                "name": "Beras Premium 5 Kg",
                "barcode": "899100000002",
                "price": "72000",
                "stock": "25",
                "unit": "karung",
            },
            {
                "name": "Telur Ayam",
                "barcode": None,
                "price": "28000",
                "stock": "15.5",
                "unit": "kg",
            },
        ],
        "Minuman": [
            {
                "name": "Air Mineral 600 ml",
                "barcode": "899100000003",
                "price": "3000",
                "stock": "200",
                "unit": "botol",
            },
            {
                "name": "Teh Botol",
                "barcode": "899100000004",
                "price": "5000",
                "stock": "80",
                "unit": "botol",
            },
        ],
        "Elektronik": [
            {
                "name": "Kabel USB-C 1 m",
                "barcode": "899100000005",
                "price": "35000",
                "stock": "30",
                "unit": "pcs",
            },
            {
                "name": "Baterai AA (isi 4)",
                "barcode": "899100000006",
                "price": "22000",
                "stock": "45",
                "unit": "pack",
            },
        ],
        "Pakaian": [
            {
                "name": "Kaos Polos Hitam",
                "barcode": "899100000007",
                "price": "55000",
                "stock": "18",
                "unit": "pcs",
            },
        ],
        "Alat Tulis": [
            {
                "name": "Pulpen Hitam",
                "barcode": "899100000008",
                "price": "3500",
                "stock": "150",
                "unit": "pcs",
            },
            {
                "name": "Buku Tulis 38 Lembar",
                "barcode": "899100000009",
                "price": "6000",
                "stock": "90",
                "unit": "pcs",
            },
        ],
    },
    "budi": {
        "Makanan": [
            {
                "name": "Roti Tawar",
                "barcode": "899100000010",
                "price": "16000",
                "stock": "20",
                "unit": "bungkus",
            },
            {
                "name": "Mie Instan Soto",
                "barcode": "899100000011",
                "price": "3200",
                "stock": "100",
                "unit": "pcs",
            },
        ],
        "Minuman": [
            {
                "name": "Kopi Sachet",
                "barcode": "899100000012",
                "price": "2000",
                "stock": "300",
                "unit": "sachet",
            },
            {
                "name": "Susu UHT 250 ml",
                "barcode": "899100000013",
                "price": "7500",
                "stock": "60",
                "unit": "kotak",
            },
        ],
        "Snack": [
            {
                "name": "Keripik Kentang",
                "barcode": "899100000014",
                "price": "11000",
                "stock": "40",
                "unit": "bungkus",
            },
            {
                "name": "Biskuit Cokelat",
                "barcode": "899100000015",
                "price": "9000",
                "stock": "55",
                "unit": "bungkus",
            },
        ],
    },
    "siti": {
        "Pakaian": [
            {
                "name": "Kemeja Putih",
                "barcode": "899100000016",
                "price": "120000",
                "stock": "12",
                "unit": "pcs",
            },
            {
                "name": "Rok Plisket",
                "barcode": "899100000017",
                "price": "95000",
                "stock": "9",
                "unit": "pcs",
            },
        ],
        "Kosmetik": [
            {
                "name": "Lipstik Matte",
                "barcode": "899100000018",
                "price": "49000",
                "stock": "35",
                "unit": "pcs",
            },
            {
                "name": "Sabun Cuci Muka",
                "barcode": "899100000019",
                "price": "27000",
                "stock": "42",
                "unit": "pcs",
            },
        ],
        "Aksesoris": [
            {
                "name": "Jepit Rambut",
                "barcode": None,
                "price": "8000",
                "stock": "75",
                "unit": "pcs",
            },
        ],
    },
}


async def seed_products(db: AsyncSession) -> int:
    users = await db.scalars(
        select(User).where(
            User.username.in_(PRODUCTS.keys()),
            User.deleted_at.is_(None),
        )
    )

    created = 0
    for user in users:
        categories = {
            category.name.lower(): category
            for category in await db.scalars(
                select(Category).where(
                    Category.user_id == user.id,
                    Category.deleted_at.is_(None),
                )
            )
        }

        existing = await db.execute(
            select(Product.category_id, Product.name, Product.barcode)
            .join(Product.category)
            .where(Category.user_id == user.id, Product.deleted_at.is_(None))
        )
        names = set()
        barcodes = set()
        for category_id, name, barcode in existing:
            names.add((category_id, name.lower()))
            if barcode:
                barcodes.add(barcode)

        for category_name, items in PRODUCTS[user.username].items():
            category = categories.get(category_name.lower())
            if not category:
                continue  # kategori belum ada, jalankan seeder categories dulu

            for item in items:
                key = (category.id, item["name"].lower())
                barcode = item["barcode"]
                if key in names or (barcode and barcode in barcodes):
                    continue

                product = Product(
                    id=uuid.uuid4(),
                    category_id=category.id,
                    name=item["name"],
                    barcode=barcode,
                    price=Decimal(item["price"]),
                    stock=Decimal(item["stock"]),
                    unit=item["unit"],
                )
                db.add(product)

                if product.stock > 0:
                    db.add(
                        ProductMutation(
                            product_id=product.id,
                            mutation_type=INITIAL_TYPE,
                            quantity=product.stock,
                            stock_before=Decimal("0"),
                            stock_after=product.stock,
                            notes="Initial stock",
                        )
                    )

                names.add(key)
                if barcode:
                    barcodes.add(barcode)
                created += 1

    await db.commit()
    return created
