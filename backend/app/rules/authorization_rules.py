"""Authorization rules for exception-queue actions (Approve/Reject/Retry/
Escalate/Request correction). Complements, not duplicates, app.access —
access.py is the single source of truth for page/endpoint-level RBAC
(who can see which data); this module encodes the specific minimum level
required per exception *action*, with a human-readable reason, consumed by
the exception-resolution endpoint (Phase 9) to explain why an action was
allowed or denied rather than just returning a bare 403.
"""

from app.models import LEVEL_RANK, Level
from app.rules.base import RuleResult

EXCEPTION_ACTION_MIN_LEVEL: dict[str, Level] = {
    "approve": Level.SENIOR_MANAGER,
    "reject": Level.SENIOR_MANAGER,
    "escalate": Level.MANAGER,
    "retry": Level.MANAGER,
    "request_correction": Level.MANAGER,
}


def evaluate_exception_action_authorization(actor_level: Level, action: str) -> RuleResult:
    required = EXCEPTION_ACTION_MIN_LEVEL.get(action, Level.SENIOR_MANAGER)
    if LEVEL_RANK[actor_level] >= LEVEL_RANK[required]:
        return RuleResult(
            decision="AUTHORIZED",
            reasons=[f"{actor_level.value} meets the minimum level ({required.value}) required for '{action}'"],
            recommended_action="Proceed.",
        )
    return RuleResult(
        decision="UNAUTHORIZED",
        reasons=[f"{actor_level.value} is below the minimum level ({required.value}) required for '{action}'"],
        recommended_action=f"Escalate to a {required.value} or above.",
    )
