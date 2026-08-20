"""Production rules — daily variance anomaly thresholds (Production KB #1)
and crude oil receipt reconciliation custody-transfer tolerance
(Production KB #4)."""

from app.rules.base import RuleResult

VARIANCE_ANOMALY_FLAG_PCT = 5.0  # Production KB #1
VARIANCE_CRITICAL_PCT = 10.0  # Production KB #1

CRUDE_AUTO_CLOSE_PCT = 0.3  # Production KB #4: industry-standard custody transfer tolerance
CRUDE_SENIOR_SIGNOFF_PCT = 0.5  # Production KB #4


def evaluate_production_variance(planned: float, actual: float) -> RuleResult:
    variance_pct = (abs(planned - actual) / planned * 100) if planned else 0.0
    if variance_pct > VARIANCE_CRITICAL_PCT:
        decision = "CRITICAL_ANOMALY"
        action = "Same-shift notification to the Production Department Head (Production KB #1)."
    elif variance_pct > VARIANCE_ANOMALY_FLAG_PCT:
        decision = "ANOMALY_FLAG"
        action = "Automatic anomaly flag raised (Production KB #1)."
    else:
        decision = "NORMAL"
        action = "No action required."
    return RuleResult(
        decision=decision,
        reasons=[f"Actual vs. planned variance {variance_pct:.2f}% (Production KB #1)"],
        recommended_action=action,
        metadata={"variance_pct": round(variance_pct, 2)},
    )


def evaluate_crude_reconciliation(terminal_qty: float, tank_qty: float, sap_qty: float) -> RuleResult:
    """Compares Terminal Management System and Tank Farm readings against the
    SAP MM receipt quantity (the system-of-record figure financial posting
    keys off), taking the larger of the two variances as the governing one."""
    if not sap_qty:
        return RuleResult(
            decision="HARD_EXCEPTION",
            reasons=["SAP receipt quantity is zero/unavailable — cannot reconcile"],
            recommended_action="Joint measurement review required with the terminal operator.",
        )
    terminal_variance_pct = abs(terminal_qty - sap_qty) / sap_qty * 100
    tank_variance_pct = abs(tank_qty - sap_qty) / sap_qty * 100
    max_variance_pct = max(terminal_variance_pct, tank_variance_pct)

    if max_variance_pct <= CRUDE_AUTO_CLOSE_PCT:
        decision = "AUTO_CLOSE"
        action = "Auto-close reconciliation — within custody transfer tolerance (Production KB #4)."
    elif max_variance_pct <= CRUDE_SENIOR_SIGNOFF_PCT:
        decision = "SENIOR_MANAGER_SIGNOFF"
        action = "Requires Senior Manager sign-off (Production KB #4)."
    else:
        decision = "HARD_EXCEPTION"
        action = "Joint measurement review required with the terminal operator (Production KB #4)."

    return RuleResult(
        decision=decision,
        reasons=[
            f"Max variance vs. SAP receipt quantity: {max_variance_pct:.3f}% "
            f"(Terminal {terminal_variance_pct:.3f}%, Tank Farm {tank_variance_pct:.3f}%) (Production KB #4)"
        ],
        recommended_action=action,
        metadata={"variance_pct": round(max_variance_pct, 3)},
    )
