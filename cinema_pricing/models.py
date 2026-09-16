from dataclasses import dataclass
from decimal import Decimal


@dataclass
class SeatTier:
    name: str
    price_paise: int
    available_seats: int


@dataclass(frozen=True)
class PricingRules:
    member_discount_percent: Decimal
    member_discount_cap_paise_per_ticket: int
    festival_discount_paise: int
    convenience_fee_paise_per_ticket: int
    gst_percent: Decimal


@dataclass(frozen=True)
class BookingRequest:
    tier_name: str
    quantity: int
    is_member: bool = False


@dataclass(frozen=True)
class InvoiceLine:
    description: str
    amount_paise: int
    quantity: int | None = None
    unit_amount_paise: int | None = None


@dataclass(frozen=True)
class Invoice:
    tier_name: str
    quantity: int
    base_amount_paise: int
    member_discount_paise: int
    festival_discount_paise: int
    convenience_fee_paise: int
    taxable_amount_paise: int
    gst_paise: int
    total_paise: int
    member_discount_percent: Decimal
    gst_percent: Decimal

    @property
    def lines(self) -> tuple[InvoiceLine, ...]:
        return (
            InvoiceLine("Ticket price", self.base_amount_paise, self.quantity),
            InvoiceLine("Member discount", -self.member_discount_paise),
            InvoiceLine("Festival discount", -self.festival_discount_paise),
            InvoiceLine("Convenience fee", self.convenience_fee_paise, self.quantity),
            InvoiceLine("GST", self.gst_paise),
        )
