import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .models import SeatTier


@dataclass(frozen=True)
class ImportedPrice:
    row_number: int
    original_name: object
    normalized_name: str
    price_paise: int


@dataclass(frozen=True)
class RejectedPrice:
    row_number: int
    row: object
    reason: str


@dataclass(frozen=True)
class PriceImportReport:
    imported: tuple[ImportedPrice, ...]
    deduplicated: tuple[ImportedPrice, ...]
    rejected: tuple[RejectedPrice, ...]

    @property
    def tiers(self) -> tuple[SeatTier, ...]:
        return tuple(
            SeatTier(item.normalized_name, item.price_paise, 0)
            for item in self.imported
        )


def _parse_price(value: object) -> int:
    if value is None or not str(value).strip():
        raise ValueError("blank price")

    text = str(value).strip().lower()
    is_paise = bool(re.search(r"\bpaise?\b", text))
    text = re.sub(r"(?:₹|rs\.?|inr|paise?)", "", text)
    text = text.replace(",", "").strip()
    try:
        amount = Decimal(text)
    except InvalidOperation as error:
        raise ValueError("invalid price format") from error
    if not amount.is_finite():
        raise ValueError("invalid price format")
    if amount < 0:
        raise ValueError("negative price")
    if is_paise:
        if amount != amount.to_integral_value():
            raise ValueError("paise price must be a whole number")
        price_paise = int(amount)
    else:
        price_paise = int(
            (amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
    if price_paise == 0:
        raise ValueError("zero price")
    return price_paise


def _row_values(row: object) -> tuple[object, object]:
    if isinstance(row, Mapping):
        return (
            row.get("name", row.get("tier", row.get("tier_name"))),
            row.get("price"),
        )
    if isinstance(row, Sequence) and not isinstance(row, (str, bytes)):
        if len(row) < 2:
            return row[0] if row else None, None
        return row[0], row[1]
    return None, None


def import_price_list(rows: Iterable[object]) -> PriceImportReport:
    imported: list[ImportedPrice] = []
    deduplicated: list[ImportedPrice] = []
    rejected: list[RejectedPrice] = []
    seen: set[str] = set()

    for row_number, row in enumerate(rows, start=1):
        raw_name, raw_price = _row_values(row)
        normalized_name = " ".join(str(raw_name or "").split()).title()
        if not normalized_name:
            rejected.append(RejectedPrice(row_number, row, "blank seat-class name"))
            continue
        try:
            price_paise = _parse_price(raw_price)
        except ValueError as error:
            rejected.append(RejectedPrice(row_number, row, str(error)))
            continue

        item = ImportedPrice(row_number, raw_name, normalized_name, price_paise)
        key = normalized_name.casefold()
        if key in seen:
            deduplicated.append(item)
            continue
        seen.add(key)
        imported.append(item)

    return PriceImportReport(tuple(imported), tuple(deduplicated), tuple(rejected))