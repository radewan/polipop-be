import secrets
import string
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.categories.models import Category
from src.config import settings
from src.discounts.models import Discount
from src.exceptions import AppException, Conflict, NotFound, Unprocessable
from src.product_mutations.constants import MAX_STOCK as MAX_AMOUNT
from src.product_mutations.models import ProductMutation
from src.products.models import Product
from src.transactions import pricing
from src.transactions.models import Transaction, TransactionItem
from src.transactions.schemas import PreviewRequest, TransactionCreate, TransactionSummary
from src.users.models import User
from src.utils import day_start_utc, utcnow

SORT_COLUMNS = {"created_at": Transaction.created_at, "total": Transaction.total}
NUMBER_ALPHABET = string.ascii_uppercase + string.digits


async def _load_products(
    db: AsyncSession, user: User, ids: list[uuid.UUID], *, lock: bool
) -> dict[uuid.UUID, Product]:
    # 1. Pastikan semua produk ada dan milik user (tanpa mengunci kategori)
    owned = set(
        await db.scalars(
            select(Product.id)
            .join(Product.category)
            .where(
                Product.id.in_(ids),
                Product.deleted_at.is_(None),
                Category.user_id == user.id,
            )
        )
    )
    if owned != set(ids):
        raise AppException("One or more products were not found", field="items")

    # 2. Ambil (dan kunci) baris produk, berurutan menurut id agar tidak deadlock
    query = select(Product).where(Product.id.in_(ids)).order_by(Product.id)
    if lock:
        query = query.with_for_update()
    rows = await db.scalars(query.execution_options(populate_existing=True))
    products = {product.id: product for product in rows}

    if len(products) != len(ids) or any(p.deleted_at is not None for p in products.values()):
        raise AppException("One or more products were not found", field="items")
    return products


async def _calculate(
    db: AsyncSession,
    user: User,
    items,
    products: dict[uuid.UUID, Product],
    now: datetime,
) -> pricing.Calculation:
    discounts = list(
        await db.scalars(
            select(Discount)
            .where(
                Discount.user_id == user.id,
                Discount.deleted_at.is_(None),
                Discount.is_active.is_(True),
                or_(Discount.starts_at.is_(None), Discount.starts_at <= now),
                or_(Discount.ends_at.is_(None), Discount.ends_at >= now),
            )
            .order_by(Discount.created_at, Discount.id)
        )
    )

    by_product: dict[uuid.UUID, Discount] = {}
    for discount in discounts:
        if discount.discount_scope == "product" and discount.product_id in products:
            by_product.setdefault(discount.product_id, discount)
    transaction_candidates = [d for d in discounts if d.discount_scope == "transaction"]

    lines = []
    for item in items:
        product = products[item.product_id]
        if product.price * item.quantity > MAX_AMOUNT:
            raise Unprocessable("Amount is too large", field="items")
        lines.append(pricing.price_item(product, item.quantity, by_product.get(product.id)))

    calculation = pricing.calculate(lines, transaction_candidates)
    if calculation.subtotal > MAX_AMOUNT:
        raise Unprocessable("Amount is too large", field="items")
    return calculation


async def preview(db: AsyncSession, user: User, data: PreviewRequest) -> pricing.Calculation:
    products = await _load_products(db, user, [i.product_id for i in data.items], lock=False)
    return await _calculate(db, user, data.items, products, utcnow())


async def _generate_number(db: AsyncSession, now: datetime) -> str:
    day = now.astimezone(ZoneInfo(settings.APP_TIMEZONE)).strftime("%Y%m%d")
    for _ in range(5):
        suffix = "".join(secrets.choice(NUMBER_ALPHABET) for _ in range(6))
        number = f"TRX-{day}-{suffix}"
        if not await db.scalar(
            select(Transaction.id).where(Transaction.transaction_number == number)
        ):
            return number
    raise Conflict("Could not generate a transaction number, please try again")


