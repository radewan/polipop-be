import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.categories.models import Category
from src.categories.schemas import CategoryCreate, CategoryRead, CategoryUpdate
from src.exceptions import Conflict, NotFound
from src.products.models import Product
from src.users.models import User, utcnow


async def _ensure_unique_name(
    db: AsyncSession, user_id: uuid.UUID, name: str, exclude_id: uuid.UUID | None = None
) -> None:
    query = select(Category.id).where(
        Category.user_id == user_id,
        Category.deleted_at.is_(None),
        func.lower(Category.name) == name.lower(),
    )
    if exclude_id:
        query = query.where(Category.id != exclude_id)
    if await db.scalar(query):
        raise Conflict("Category name already exists", field="name")


async def list_categories(
    db: AsyncSession, user: User, page: int, per_page: int, search: str | None
) -> tuple[list[CategoryRead], int]:
    filters = [Category.user_id == user.id, Category.deleted_at.is_(None)]
    if search:
        filters.append(Category.name.icontains(search.strip(), autoescape=True))

    total = await db.scalar(select(func.count()).select_from(Category).where(*filters))

    product_count = (
        select(func.count(Product.id))
        .where(Product.category_id == Category.id, Product.deleted_at.is_(None))
        .correlate(Category)
        .scalar_subquery()
    )
    rows = await db.execute(
        select(Category, product_count)
        .where(*filters)
        .order_by(Category.created_at.desc(), Category.id)
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    items = [
        CategoryRead.model_validate(category).model_copy(
            update={"total_product": count}
        )
        for category, count in rows
    ]
    return items, total or 0


async def get_category(
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
        raise NotFound("Category not found")
    return category


async def create_category(
    db: AsyncSession, user: User, data: CategoryCreate
) -> Category:
    await _ensure_unique_name(db, user.id, data.name)
    category = Category(user_id=user.id, name=data.name)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession, user: User, category_id: uuid.UUID, data: CategoryUpdate
) -> Category:
    category = await get_category(db, user, category_id)
    await _ensure_unique_name(db, user.id, data.name, exclude_id=category.id)
    category.name = data.name
    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, user: User, category_id: uuid.UUID) -> None:
    category = await get_category(db, user, category_id)

    has_products = await db.scalar(
        select(Product.id)
        .where(Product.category_id == category.id, Product.deleted_at.is_(None))
        .limit(1)
    )
    if has_products:
        raise Conflict("Category still has products")

    category.deleted_at = utcnow()
    await db.commit()
