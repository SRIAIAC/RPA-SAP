"""HSE rules — severity-based escalation (HSE KB #2) and spill-volume
reporting threshold (HSE KB #5). The AI classifier proposes a severity
tier; this rule decides whether that tier triggers an auto-escalation —
AI recommends, rules decide."""

from typing import Optional

from app.rules.base import RuleResult

SPILL_REGULATORY_THRESHOLD_LITERS = 159  # HSE KB #5: "1 barrel (159 L)"


def evaluate_hse_incident(ai_severity: str, spill_volume_liters: Optional[float] = None) -> RuleResult:
    severity = ai_severity
    reasons = [f"AI-classified severity: {severity}"]
    regulatory_notification = False

    if spill_volume_liters is not None and spill_volume_liters > SPILL_REGULATORY_THRESHOLD_LITERS:
        regulatory_notification = True
        reasons.append(
            f"Spill volume {spill_volume_liters}L exceeds {SPILL_REGULATORY_THRESHOLD_LITERS}L "
            f"(1 barrel) — mandatory regulatory notification (HSE KB #5)"
        )
        if severity not in ("High", "Critical"):
            severity = "High"
            reasons.append("Severity raised to High due to spill volume threshold")

    escalate = severity in ("High", "Critical")
    decision = "AUTO_ESCALATE" if escalate else "LOG_ROUTINE"
    reasons.append(
        f"{'Escalates' if escalate else 'Does not escalate'} to HSE Manager/Site Director "
        f"immediately, bypassing the normal review queue (HSE KB #2)"
    )
    return RuleResult(
        decision=decision,
        reasons=reasons,
        recommended_action="Escalate immediately and open a formal investigation." if escalate else "Log for routine HSE tracking.",
        metadata={"severity": severity, "regulatory_notification_required": regulatory_notification},
    )
