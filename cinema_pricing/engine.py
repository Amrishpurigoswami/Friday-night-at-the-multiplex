from decimal import Decimal, ROUND_HALF_UP

from .models import BookingRequest, Invoice, PricingRules, SeatTier


class PricingError(ValueError):
    """Raised when a booking cannot be priced or booked."""


def _rounded_paise(amount: Decimal) -> int:
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class CinemaPricingEngine:
    def __init__(self, tiers: list[SeatTier], rules: PricingRules) -> None:
        self._tiers = {tier.name: tier for tier in tiers}
        if len(self._tiers) != len(tiers):
            raise PricingError("Tier names must be unique")
        self.rules = rules
        self._validate_configuration()

    @property
    def tiers(self) -> tuple[SeatTier, ...]:
        return tuple(self._tiers.values())

    def quote(self, booking: BookingRequest) -> Invoice:
        tier = self._validate_booking(booking)
        return self._calculate_invoice(booking, tier)

    def book(self, booking: BookingRequest) -> Invoice:
        tier = self._validate_booking(booking)
        invoice = self._calculate_invoice(booking, tier)
        tier.available_seats -= booking.quantity
        return invoice

    def _validate_configuration(self) -> None:
        if not self._tiers:
            raise PricingError("At least one seat tier is required")
        for tier in self._tiers.values():
            if tier.price_paise < 0 or tier.available_seats < 0:
                raise PricingError("Tier price and availability cannot be negative")
        if self.rules.member_discount_percent < 0 or self.rules.gst_percent < 0:
            raise PricingError("Percentages cannot be negative")
        if self.rules.member_discount_cap_paise_per_ticket < 0:
            raise PricingError("Member discount cap cannot be negative")
        if self.rules.festival_discount_paise < 0:
            raise PricingError("Festival discount cannot be negative")
        if self.rules.convenience_fee_paise_per_ticket < 0:
            raise PricingError("Convenience fee cannot be negative")

    def _validate_booking(self, booking: BookingRequest) -> SeatTier:
        tier = self._tiers.get(booking.tier_name)
        if tier is None:
            raise PricingError(f"Unknown tier: {booking.tier_name}")
        if not isinstance(booking.quantity, int) or isinstance(booking.quantity, bool):
            raise PricingError("Quantity must be a whole number")
        if booking.quantity <= 0:
            raise PricingError("Quantity must be greater than zero")
        if booking.quantity > tier.available_seats:
            raise PricingError(
                f"Tier sold out: {booking.tier_name} has only "
                f"{tier.available_seats} seat(s) available"
            )
        return tier

    def _calculate_invoice(self, booking: BookingRequest, tier: SeatTier) -> Invoice:
        rules = self.rules
        base = booking.quantity * tier.price_paise
        member_discount = 0
        if booking.is_member:
            calculated = _rounded_paise(
                Decimal(base) * rules.member_discount_percent / Decimal("100")
            )
            member_discount = min(
                calculated,
                booking.quantity * rules.member_discount_cap_paise_per_ticket,
            )

        after_member = base - member_discount
        festival_discount = min(rules.festival_discount_paise, after_member)
        discounted_tickets = after_member - festival_discount
        convenience_fee = booking.quantity * rules.convenience_fee_paise_per_ticket
        taxable_amount = discounted_tickets + convenience_fee
        gst = _rounded_paise(
            Decimal(taxable_amount) * rules.gst_percent / Decimal("100")
        )

        return Invoice(
            tier_name=tier.name,
            quantity=booking.quantity,
            base_amount_paise=base,
            member_discount_paise=member_discount,
            festival_discount_paise=festival_discount,
            convenience_fee_paise=convenience_fee,
            taxable_amount_paise=taxable_amount,
            gst_paise=gst,
            total_paise=taxable_amount + gst,
            member_discount_percent=rules.member_discount_percent,
            gst_percent=rules.gst_percent,
        )