"""Business Rules Engine — deterministic decisions, thresholds traceable to
app/knowledge_base/*.md. The five invoice scenarios here are exactly the
"golden demo scenarios" from the platform spec (auto-approve / quantity
mismatch / price mismatch / duplicate invoice / missing GRN)."""

from datetime import date, timedelta

from app.models import Level
from app.rules.authorization_rules import evaluate_exception_action_authorization
from app.rules.contract_rules import evaluate_contract_expiry
from app.rules.hse_rules import evaluate_hse_incident
from app.rules.invoice_rules import evaluate_three_way_match
from app.rules.maintenance_rules import check_duplicate_work_order, classify_work_order_priority
from app.rules.procurement_rules import evaluate_po_approval, evaluate_vendor_blocked
from app.rules.production_rules import evaluate_crude_reconciliation, evaluate_production_variance
from app.rules.vendor_compliance_rules import evaluate_vendor_compliance


# --- Invoice 3-way match: the 5 golden scenarios -----------------------------
def test_invoice_scenario_1_auto_approve():
    result = evaluate_three_way_match(
        po_quantity=100, grn_quantity=100, invoice_quantity=100,
        po_unit_price=125000, invoice_unit_price=125000,
        is_duplicate=False, grn_exists=True,
    )
    assert result.decision == "AUTO_APPROVE"


def test_invoice_scenario_2_quantity_mismatch():
    result = evaluate_three_way_match(
        po_quantity=100, grn_quantity=95, invoice_quantity=100,
        po_unit_price=125000, invoice_unit_price=125000,
        is_duplicate=False, grn_exists=True,
    )
    assert result.decision == "QUANTITY_MISMATCH"


def test_invoice_scenario_3_price_mismatch():
    result = evaluate_three_way_match(
        po_quantity=100, grn_quantity=100, invoice_quantity=100,
        po_unit_price=125000, invoice_unit_price=140000,
        is_duplicate=False, grn_exists=True,
    )
    assert result.decision == "PRICE_MISMATCH"


def test_invoice_scenario_4_duplicate_invoice():
    result = evaluate_three_way_match(
        po_quantity=100, grn_quantity=100, invoice_quantity=100,
        po_unit_price=125000, invoice_unit_price=125000,
        is_duplicate=True, grn_exists=True,
    )
    assert result.decision == "DUPLICATE_INVOICE"


def test_invoice_scenario_5_missing_grn():
    result = evaluate_three_way_match(
        po_quantity=100, grn_quantity=None, invoice_quantity=100,
        po_unit_price=125000, invoice_unit_price=125000,
        is_duplicate=False, grn_exists=False,
    )
    assert result.decision == "MISSING_GRN"


def test_invoice_qty_within_tolerance_still_auto_approves():
    # 2% of 100 = 2 units, which is smaller than the flat 5-unit cap.
    result = evaluate_three_way_match(
        po_quantity=100, grn_quantity=100, invoice_quantity=101,
        po_unit_price=100000, invoice_unit_price=100000,
        is_duplicate=False, grn_exists=True,
    )
    assert result.decision == "AUTO_APPROVE"


# --- Procurement -------------------------------------------------------------
def test_po_approval_within_manager_limit():
    assert evaluate_po_approval(150_000, "Manager").decision == "AUTO_APPROVE"


def test_po_approval_exceeds_manager_limit_escalates():
    assert evaluate_po_approval(250_000, "Manager").decision == "ESCALATE"


def test_blocked_vendor_flagged():
    assert evaluate_vendor_blocked(True).decision == "BLOCKED_VENDOR"
    assert evaluate_vendor_blocked(False).decision == "OK"


# --- Vendor compliance --------------------------------------------------------
def test_vendor_compliance_expired_insurance():
    result = evaluate_vendor_compliance(
        insurance_expiry=date(2026, 1, 1), gst_number="27ABCDE1234F1Z5",
        is_duplicate_gst_or_bank=False, today=date(2026, 8, 19),
    )
    assert result.decision == "EXPIRED_INSURANCE"


