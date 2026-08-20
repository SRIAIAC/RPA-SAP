"""Procurement rules beyond invoice matching — PO approval limits
(Procurement KB #2) and blocked-vendor handling (Procurement KB #6)."""

from app.rules.base import RuleResult

PO_APPROVAL_LIMITS_INR = {
    "Manager": 200_000,  # Procurement KB #2
    "Senior Manager": 1_000_000,
    "Department Head": 5_000_000,
    # Admin: no limit — falls through to the None branch below.
}


def evaluate_po_approval(amount: float, approver_level: str) -> RuleResult:
    limit = PO_APPROVAL_LIMITS_INR.get(approver_level)
    if limit is None:
        return RuleResult(
            decision="AUTO_APPROVE",
            reasons=[f"{approver_level} has unlimited PO authority (Procurement KB #2)"],
            recommended_action="Proceed to create PO in SAP MM.",
        )
    if amount <= limit:
        return RuleResult(
            decision="AUTO_APPROVE",
            reasons=[f"PO amount INR {amount:,.0f} within {approver_level} limit of INR {limit:,.0f} (Procurement KB #2)"],
            recommended_action="Proceed to create PO in SAP MM.",
        )
    return RuleResult(
        decision="ESCALATE",
        reasons=[f"PO amount INR {amount:,.0f} exceeds {approver_level} limit of INR {limit:,.0f} (Procurement KB #2)"],
        recommended_action="Escalate to the next approval level or Admin/CFO sign-off.",
    )


def evaluate_vendor_blocked(vendor_blocked: bool) -> RuleResult:
    if vendor_blocked:
        return RuleResult(
            decision="BLOCKED_VENDOR",
            reasons=["Vendor is blocked in SAP (Procurement KB #6)"],
            recommended_action="Re-route to Procurement Manager for an alternate-vendor decision within 2 business days.",
        )
    return RuleResult(decision="OK", reasons=["Vendor is not blocked"], recommended_action="Proceed.")
