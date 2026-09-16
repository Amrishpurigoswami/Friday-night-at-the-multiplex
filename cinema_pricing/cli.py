import argparse
import csv
from decimal import Decimal, InvalidOperation

from .engine import CinemaPricingEngine, PricingError
from .formatting import format_invoice
from .importer import PriceImportReport, import_price_list
from .models import BookingRequest, PricingRules, SeatTier


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise argparse.ArgumentTypeError(f"Invalid decimal: {value}") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Price a single-tier cinema booking")
    parser.add_argument("--tier", default="Gold", help="Seat tier to book")
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--member", action="store_true")
    parser.add_argument("--festival-discount", type=int, default=500)
    parser.add_argument("--member-percent", type=_decimal, default=Decimal("10"))
    parser.add_argument("--member-cap-per-ticket", type=int, default=1000)
    parser.add_argument("--fee-per-ticket", type=int, default=200)
    parser.add_argument("--gst-percent", type=_decimal, default=Decimal("18"))
    parser.add_argument("--gold-price", type=int, default=25000)
    parser.add_argument("--gold-seats", type=int, default=50)
    parser.add_argument("--silver-price", type=int, default=18000)
    parser.add_argument("--silver-seats", type=int, default=50)
    parser.add_argument("--recliner-price", type=int, default=40000)
    parser.add_argument("--recliner-seats", type=int, default=20)
    parser.add_argument(
        "--price-list",
        help="CSV file with name,price columns; prices are rupees unless marked paise",
    )
    parser.add_argument("--imported-seats", type=int, default=50)
    return parser


def _load_price_list(path: str) -> PriceImportReport:
    with open(path, newline="", encoding="utf-8") as file:
        return import_price_list(csv.DictReader(file))


def _print_import_report(report: PriceImportReport) -> None:
    print(
        f"Price list: {len(report.imported)} imported, "
        f"{len(report.deduplicated)} de-duplicated, "
        f"{len(report.rejected)} rejected"
    )
    for item in report.deduplicated:
        print(f"  duplicate row {item.row_number}: {item.normalized_name}")
    for item in report.rejected:
        print(f"  rejected row {item.row_number}: {item.reason}")


def main() -> int:
    args = build_parser().parse_args()
    report = _load_price_list(args.price_list) if args.price_list else None
    if report is not None:
        _print_import_report(report)
        if not report.imported:
            print("Booking rejected: price list contains no valid seat classes")
            return 2
        tiers = [
            SeatTier(item.normalized_name, item.price_paise, args.imported_seats)
            for item in report.imported
        ]
    else:
        tiers = [
            SeatTier("Silver", args.silver_price, args.silver_seats),
            SeatTier("Gold", args.gold_price, args.gold_seats),
            SeatTier("Recliner", args.recliner_price, args.recliner_seats),
        ]
    engine = CinemaPricingEngine(
        tiers,
        PricingRules(
            member_discount_percent=args.member_percent,
            member_discount_cap_paise_per_ticket=args.member_cap_per_ticket,
            festival_discount_paise=args.festival_discount,
            convenience_fee_paise_per_ticket=args.fee_per_ticket,
            gst_percent=args.gst_percent,
        ),
    )
    try:
        invoice = engine.book(BookingRequest(args.tier, args.quantity, args.member))
    except PricingError as error:
        print(f"Booking rejected: {error}")
        return 2
    print(format_invoice(invoice))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())