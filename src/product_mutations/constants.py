from decimal import Decimal
from typing import Literal

ManualMutationType = Literal["restock", "return", "sale", "damaged", "adjustment"]
AnyMutationType = Literal[
    "initial", "restock", "return", "sale", "damaged", "adjustment"
]

INITIAL_TYPE = "initial"
INCREASE_TYPES = {"restock", "return"}
DECREASE_TYPES = {"sale", "damaged"}

MAX_STOCK = Decimal("9999999999999.99")  # batas DECIMAL(15,2)
