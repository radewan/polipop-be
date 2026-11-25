import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from src.categories.models import Category
from src.config import settings
from src.exceptions import AppException, Conflict
from src.product_mutations.constants import MAX_STOCK
from src.product_mutations.models import ProductMutation
from src.product_mutations.schemas import MutationCreate
from src.products.models import Product
from src.users.models import User


def _day_start_utc(day: date) -> datetime:
    """Awal hari di zona waktu aplikasi, dinyatakan dalam UTC."""
    local = datetime.combine(day, time.min, tzinfo=ZoneInfo(settings.APP_TIMEZONE))
    return local.astimezone(UTC)


def _joined(query):
    return query.join(ProductMutation.product).join(Product.category)


async def list_mutations(
    db: AsyncSession,
    user: User,
    *,
    page: int,
    per_page: int,
    product_id: uuid.UUID | None,
    search: str | None,
    mutation_type: str | None,
    date_from: date | None,
    date_to: date | None,
) -> tuple[list[ProductMutation], int]:
    if date_from and date_to and date_from > date_to:
        raise AppException("date_from must not be after date_to", field="date_from")

    filters = [Category.user_id == user.id, ProductMutation.deleted_at.is_(None)]
    if product_id:
        filters.append(ProductMutation.product_id == product_id)
    if search and search.strip():
        filters.append(Product.name.icontains(search.strip(), autoescape=True))
    if mutation_type:
        filters.append(ProductMutation.mutation_type == mutation_type)
    if date_from:
        filters.append(ProductMutation.created_at >= _day_start_utc(date_from))
    if date_to:  # inklusif: sampai akhir hari date_to
        filters.append(
            ProductMutation.created_at < _day_start_utc(date_to + timedelta(days=1))
        )

    total = await db.scalar(
        _joined(select(func.count(ProductMutation.id))).where(*filters)
    )
    rows = await db.scalars(
        _joined(select(ProductMutation))
        .options(contains_eager(ProductMutation.product))
        .where(*filters)
        .order_by(ProductMutation.created_at.desc(), ProductMutation.id)
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    return list(rows), total or 0


async def create_mutation(
    db: AsyncSession, user: User, data: MutationCreate
) -> ProductMutation:
    # 1. Pastikan produk ada dan milik user ini
    owned = await db.scalar(
        select(Product.id)
        .join(Product.category)
        .where(
            Product.id == data.product_id,
            Product.deleted_at.is_(None),
            Category.user_id == user.id,
        )
    )
    if not owned:
        raise AppException("Product not found", field="product_id")

    # 2. Kunci baris produk sampai commit, lalu baca stok TERBARU
    product = await db.scalar(
        select(Product)
        .where(Product.id == data.product_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if product is None or product.deleted_at is not None:
        raise AppException("Product not found", field="product_id")

    stock_before = product.stock
    stock_after = stock_before + data.quantity
    if stock_after < 0:
        raise Conflict(
            f"Insufficient stock (available: {stock_before})", field="quantity"
        )
    if stock_after > MAX_STOCK:
        raise AppException("Resulting stock is too large", field="quantity")

    # 3. Ubah stok dan catat mutasi dalam SATU transaksi
    product.stock = stock_after
    mutation = ProductMutation(
        product_id=product.id,
        mutation_type=data.mutation_type,
        quantity=data.quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        notes=data.notes,
        reference_id=data.reference_id,
    )
    db.add(mutation)
    await db.commit()

    return await db.scalar(
        select(ProductMutation)
        .join(ProductMutation.product)
        .options(contains_eager(ProductMutation.product))
        .where(ProductMutation.id == mutation.id)
        .execution_options(populate_existing=True)
    )
