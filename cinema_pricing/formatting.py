from .models import Invoice


def money(paise: int) -> str:
    sign = "-" if paise < 0 else ""
    absolute = abs(paise)
    return f"{sign}₹{absolute // 100}.{absolute % 100:02d}"


def format_invoice(invoice: Invoice) -> str:
    member_label = f"Member discount ({invoice.member_discount_percent:g}%)"
    gst_label = f"GST ({invoice.gst_percent:g}%)"
    rows = [
        "CINEMA BILL",
        "=" * 36,
        f"{invoice.quantity} x {invoice.tier_name} tickets".ljust(25)
        + money(invoice.base_amount_paise),
        member_label.ljust(25) + money(-invoice.member_discount_paise),
        "Festival discount".ljust(25) + money(-invoice.festival_discount_paise),
        "Convenience fee".ljust(25) + money(invoice.convenience_fee_paise),
        gst_label.ljust(25) + money(invoice.gst_paise),
        "-" * 36,
        "TOTAL".ljust(25) + money(invoice.total_paise),
        "=" * 36,
    ]
    return "\n".join(rows)