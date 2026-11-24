import uuid

from fastapi import UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from src import storage
from src.categories.models import Category
from src.exceptions import AppException, Conflict, NotFound
from src.products.models import Product
from src.products.schemas import ProductCreate, ProductUpdate
from src.users.models import User
from src.utils import utcnow

SORT_COLUMNS = {
    "name": Product.name,
    "price": Product.price,
    "stock": Product.stock,
    "created_at": Product.created_at,
}


def _owned_filters(user: User) -> list:
    return [Category.user_id == user.id, Product.deleted_at.is_(None)]


async def _get_owned_category(
    db: AsyncSession, user: User, category_id: uuid.UUID
) -> Category:
    category = await db.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user.id,
            Category.deleted_at.is_(None),
        )
    )
    if not category:
        raise AppException("Category not found", field="category_id")
    return category


async def _ensure_unique_barcode(
    db: AsyncSession, user: User, barcode: str, exclude_id: uuid.UUID | None = None
) -> None:
    query = (
        select(Product.id)
        .join(Product.category)
        .where(*_owned_filters(user), Product.barcode == barcode)
    )
    if exclude_id:
        query = query.where(Product.id != exclude_id)
    if await db.scalar(query):
        raise Conflict("Barcode already used", field="barcode")


async def list_products(
    db: AsyncSession,
    user: User,
    *,
    page: int,
    per_page: int,
    search: str | None,
    category_id: uuid.UUID | None,
    sort_by: str,
    order: str,
) -> tuple[list[Product], int]:
    filters = _owned_filters(user)
    if category_id:
        filters.append(Product.category_id == category_id)
    if search and search.strip():
        term = search.strip()
        filters.append(
            or_(
                Product.name.icontains(term, autoescape=True),
                Category.name.icontains(term, autoescape=True),
                Product.barcode.icontains(term, autoescape=True),
            )
        )

    total = await db.scalar(
        select(func.count()).select_from(Product).join(Product.category).where(*filters)
    )

    column = SORT_COLUMNS[sort_by]
    direction = column.asc() if order == "asc" else column.desc()
    rows = await db.scalars(
        select(Product)
        .join(Product.category)
        .options(contains_eager(Product.category))
        .where(*filters)
        .order_by(direction, Product.id)
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    return list(rows), total or 0


async def get_product(db: AsyncSession, user: User, product_id: uuid.UUID) -> Product:
    product = await db.scalar(
        select(Product)
        .join(Product.category)
        .options(contains_eager(Product.category))
        .where(Product.id == product_id, *_owned_filters(user))
        .execution_options(populate_existing=True)
    )
    if not product:
        raise NotFound("Product not found")
    return product


async def create_product(db: AsyncSession, user: User, data: ProductCreate) -> Product:
    await _get_owned_category(db, user, data.category_id)
    if data.barcode:
        await _ensure_unique_barcode(db, user, data.barcode)

    product = Product(**data.model_dump())
    db.add(product)
    await db.commit()
    return await get_product(db, user, product.id)


async def update_product(
    db: AsyncSession, user: User, product_id: uuid.UUID, data: ProductUpdate
) -> Product:
    product = await get_product(db, user, product_id)

    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise AppException("No fields to update")

    if "category_id" in changes and changes["category_id"] != product.category_id:
        await _get_owned_category(db, user, changes["category_id"])
    if changes.get("barcode") and changes["barcode"] != product.barcode:
        await _ensure_unique_barcode(
            db, user, changes["barcode"], exclude_id=product.id
        )

    for key, value in changes.items():
        setattr(product, key, value)
    await db.commit()
    return await get_product(db, user, product.id)


async def delete_product(db: AsyncSession, user: User, product_id: uuid.UUID) -> None:
    product = await get_product(db, user, product_id)
    product.deleted_at = utcnow()
    await db.commit()


async def set_image(
    db: AsyncSession, user: User, product_id: uuid.UUID, file: UploadFile
) -> Product:
    product = await get_product(db, user, product_id)  # 404 dulu sebelum memproses file

    data = await storage.read_upload(file)
    new_path = await storage.save_image(data)
    old_path = product.image

    product.image = new_path
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        storage.delete_image(new_path)  # jangan tinggalkan file yatim
        raise

    storage.delete_image(old_path)  # hapus file lama hanya setelah commit berhasil
    return await get_product(db, user, product.id)


async def remove_image(db: AsyncSession, user: User, product_id: uuid.UUID) -> None:
    product = await get_product(db, user, product_id)
    old_path = product.image
    if not old_path:
        return

    product.image = None
    await db.commit()
    storage.delete_image(old_path)
