"""Invoice 3-way match rules — Procurement KB #1 (tolerance table) and #8
(duplicate detection). Checks run in priority order: duplicate, missing
GRN, quantity, price — matching how a real AP clerk would triage (a
duplicate or missing-GRN invoice can't even be meaningfully qty/price
checked).

Simplification vs. the KB: Procurement KB #1 distinguishes hazard-
classified items (zero quantity tolerance) from general MRO items (2%/5
units). This demo's data model doesn't track a per-material hazard flag,
so the general MRO tolerance is applied uniformly — documented here rather
than silently narrowed.
"""

from app.rules.base import RuleResult

QTY_TOLERANCE_PCT = 0.02  # Procurement KB #1: "variance of up to 2%"
QTY_TOLERANCE_ABS_UNITS = 5  # Procurement KB #1: "...or 5 units, whichever is smaller"
PRICE_TOLERANCE_PCT = 0.03  # Procurement KB #1: "up to 3%"
PRICE_TOLERANCE_ABS_INR = 5000  # Procurement KB #1: "...or INR 5,000 per line, whichever is lower"


def evaluate_three_way_match(
    po_quantity: float,
    grn_quantity: float | None,
    invoice_quantity: float,
    po_unit_price: float,
    invoice_unit_price: float,
    is_duplicate: bool,
    grn_exists: bool,
) -> RuleResult:
    if is_duplicate:
        return RuleResult(
            decision="DUPLICATE_INVOICE",
            reasons=["Invoice number already exists for this vendor in SAP FI (Procurement KB #8)"],
            recommended_action="Confirm with AP whether this is a genuine resubmission; reject if duplicate.",
        )

    if not grn_exists or grn_quantity is None:
        return RuleResult(
            decision="MISSING_GRN",
            reasons=["Invoice submitted but no goods receipt has been posted against this PO"],
            recommended_action="Hold payment until GRN is posted in SAP MM.",
        )

    qty_variance = abs(invoice_quantity - grn_quantity)
    qty_tolerance = min(QTY_TOLERANCE_ABS_UNITS, grn_quantity * QTY_TOLERANCE_PCT)
    if qty_variance > qty_tolerance:
        return RuleResult(
            decision="QUANTITY_MISMATCH",
            reasons=[
                f"Invoice qty {invoice_quantity} vs GRN qty {grn_quantity}: variance {qty_variance:.2f} "
                f"exceeds tolerance {qty_tolerance:.2f} (Procurement KB #1)"
            ],
            recommended_action="Review GRN and invoice line items before resubmitting.",
            metadata={"qty_variance": qty_variance, "qty_tolerance": qty_tolerance},
        )

    price_variance = abs(invoice_unit_price - po_unit_price)
    price_tolerance = min(PRICE_TOLERANCE_ABS_INR, po_unit_price * PRICE_TOLERANCE_PCT)
    if price_variance > price_tolerance:
        return RuleResult(
            decision="PRICE_MISMATCH",
            reasons=[
                f"Invoice price {invoice_unit_price} vs PO price {po_unit_price}: variance "
                f"{price_variance:.2f} exceeds tolerance {price_tolerance:.2f} (Procurement KB #1)"
            ],
            recommended_action="Confirm price change with vendor/procurement before posting.",
            metadata={"price_variance": price_variance, "price_tolerance": price_tolerance},
        )

    return RuleResult(
        decision="AUTO_APPROVE",
        reasons=["Quantities and price within tolerance across PO/GRN/Invoice (Procurement KB #1)"],
        recommended_action="Post invoice in SAP FI.",
    )
