import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from src.categories.models import Category
from src.discounts.models import Discount
from src.discounts.schemas import DiscountCreate, DiscountUpdate
from src.exceptions import AppException, Conflict, NotFound, Unprocessable
from src.products.models import Product
from src.users.models import User
from src.utils import utcnow

SORT_COLUMNS = {
    "created_at": Discount.created_at,
    "name": Discount.name,
    "discount_value": Discount.discount_value,
    "starts_at": Discount.starts_at,
    "ends_at": Discount.ends_at,
}
NULLABLE_SORTS = {"starts_at", "ends_at"}


def _status_filter(status: str, now: datetime):
    if status == "inactive":
        return Discount.is_active.is_(False)
    if status == "scheduled":
        return and_(Discount.is_active.is_(True), Discount.starts_at > now)
    if status == "expired":
        return and_(Discount.is_active.is_(True), Discount.ends_at < now)
    return and_(  # active
        Discount.is_active.is_(True),
        or_(Discount.starts_at.is_(None), Discount.starts_at <= now),
        or_(Discount.ends_at.is_(None), Discount.ends_at >= now),
    )


async def list_discounts(
    db: AsyncSession,
    user: User,
    *,
    page: int,
    per_page: int,
    search: str | None,
    scope: str | None,
    discount_type: str | None,
    status: str | None,
    product_id: uuid.UUID | None,
    sort_by: str,
    order: str,
) -> tuple[list[Discount], int]:
    filters = [Discount.user_id == user.id, Discount.deleted_at.is_(None)]
    if scope:
        filters.append(Discount.discount_scope == scope)
    if discount_type:
        filters.append(Discount.discount_type == discount_type)
    if product_id:
        filters.append(Discount.product_id == product_id)
    if status:
        filters.append(_status_filter(status, utcnow()))
    if search and search.strip():
        term = search.strip()
        filters.append(
            or_(
                Discount.name.icontains(term, autoescape=True),
                Product.name.icontains(term, autoescape=True),
            )
        )

    total = await db.scalar(
        select(func.count(Discount.id)).outerjoin(Discount.product).where(*filters)
    )

    column = SORT_COLUMNS[sort_by]
    ordering = [column.asc() if order == "asc" else column.desc(), Discount.id]
    if sort_by in NULLABLE_SORTS:
        ordering.insert(
            0, column.is_(None)
        )  # nilai kosong selalu di akhir (MySQL tanpa NULLS LAST)

    rows = await db.scalars(
        select(Discount)
        .outerjoin(Discount.product)
        .options(contains_eager(Discount.product))
        .where(*filters)
        .order_by(*ordering)
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    return list(rows), total or 0


async def get_discount(
    db: AsyncSession, user: User, discount_id: uuid.UUID
) -> Discount:
    discount = await db.scalar(
        select(Discount)
        .outerjoin(Discount.product)
        .options(contains_eager(Discount.product))
        .where(
            Discount.id == discount_id,
            Discount.user_id == user.id,
            Discount.deleted_at.is_(None),
        )
        .execution_options(populate_existing=True)
    )
    if not discount:
        raise NotFound("Discount not found")
    return discount


async def _lock_owned_product(
    db: AsyncSession, user: User, product_id: uuid.UUID
) -> Product:
    """Pastikan produk milik user, lalu kunci barisnya sampai commit (cegah dua diskon aktif bersamaan)."""
    owned = await db.scalar(
        select(Product.id)
        .join(Product.category)
        .where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
            Category.user_id == user.id,
        )
    )
    if not owned:
        raise AppException("Product not found", field="product_id")

    product = await db.scalar(
        select(Product)
        .where(Product.id == product_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if product is None or product.deleted_at is not None:
        raise AppException("Product not found", field="product_id")
    return product


async def _ensure_no_active_product_discount(
    db: AsyncSession, product_id: uuid.UUID, exclude_id: uuid.UUID | None = None
) -> None:
    query = select(Discount.id).where(
        Discount.product_id == product_id,
        Discount.discount_scope == "product",
        Discount.is_active.is_(True),
        Discount.deleted_at.is_(None),
    )
    if exclude_id:
        query = query.where(Discount.id != exclude_id)
    if await db.scalar(query):
        raise Conflict("Product already has an active discount", field="product_id")


def _validate_effective(
    *,
    scope: str,
    discount_type: str,
    value: Decimal,
    min_amount: Decimal | None,
    starts_at: datetime | None,
    ends_at: datetime | None,
    product: Product | None,
) -> None:
    if discount_type == "percentage" and value > 100:
        raise Unprocessable("Percentage must not exceed 100", field="discount_value")
    if scope == "product" and min_amount is not None:
        raise Unprocessable(
            "min_transaction_amount must be empty for product discounts",
            field="min_transaction_amount",
        )
    if starts_at and ends_at and ends_at < starts_at:
        raise Unprocessable("ends_at must not be before starts_at", field="ends_at")
    if product is not None and discount_type == "fixed" and value > product.price:
        raise Unprocessable(
            f"Fixed discount must not exceed product price ({product.price})",
            field="discount_value",
        )


async def create_discount(
    db: AsyncSession, user: User, data: DiscountCreate
) -> Discount:
    product = None
    if data.discount_scope == "product":
        product = await _lock_owned_product(db, user, data.product_id)
        if data.is_active:
            await _ensure_no_active_product_discount(db, product.id)

    _validate_effective(
        scope=data.discount_scope,
        discount_type=data.discount_type,
        value=data.discount_value,
        min_amount=data.min_transaction_amount,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        product=product,
    )

    discount = Discount(user_id=user.id, **data.model_dump())
    db.add(discount)
    await db.commit()
    return await get_discount(db, user, discount.id)


async def update_discount(
    db: AsyncSession, user: User, discount_id: uuid.UUID, data: DiscountUpdate
) -> Discount:
    discount = await get_discount(db, user, discount_id)

    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise AppException("No fields to update")

    def effective(key: str):
        return changes[key] if key in changes else getattr(discount, key)

    product = None
    if discount.discount_scope == "product":
        product = await _lock_owned_product(db, user, discount.product_id)

    _validate_effective(
        scope=discount.discount_scope,
        discount_type=effective("discount_type"),
        value=effective("discount_value"),
        min_amount=effective("min_transaction_amount"),
        starts_at=effective("starts_at"),
        ends_at=effective("ends_at"),
        product=product,
    )

    if product is not None and effective("is_active"):
        await _ensure_no_active_product_discount(db, product.id, exclude_id=discount.id)

    for key, value in changes.items():
        setattr(discount, key, value)
    await db.commit()
    return await get_discount(db, user, discount.id)


async def delete_discount(db: AsyncSession, user: User, discount_id: uuid.UUID) -> None:
    discount = await get_discount(db, user, discount_id)
    discount.deleted_at = utcnow()
    await db.commit()
