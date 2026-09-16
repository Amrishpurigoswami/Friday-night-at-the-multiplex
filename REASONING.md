# Reasoning

## Choice of implementation

The core is a pure Python 3.12 package. It has no runtime dependency because
the pricing rules should be usable from a counter CLI, an API, or a future
checkout application. Streamlit is an optional presentation layer, not part of
the pricing calculation.

## Money model

The engine stores all currency as integer paise. This avoids binary floating
point errors in multiplication, subtraction, and reconciliation. Percentages
are represented as `Decimal` values only while calculating a discount or GST;
the result is immediately rounded with `ROUND_HALF_UP` and converted to an
integer paise amount.

## Calculation order

For a single-tier booking, the pipeline is:

1. Validate the tier, quantity, and available seats.
2. Calculate base price as quantity multiplied by tier price.
3. Calculate the member percentage discount, capped at cap-per-ticket times quantity.
4. Apply the flat festival discount to the remaining ticket amount.
5. Add the per-ticket convenience fee.
6. Calculate GST on discounted tickets plus convenience fee.
7. Return the invoice total and ledger.
8. On `book`, decrement inventory only after all prior steps succeed.

The `quote` method follows the same calculation but never mutates inventory.
This makes previews safe and keeps mutation at one explicit boundary.

## Messy price-list import

The importer accepts CSV dictionaries or two-value rows. It normalizes class
names by trimming whitespace and title-casing them, then de-duplicates using a
case-insensitive key. The first valid occurrence wins. Price text accepts
currency symbols, `rs`, `inr`, comma separators, decimal rupees, and explicit
whole-paise values. Blank names, blank prices, malformed prices, negative
prices, and fractional explicit-paise values are rejected rather than guessed.

`PriceImportReport` keeps separate imported, de-duplicated, and rejected rows
so the counter can explain exactly what happened to every input row.

## Streamlit presentation

The visual layer keeps the pricing engine authoritative. A live quote calls
`quote`, while `Confirm & Print` calls `book` again against the current
inventory before recording a receipt. Session history is presentation state;
the calculation and inventory validation remain in the engine. The import tab
does not silently replace prices: the operator reviews the clean, duplicate,
and rejected sections first, then explicitly applies matching cleaned prices
while existing seat counts remain unchanged.

## Scope decisions

The requirements specify one tier per booking, so mixed-tier bookings are
rejected by the data shape rather than silently combined. The engine accepts a
list of tiers and configurable rules, so it is not tied to one cinema show.

The invoice exposes both a total and named amounts. The taxable amount is
stored explicitly to make the GST base auditable. The line items sum to the
same total as the calculation, including negative discount lines.

## Testing strategy

Tests focus on rules that commonly cause counter discrepancies: discount order,
per-ticket caps, half-up rounding, invalid quantities, sold-out inventory, and
the no-mutation-on-failure guarantee. The CLI is also compiled and exercised
as an integration check.