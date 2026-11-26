import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0.00")


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class Line:
    product_id: uuid.UUID
    product_name: str
    unit_price: Decimal
    quantity: Decimal
    discount_type: str | None
    discount_value: Decimal | None
    discount_amount: Decimal
    subtotal: Decimal


@dataclass
class AppliedDiscount:
    id: uuid.UUID
    name: str
    discount_type: str
    discount_value: Decimal
    amount: Decimal


@dataclass
class Calculation:
    items: list[Line]
    subtotal: Decimal
    product_discount_total: Decimal
    transaction_discount_amount: Decimal
    total: Decimal
    discount: AppliedDiscount | None


def price_item(product, quantity: Decimal, discount) -> Line:
    """Hitung satu item. `discount` = diskon produk aktif atau None."""
    gross = money(product.price * quantity)
    amount = ZERO
    d_type = d_value = None

    if discount is not None:
        d_type, d_value = discount.discount_type, discount.discount_value
        if d_type == "percentage":
            amount = money(gross * d_value / 100)
        else:  # fixed: per satuan, dibatasi harga satuan
            amount = money(min(d_value, product.price) * quantity)
        amount = min(amount, gross)

    return Line(
        product_id=product.id,
        product_name=product.name,
        unit_price=product.price,
        quantity=quantity,
        discount_type=d_type,
        discount_value=d_value,
        discount_amount=amount,
        subtotal=gross - amount,
    )


def _transaction_amount(base: Decimal, discount) -> Decimal:
    if discount.discount_type == "percentage":
        return money(base * discount.discount_value / 100)
    return money(min(discount.discount_value, base))


def pick_transaction_discount(
    base: Decimal, candidates
) -> tuple[object | None, Decimal]:
    """Pilih satu diskon transaksi dengan potongan terbesar.
    `candidates` harus terurut dari yang paling lama dibuat, sehingga hasil seri
    jatuh ke yang lebih lama (hanya potongan yang lebih besar yang menggantikan)."""
    best, best_amount = None, ZERO
    for discount in candidates:
        minimum = discount.min_transaction_amount
        if minimum is not None and base < minimum:
            continue
        amount = _transaction_amount(base, discount)
        if amount > best_amount:
            best, best_amount = discount, amount
    return best, best_amount


def calculate(lines: list[Line], transaction_candidates) -> Calculation:
    subtotal = sum((line.subtotal + line.discount_amount for line in lines), ZERO)
    product_discount_total = sum((line.discount_amount for line in lines), ZERO)
    base = subtotal - product_discount_total

    discount, amount = pick_transaction_discount(base, transaction_candidates)
    applied = (
        AppliedDiscount(
            id=discount.id,
            name=discount.name,
            discount_type=discount.discount_type,
            discount_value=discount.discount_value,
            amount=amount,
        )
        if discount
        else None
    )
    return Calculation(
        items=lines,
        subtotal=subtotal,
        product_discount_total=product_discount_total,
        transaction_discount_amount=amount,
        total=base - amount,
        discount=applied,
    )
