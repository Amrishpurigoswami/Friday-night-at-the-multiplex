# Friday Night at the Multiplex

A cinema ticket pricing engine that calculates every amount in integer paise and
returns a line-by-line invoice. A booking contains tickets from one tier only.

## Rules implemented

- Member percentage discount is applied first.
- The member discount cap is per ticket, then multiplied by ticket quantity.
- Flat festival discount is applied after the member discount.
- Festival discount cannot make the ticket amount negative.
- Convenience fee is charged per ticket.
- GST is calculated on discounted tickets plus convenience fee.
- Percentage calculations are rounded to the nearest paise using half-up rounding.
- Inventory is checked before calculation and decremented only after a successful booking.

All configurable money values are integer paise. For example, `25000` means
₹250.00. Percentage values use `Decimal` so that the conversion into paise is
deterministic.

## Setup

Python 3.12 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Install the optional visual interface with:

```bash
python -m pip install -e '.[ui]'
```

## Run the CLI

The CLI uses sensible defaults for a Silver, Gold, and Recliner counter:

```bash
python -m cinema_pricing --tier Gold --quantity 2 --member
```

Prices, offers, fees, tax, and inventory can be changed with command-line
options. Use `python -m cinema_pricing --help` for the complete list.

To import a messy CSV price list, use `name,price` columns. Names are trimmed
and matched case-insensitively. Prices are rupees by default, with support for
symbols, commas, decimals, and explicit `paise` values:

```bash
python -m cinema_pricing --price-list prices.csv --tier Gold --quantity 2
```

The repository includes a ready-to-run example at `prices.csv`.

The CLI reports valid rows imported, duplicate rows de-duplicated, and invalid
rows rejected with reasons. The first valid row wins when names differ only by
case or whitespace.

## Run the Streamlit interface

```bash
streamlit run streamlit_app.py
```

The Streamlit app is a wide counter interface with two tabs:

- **Booking Counter:** availability table, live quote, final `Confirm & Print`
	validation, receipt history, and session revenue summary.
- **Import Seat Prices:** CSV upload, bundled sample execution/download, clean
	list, duplicate list, rejected-row list, and an explicit apply-to-engine
	action that preserves existing inventory counts.

The bundled `sample_messy_data.csv` demonstrates duplicate casing, inconsistent
formats, blank values, negative values, and zero values.

## Run tests and debug

```bash
pytest -q
python -m py_compile cinema_pricing/*.py streamlit_app.py
```

The core API is:

```python
invoice = engine.book(BookingRequest("Gold", 2, is_member=True))
print(invoice.total_paise)
```

Use `engine.quote(...)` when you need a calculation without changing inventory.
`PricingError` explains rejected tiers, quantities, and availability failures.

## Project layout

```text
cinema_pricing/
	models.py       # booking, tier, rules, and invoice data
	engine.py       # validation and pricing pipeline
	formatting.py   # rupee and CLI invoice formatting
	cli.py          # pure Python command-line entry point
streamlit_app.py  # optional visual interface
tests/            # behavior and money-rule tests
REASONING.md      # design decisions
AI_LOGS.md        # conversation record
```
