from __future__ import annotations

import csv
from decimal import Decimal
from io import StringIO
from pathlib import Path

import streamlit as st

from cinema_pricing import (
    BookingRequest,
    CinemaPricingEngine,
    PricingError,
    PricingRules,
    SeatTier,
    import_price_list,
)
from cinema_pricing.formatting import format_invoice, money
from cinema_pricing.importer import PriceImportReport


st.set_page_config(
    page_title="Friday Night at the Multiplex",
    page_icon="🎬",
    layout="wide",
)


def default_inventory() -> dict[str, dict[str, int]]:
    return {
        "Silver": {"price": 18000, "available": 20},
        "Gold": {"price": 25000, "available": 50},
        "Recliner": {"price": 40000, "available": 10},
    }


def make_engine(
    inventory: dict[str, dict[str, int]], rules: PricingRules
) -> CinemaPricingEngine:
    return CinemaPricingEngine(
        [SeatTier(name, values["price"], values["available"]) for name, values in inventory.items()],
        rules,
    )


if "inventory" not in st.session_state:
    st.session_state.inventory = default_inventory()
if "rules" not in st.session_state:
    st.session_state.rules = PricingRules(Decimal("10"), 1000, 500, 200, Decimal("18"))
if "bookings" not in st.session_state:
    st.session_state.bookings = []
if "import_report" not in st.session_state:
    st.session_state.import_report = None

st.title("🎬 Friday Night at the Multiplex")
st.caption("Counter demo with exact integer-paisa pricing and auditable imports")

