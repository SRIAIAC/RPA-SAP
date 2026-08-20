"""Contract rules — renewal window and unowned-contract escalation
(Procurement KB #13)."""

from app.rules.base import RuleResult

RENEWAL_WINDOW_DAYS = 30  # Procurement KB #13


def evaluate_contract_expiry(days_remaining: int, has_owner: bool) -> RuleResult:
    if not has_owner:
        return RuleResult(
            decision="ESCALATE_NO_OWNER",
            reasons=["Contract has no assigned owner on file (Procurement KB #13)"],
            recommended_action="Escalate to the Department Head immediately, rather than waiting for the 30-day trigger.",
        )
    if days_remaining <= RENEWAL_WINDOW_DAYS:
        return RuleResult(
            decision="RENEWAL_REVIEW",
            reasons=[f"Contract expires in {days_remaining} day(s) — inside the {RENEWAL_WINDOW_DAYS}-day renewal window (Procurement KB #13)"],
            recommended_action="Notify the contract owner and Finance; create a renewal task in the tracker.",
        )
    return RuleResult(
        decision="NO_ACTION",
        reasons=[f"Contract expires in {days_remaining} day(s) — outside the {RENEWAL_WINDOW_DAYS}-day renewal window"],
        recommended_action="No action required yet.",
    )