async def create_transaction(
    db: AsyncSession, user: User, data: TransactionCreate
) -> Transaction:
    products = await _load_products(db, user, [i.product_id for i in data.items], lock=True)
    now = utcnow()
    calc = await _calculate(db, user, data.items, products, now)

    if data.cash_received < calc.total:
        raise Unprocessable(
            f"Cash received is less than the total ({calc.total})", field="cash_received"
        )

    for line in calc.items:
        product = products[line.product_id]
        if product.stock < line.quantity:
            raise Conflict(
                f"Insufficient stock for '{product.name}' (available: {product.stock})",
                field="items",
            )

    discount = calc.discount
    transaction = Transaction(
        id=uuid.uuid4(),
        user_id=user.id,
        discount_id=discount.id if discount else None,
        transaction_number=await _generate_number(db, now),
        subtotal=calc.subtotal,
        product_discount_total=calc.product_discount_total,
        transaction_discount_amount=calc.transaction_discount_amount,
        total=calc.total,
        cash_received=data.cash_received,
        change_amount=data.cash_received - calc.total,
        discount_name=discount.name if discount else None,
        discount_type=discount.discount_type if discount else None,
        discount_value=discount.discount_value if discount else None,
    )
    db.add(transaction)
    await db.flush()  # baris transaksi harus ada sebelum item dan mutasi

    for line in calc.items:
        product = products[line.product_id]
        stock_before = product.stock
        product.stock = stock_before - line.quantity

        db.add(
            TransactionItem(
                transaction_id=transaction.id,
                product_id=product.id,
                product_name=line.product_name,
                unit_price=line.unit_price,
                quantity=line.quantity,
                discount_type=line.discount_type,
                discount_value=line.discount_value,
                discount_amount=line.discount_amount,
                subtotal=line.subtotal,
            )
        )
        db.add(
            ProductMutation(
                product_id=product.id,
                mutation_type="sale",
                quantity=-line.quantity,
                stock_before=stock_before,
                stock_after=product.stock,
                notes=f"Sale {transaction.transaction_number}",
                reference_id=transaction.id,
            )
        )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise Conflict("Could not save the transaction, please try again")

    return await get_transaction(db, user, transaction.id)


async def get_transaction(db: AsyncSession, user: User, transaction_id: uuid.UUID) -> Transaction:
    transaction = await db.scalar(
        select(Transaction)
        .options(selectinload(Transaction.items))
        .where(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .execution_options(populate_existing=True)
    )
    if not transaction:
        raise NotFound("Transaction not found")
    return transaction


async def list_transactions(
    db: AsyncSession,
    user: User,
    *,
    page: int,
    per_page: int,
    search: str | None,
    date_from: date | None,
    date_to: date | None,
    sort_by: str,
    order: str,
) -> tuple[list[TransactionSummary], int]:
    if date_from and date_to and date_from > date_to:
        raise AppException("date_from must not be after date_to", field="date_from")

    filters = [Transaction.user_id == user.id]
    if search and search.strip():
        filters.append(
            Transaction.transaction_number.icontains(search.strip(), autoescape=True)
        )
    if date_from:
        filters.append(Transaction.created_at >= day_start_utc(date_from))
    if date_to:  # inklusif sampai akhir hari date_to
        filters.append(Transaction.created_at < day_start_utc(date_to + timedelta(days=1)))

    total = await db.scalar(select(func.count(Transaction.id)).where(*filters))

    item_count = (
        select(func.count(TransactionItem.id))
        .where(TransactionItem.transaction_id == Transaction.id)
        .correlate(Transaction)
        .scalar_subquery()
    )
    column = SORT_COLUMNS[sort_by]
    direction = column.asc() if order == "asc" else column.desc()
    rows = await db.execute(
        select(Transaction, item_count)
        .where(*filters)
        .order_by(direction, Transaction.id)
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    items = [
        TransactionSummary.model_validate(transaction).model_copy(update={"item_count": count})
        for transaction, count in rows
    ]
    return items, total or 0