with st.sidebar:
    st.header("Pricing Rules")
    st.caption("Changes apply to the next booking.")
    festival_rs = st.number_input(
        "Festival discount (₹)", min_value=0, max_value=10000,
        value=int(st.session_state.rules.festival_discount_paise // 100), step=10,
    )
    member_pct = st.slider(
        "Member discount (%)", min_value=0, max_value=50,
        value=int(st.session_state.rules.member_discount_percent),
    )
    member_cap_rs = st.number_input(
        "Member cap per ticket (₹)", min_value=0, max_value=5000,
        value=int(st.session_state.rules.member_discount_cap_paise_per_ticket // 100), step=10,
    )
    fee_rs = st.number_input(
        "Convenience fee per ticket (₹)", min_value=0, max_value=500,
        value=int(st.session_state.rules.convenience_fee_paise_per_ticket // 100), step=5,
    )
    gst_pct = st.slider("GST (%)", min_value=0, max_value=28, value=int(st.session_state.rules.gst_percent))
    st.session_state.rules = PricingRules(
        member_discount_percent=Decimal(member_pct),
        member_discount_cap_paise_per_ticket=int(member_cap_rs) * 100,
        festival_discount_paise=int(festival_rs) * 100,
        convenience_fee_paise_per_ticket=int(fee_rs) * 100,
        gst_percent=Decimal(gst_pct),
    )
    st.divider()
    if st.button("Reset inventory and history", use_container_width=True):
        st.session_state.inventory = default_inventory()
        st.session_state.bookings = []
        st.success("Inventory and booking history reset.")

rules = st.session_state.rules
tab_booking, tab_import = st.tabs(["🎟️ Booking Counter", "📂 Import Seat Prices"])

with tab_booking:
    col_book, col_history = st.columns([1, 1], gap="large")
    with col_book:
        st.subheader("Current Availability")
        inventory = st.session_state.inventory
        st.table([
            {
                "Tier": name,
                "Price": money(values["price"]),
                "Available": values["available"],
                "Status": "Available" if values["available"] else "Sold Out",
            }
            for name, values in inventory.items()
        ])

        st.subheader("New Booking")
        tier_choice = st.selectbox("Seat tier", list(inventory))
        available = inventory[tier_choice]["available"]
        qty = st.number_input(
            "Number of tickets",
            min_value=0 if available == 0 else 1,
            max_value=max(available, 1),
            value=0 if available == 0 else 1,
            step=1,
        )
        is_member = st.checkbox("Member card")
        request = BookingRequest(tier_choice, int(qty), is_member)
        engine = make_engine(inventory, rules)

        st.subheader("Live Quote")
        try:
            preview = engine.quote(request)
        except PricingError as error:
            preview = None
            st.warning(str(error))
        else:
            for line in preview.lines:
                st.write(f"{line.description}: **{money(line.amount_paise)}**")
            st.metric("Total payable", money(preview.total_paise))

        if st.button(
            "💳 Confirm & Print",
            type="primary",
            use_container_width=True,
            disabled=preview is None,
        ):
            try:
                confirmed = engine.book(request)
            except PricingError as error:
                st.error(f"Booking rejected during final validation: {error}")
            else:
                inventory[tier_choice]["available"] -= confirmed.quantity
                st.session_state.bookings.insert(0, (request, confirmed))
                st.success(f"Booking confirmed: {money(confirmed.total_paise)}")
                st.rerun()

    with col_history:
        st.subheader("🧾 Receipts")
        bookings = st.session_state.bookings
        if not bookings:
            st.info("No bookings yet. Use the counter on the left to get started.")
        else:
            shown = bookings[:5]
            receipt_tabs = st.tabs([
                f"#{index + 1} — {req.tier_name} x{req.quantity}"
                for index, (req, _) in enumerate(shown)
            ])
            for receipt_tab, (_, invoice) in zip(receipt_tabs, shown):
                with receipt_tab:
                    st.code(format_invoice(invoice), language=None)
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Tickets", invoice.quantity)
                    m2.metric("Tier", invoice.tier_name)
                    m3.metric("Total", money(invoice.total_paise))

            if len(bookings) > 5:
                st.caption(f"Showing 5 of {len(bookings)} bookings.")
            st.divider()
            st.subheader("📊 Session Summary")
            total_tickets = sum(invoice.quantity for _, invoice in bookings)
            total_revenue = sum(invoice.total_paise for _, invoice in bookings)
            s1, s2, s3 = st.columns(3)
            s1.metric("Bookings", len(bookings))
            s2.metric("Tickets sold", total_tickets)
            s3.metric("Revenue", money(total_revenue))

with tab_import:
    st.subheader("📂 Import and Clean a Messy Seat Price List")
    st.markdown(
        "Upload `tier_name,price` or `name,price`. Currency symbols, commas, "
        "duplicate casing, blanks, negative values, and zero values are handled "
        "with a row-level audit."
    )
    upload_col, sample_col = st.columns([2, 1])
    with upload_col:
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    with sample_col:
        sample_path = Path(__file__).with_name("sample_messy_data.csv")
        use_sample = st.button("▶ Run bundled sample", use_container_width=True)
        if sample_path.exists():
            st.download_button(
                "⬇ Download sample CSV",
                data=sample_path.read_bytes(),
                file_name=sample_path.name,
                mime="text/csv",
                use_container_width=True,
            )

    report: PriceImportReport | None = None
    if uploaded_file is not None:
        report = import_price_list(csv.DictReader(StringIO(uploaded_file.getvalue().decode("utf-8-sig"))))
        st.session_state.import_report = report
    elif use_sample and sample_path.exists():
        report = import_price_list(csv.DictReader(StringIO(sample_path.read_text(encoding="utf-8"))))
        st.session_state.import_report = report
    elif use_sample:
        st.error("Bundled sample_messy_data.csv was not found.")
    if report is None:
        report = st.session_state.import_report

    if report is not None:
        st.divider()
        total_rows = len(report.imported) + len(report.deduplicated) + len(report.rejected)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows read", total_rows)
        c2.metric("Imported", len(report.imported))
        c3.metric("Duplicates", len(report.deduplicated))
        c4.metric("Rejected", len(report.rejected))

        clean_col, duplicate_col, rejected_col = st.columns(3)
        with clean_col:
            st.markdown("### ✅ Clean price list")
            st.table([
                {"Tier": item.normalized_name, "Price": money(item.price_paise), "Paise": item.price_paise}
                for item in report.imported
            ] or [{"Tier": "No valid tiers", "Price": "", "Paise": ""}])
        with duplicate_col:
            st.markdown("### ⚠️ Duplicates discarded")
            st.table([
                {"Row": item.row_number, "Raw name": item.original_name, "Kept as": item.normalized_name}
                for item in report.deduplicated
            ] or [{"Row": "", "Raw name": "No duplicates", "Kept as": ""}])
        with rejected_col:
            st.markdown("### ❌ Rejected rows")
            st.table([
                {"Row": item.row_number, "Raw row": str(item.row), "Reason": item.reason}
                for item in report.rejected
            ] or [{"Row": "", "Raw row": "No rejections", "Reason": ""}])

        st.divider()
        st.subheader("Apply imported prices to booking engine")
        st.caption("Existing inventory counts are preserved; only matching tier prices change.")
        if st.button("🔁 Apply cleaned prices", disabled=not report.imported):
            updated = 0
            skipped = 0
            for item in report.imported:
                if item.normalized_name in st.session_state.inventory:
                    st.session_state.inventory[item.normalized_name]["price"] = item.price_paise
                    updated += 1
                else:
                    skipped += 1
            message = f"Updated {updated} tier(s)."
            if skipped:
                message += f" Skipped {skipped} new tier(s) not in the current counter."
            st.success(message)
            st.rerun()