def test_vendor_compliance_renewal_due():
    today = date(2026, 8, 19)
    result = evaluate_vendor_compliance(
        insurance_expiry=today + timedelta(days=10), gst_number="27ABCDE1234F1Z5",
        is_duplicate_gst_or_bank=False, today=today,
    )
    assert result.decision == "INSURANCE_RENEWAL_DUE"


def test_vendor_compliance_missing_kyc():
    today = date(2026, 8, 19)
    result = evaluate_vendor_compliance(
        insurance_expiry=today + timedelta(days=365), gst_number=None,
        is_duplicate_gst_or_bank=False, today=today,
    )
    assert result.decision == "MISSING_KYC"


def test_vendor_compliance_compliant():
    today = date(2026, 8, 19)
    result = evaluate_vendor_compliance(
        insurance_expiry=today + timedelta(days=365), gst_number="27ABCDE1234F1Z5",
        is_duplicate_gst_or_bank=False, today=today,
    )
    assert result.decision == "COMPLIANT"


# --- Maintenance ---------------------------------------------------------------
def test_maintenance_priority_mapping():
    assert classify_work_order_priority("critical").decision == "Emergency"
    assert classify_work_order_priority("warning").decision == "Urgent"
    assert classify_work_order_priority("info").decision == "Routine"


def test_maintenance_duplicate_work_order():
    assert check_duplicate_work_order(True).decision == "APPEND_NOTE"
    assert check_duplicate_work_order(False).decision == "CREATE_NEW"


# --- HSE -------------------------------------------------------------------------
def test_hse_high_severity_auto_escalates():
    assert evaluate_hse_incident("High").decision == "AUTO_ESCALATE"


def test_hse_low_severity_logs_routine():
    assert evaluate_hse_incident("Low").decision == "LOG_ROUTINE"


def test_hse_large_spill_forces_escalation_even_if_ai_said_low():
    result = evaluate_hse_incident("Low", spill_volume_liters=500)
    assert result.decision == "AUTO_ESCALATE"
    assert result.metadata["regulatory_notification_required"] is True


# --- Production ------------------------------------------------------------------
def test_production_variance_critical():
    result = evaluate_production_variance(planned=1000, actual=850)
    assert result.decision == "CRITICAL_ANOMALY"
    assert result.metadata["variance_pct"] == 15.0


def test_production_variance_normal():
    result = evaluate_production_variance(planned=1000, actual=980)
    assert result.decision == "NORMAL"


def test_crude_reconciliation_auto_close():
    result = evaluate_crude_reconciliation(terminal_qty=10000, tank_qty=10005, sap_qty=10002)
    assert result.decision == "AUTO_CLOSE"


def test_crude_reconciliation_hard_exception():
    result = evaluate_crude_reconciliation(terminal_qty=9800, tank_qty=10000, sap_qty=10000)
    assert result.decision == "HARD_EXCEPTION"


# --- Contract --------------------------------------------------------------------
def test_contract_no_owner_escalates_immediately():
    assert evaluate_contract_expiry(days_remaining=200, has_owner=False).decision == "ESCALATE_NO_OWNER"


def test_contract_within_renewal_window():
    assert evaluate_contract_expiry(days_remaining=15, has_owner=True).decision == "RENEWAL_REVIEW"


def test_contract_outside_renewal_window():
    assert evaluate_contract_expiry(days_remaining=200, has_owner=True).decision == "NO_ACTION"


# --- Authorization -----------------------------------------------------------------
def test_manager_can_retry_but_not_approve():
    assert evaluate_exception_action_authorization(Level.MANAGER, "retry").decision == "AUTHORIZED"
    assert evaluate_exception_action_authorization(Level.MANAGER, "approve").decision == "UNAUTHORIZED"


def test_senior_manager_can_approve():
    assert evaluate_exception_action_authorization(Level.SENIOR_MANAGER, "approve").decision == "AUTHORIZED"
