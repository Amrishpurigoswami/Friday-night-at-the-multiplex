from decimal import Decimal

import pytest

from cinema_pricing import (
    BookingRequest,
    CinemaPricingEngine,
    PricingError,
    PricingRules,
    SeatTier,
)


def make_engine(available: int = 10) -> CinemaPricingEngine:
    return CinemaPricingEngine(
        [SeatTier("Gold", 25000, available)],
        PricingRules(Decimal("10"), 1000, 500, 200, Decimal("18")),
    )


def test_member_discount_is_applied_before_festival_discount():
    invoice = make_engine().quote(BookingRequest("Gold", 2, True))

    assert invoice.base_amount_paise == 50000
    assert invoice.member_discount_paise == 2000
    assert invoice.festival_discount_paise == 500
    assert invoice.taxable_amount_paise == 47900
    assert invoice.gst_paise == 8622
    assert invoice.total_paise == 56522


def test_member_cap_is_per_ticket():
    rules = PricingRules(Decimal("50"), 1000, 0, 0, Decimal("0"))
    engine = CinemaPricingEngine([SeatTier("Gold", 25000, 10)], rules)

    invoice = engine.quote(BookingRequest("Gold", 3, True))

    assert invoice.member_discount_paise == 3000


def test_gst_rounds_half_up_to_one_paise():
    rules = PricingRules(Decimal("0"), 0, 0, 0, Decimal("50"))
    engine = CinemaPricingEngine([SeatTier("Gold", 1, 1)], rules)

    invoice = engine.quote(BookingRequest("Gold", 1))

    assert invoice.gst_paise == 1


def test_booking_decrements_inventory_only_after_success():
    engine = make_engine(available=2)

    engine.book(BookingRequest("Gold", 2))
    assert engine.tiers[0].available_seats == 0

    with pytest.raises(PricingError, match="Tier sold out"):
        engine.book(BookingRequest("Gold", 1))
    assert engine.tiers[0].available_seats == 0


@pytest.mark.parametrize("quantity", [0, -1, True])
def test_invalid_quantity_is_rejected(quantity):
    with pytest.raises(PricingError, match="Quantity"):
        make_engine().quote(BookingRequest("Gold", quantity))


def test_unknown_tier_is_rejected():
    with pytest.raises(PricingError, match="Unknown tier"):
        make_engine().quote(BookingRequest("Silver", 1))