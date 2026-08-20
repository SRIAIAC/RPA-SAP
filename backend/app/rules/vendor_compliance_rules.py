"""Vendor onboarding/compliance rules — insurance certificate expiry
(Procurement KB #4), KYC checklist (Procurement KB #3), duplicate vendor
check (Procurement KB #5)."""

from datetime import date
from typing import Optional

from app.rules.base import RuleResult

INSURANCE_RENEWAL_WINDOW_DAYS = 30  # Procurement KB #4


def evaluate_vendor_compliance(
    insurance_expiry: Optional[date],
    gst_number: Optional[str],
    is_duplicate_gst_or_bank: bool,
    today: Optional[date] = None,
) -> RuleResult:
    today = today or date.today()

    if insurance_expiry is not None:
        days_remaining = (insurance_expiry - today).days
        if days_remaining < 0:
            return RuleResult(
                decision="EXPIRED_INSURANCE",
                reasons=[f"Insurance certificate expired {abs(days_remaining)} day(s) ago (Procurement KB #4)"],
                recommended_action="Block PO issuance until insurance is renewed.",
                metadata={"days_remaining": days_remaining},
            )
        if days_remaining <= INSURANCE_RENEWAL_WINDOW_DAYS:
            return RuleResult(
                decision="INSURANCE_RENEWAL_DUE",
                reasons=[f"Insurance certificate expires in {days_remaining} day(s) — inside the {INSURANCE_RENEWAL_WINDOW_DAYS}-day renewal window (Procurement KB #4)"],
                recommended_action="Trigger an automatic renewal request.",
                metadata={"days_remaining": days_remaining},
            )

    if not gst_number:
        return RuleResult(
            decision="MISSING_KYC",
            reasons=["Missing GST/tax certificate (Procurement KB #3)"],
            recommended_action="Request GST certificate before creating the vendor master.",
        )

    if is_duplicate_gst_or_bank:
        return RuleResult(
            decision="DUPLICATE_VENDOR_FLAG",
            reasons=["GSTIN or bank account number matches an existing vendor (Procurement KB #5)"],
            recommended_action="Flag for manual review — not auto-rejected, as legitimate vendors can share a holding-company GSTIN.",
        )

    return RuleResult(
        decision="COMPLIANT",
        reasons=["KYC and compliance checks passed"],
        recommended_action="Proceed to create the vendor master in SAP.",
    )
