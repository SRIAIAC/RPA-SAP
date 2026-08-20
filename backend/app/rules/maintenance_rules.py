"""Maintenance rules — work order priority classification (Maintenance KB
#1) and duplicate work order prevention (Maintenance KB #3)."""

from app.rules.base import RuleResult

_PRIORITY_BY_SEVERITY = {"critical": "Emergency", "warning": "Urgent", "info": "Routine"}
_SLA_BY_PRIORITY = {
    "Emergency": "response within 1 hour",
    "Urgent": "response within 8 hours",
    "Routine": "scheduled within 5 business days",
}


def classify_work_order_priority(alert_severity: str) -> RuleResult:
    priority = _PRIORITY_BY_SEVERITY.get(alert_severity.lower(), "Routine")
    sla = _SLA_BY_PRIORITY[priority]
    return RuleResult(
        decision=priority,
        reasons=[f"Alert severity '{alert_severity}' mapped to {priority} priority — SLA: {sla} (Maintenance KB #1)"],
        recommended_action=f"Create a {priority} work order — {sla}.",
    )


def check_duplicate_work_order(existing_open_notification: bool) -> RuleResult:
    if existing_open_notification:
        return RuleResult(
            decision="APPEND_NOTE",
            reasons=["An open notification/work order already exists for this equipment within the last 72 hours (Maintenance KB #3)"],
            recommended_action="Append this alert as a note on the existing work order rather than creating a duplicate.",
        )
    return RuleResult(
        decision="CREATE_NEW",
        reasons=["No open notification found for this equipment in the last 72 hours"],
        recommended_action="Create a new maintenance notification.",
    )
