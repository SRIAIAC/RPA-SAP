"""Procurement recipes — the richest tier. INV_MATCH reproduces all 5
golden invoice scenarios (auto-approve / quantity mismatch / price mismatch
/ duplicate invoice / missing GRN) from the platform spec, selected via
ctx.scenario (defaults to "success" for a normal Dashboard "Run now" click;
Demo Scenarios, Phase 10, will pass the others explicitly).
"""

from app.rules.invoice_rules import evaluate_three_way_match
from app.rules.procurement_rules import evaluate_po_approval, evaluate_vendor_blocked
from app.rules.vendor_compliance_rules import evaluate_vendor_compliance
from app.workflow_engine.recipe_context import RecipeContext, RecipeOutcome

GOLDEN_VENDOR_CODE = "V-999001"
GOLDEN_MATERIAL_CODE = "MAT-999001"
GOLDEN_EXPIRED_VENDOR_CODE = "V-999002"

INVOICE_SCENARIOS = {
    "success": ("INV-GOLDEN-01", "PO-GOLDEN-01", False),
    "quantity_mismatch": ("INV-GOLDEN-02", "PO-GOLDEN-02", False),
    "price_mismatch": ("INV-GOLDEN-03", "PO-GOLDEN-03", False),
    "duplicate_invoice": ("INV-GOLDEN-01", "PO-GOLDEN-01", True),
    "missing_grn": ("INV-GOLDEN-05", "PO-GOLDEN-05", False),
}

_DECISION_REASON = {
    "QUANTITY_MISMATCH": "Quantity mismatch between GRN and invoice",
    "PRICE_MISMATCH": "Price variance beyond tolerance",
    "DUPLICATE_INVOICE": "Duplicate invoice detected",
    "MISSING_GRN": "Missing GRN — invoice exists but goods receipt not yet posted",
}


def po_create(ctx: RecipeContext) -> RecipeOutcome:
    mi = ctx.manual_input or {}
    vendor_code = (mi.get("vendor_code") or "").strip() or GOLDEN_VENDOR_CODE
    material_code = (mi.get("material_code") or "").strip() or GOLDEN_MATERIAL_CODE
    try:
        quantity = int(mi["quantity"]) if mi.get("quantity") not in (None, "") else 10
    except (TypeError, ValueError):
        quantity = 10

    ctx.record_step(
        "Read approved purchase request",
        detail={"vendor_code": vendor_code, "material_code": material_code, "quantity": quantity},
    )

    vendor = ctx.sap.get_vendor(vendor_code)
    if vendor is None:
        return RecipeOutcome("Exception", f"Exception raised: vendor {vendor_code} not found in SAP", "Vendor blocked in SAP")
    blocked_check = evaluate_vendor_blocked(vendor["blocked"])
    ctx.record_step("Validate vendor master in SAP", detail={"vendor": vendor["name"], "decision": blocked_check.decision})
    if blocked_check.decision == "BLOCKED_VENDOR":
        return RecipeOutcome("Exception", f"Exception raised: {blocked_check.recommended_action}", "Vendor blocked in SAP")

    material = ctx.sap.get_material(material_code)
    if material is None:
        return RecipeOutcome("Exception", f"Exception raised: material {material_code} not found in material master", "Material not found in material master")
    ctx.record_step("Validate material master in SAP", detail={"material": material["description"]})

    approval = evaluate_po_approval(quantity * material["unit_price"], "Manager")
    if approval.decision == "ESCALATE":
        return RecipeOutcome("Exception", f"Exception raised: {approval.recommended_action}", "Budget exceeds cost center limit")

    po = ctx.sap.create_purchase_order(
        {
            "vendor_id": vendor["id"], "department": "Procurement",
            "items": [{"material_id": material["id"], "quantity": quantity, "unit_price": material["unit_price"]}],
        }
    )
    ctx.record_step("Create Purchase Order in SAP MM", detail={"po_number": po["po_number"]})

    email = ctx.rpa.send_email(to=f"sales@{vendor['name'].split()[0].lower()}.example", subject=f"PO {po['po_number']} issued", body="Please confirm receipt of this purchase order.")
    ctx.record_step("Email PO to supplier", detail=email)

    ctx.record_step("Log confirmation in tracker", detail={"po_number": po["po_number"]})
    return RecipeOutcome("Completed", f"Completed successfully — PO {po['po_number']} created for {vendor['name']}.")


def inv_match(ctx: RecipeContext) -> RecipeOutcome:
    mi = ctx.manual_input or {}
    manual_invoice_number = (mi.get("invoice_number") or "").strip()
    manual_po_number = (mi.get("po_number") or "").strip()
    if manual_invoice_number or manual_po_number:
        scenario = ctx.scenario if ctx.scenario in INVOICE_SCENARIOS else "success"
        default_invoice_number, default_po_number, _ = INVOICE_SCENARIOS[scenario]
        invoice_number = manual_invoice_number or default_invoice_number
        po_number = manual_po_number or default_po_number
        # Real duplicate-invoice detection is out of scope for this mock
        # pipeline — that path is only reachable via the Demo Scenarios page.
        is_duplicate = False
    else:
        scenario = ctx.scenario if ctx.scenario in INVOICE_SCENARIOS else "success"
        invoice_number, po_number, is_duplicate = INVOICE_SCENARIOS[scenario]

    ctx.record_step("Retrieve invoice from email inbox", detail={"invoice_number": invoice_number})

    invoice = ctx.sap.get_invoice(invoice_number)
    extraction, _ = ctx.ai.extract_invoice(
        f"INVOICE\nInvoice Number: {invoice_number}\nPO Number: {po_number}\n"
        f"TOTAL: {invoice['total_amount'] if invoice else 0}"
    )
    ctx.record_step("OCR extract invoice fields", detail={"ai_extraction": extraction})

    po = ctx.sap.get_purchase_order(po_number)
    if po is None:
        return RecipeOutcome("Exception", f"Exception raised: PO {po_number} not found in SAP", "PO not found in SAP")
    ctx.record_step("Lookup PO in SAP MM", detail={"po_number": po_number, "line_items": len(po["items"])})

    grn = ctx.sap.get_goods_receipt(po_number)
    ctx.record_step("Lookup GRN in SAP MM", detail={"grn_found": grn is not None})

    if invoice is None:
        return RecipeOutcome("Exception", f"Exception raised: invoice {invoice_number} not found", "PO not found in SAP")

    po_item, grn_item, invoice_item = po["items"][0], (grn["items"][0] if grn else None), invoice["items"][0]
    match_result = evaluate_three_way_match(
        po_quantity=po_item["quantity"],
        grn_quantity=grn_item["quantity_received"] if grn_item else None,
        invoice_quantity=invoice_item["quantity"],
        po_unit_price=po_item["unit_price"],
        invoice_unit_price=invoice_item["unit_price"],
        is_duplicate=is_duplicate,
        grn_exists=grn is not None,
    )
    ctx.record_step("Perform 3-way match", detail={"decision": match_result.decision, "reasons": match_result.reasons})

    if match_result.decision != "AUTO_APPROVE":
        ai_explanation, _ = ctx.ai.explain_exception({"workflow_name": ctx.workflow.name, "reason": match_result.decision})
        reason = _DECISION_REASON.get(match_result.decision, match_result.decision)
        return RecipeOutcome("Exception", f"Exception raised: {reason} — {ai_explanation.get('recommendation', match_result.recommended_action)}", reason)

    ctx.record_step("Post invoice in SAP FI", detail={"invoice_number": invoice_number, "amount": invoice["total_amount"]})
    email = ctx.rpa.send_email(to="ap-team@petronova.example", subject=f"Invoice {invoice_number} posted", body="Auto-approved via 3-way match — within tolerance.")
    ctx.record_step("Notify AP team", detail=email)

    return RecipeOutcome("Completed", f"Completed successfully — invoice {invoice_number} matched PO {po_number} and posted to SAP FI.")


def vendor_onboard(ctx: RecipeContext) -> RecipeOutcome:
    mi = ctx.manual_input or {}
    manual_vendor_code = (mi.get("vendor_code") or "").strip()
    if manual_vendor_code:
        vendor_code = manual_vendor_code
    else:
        scenario = ctx.scenario if ctx.scenario in ("success", "expired_insurance") else "success"
        vendor_code = GOLDEN_EXPIRED_VENDOR_CODE if scenario == "expired_insurance" else GOLDEN_VENDOR_CODE

    documents = ctx.nonsap.list_documents(vendor_id=vendor_code)
    ctx.record_step("Collect vendor documents from portal", detail={"document_count": len(documents)})

    doc_text = "\n".join(f"{d['document_type']}: {d['filename']} ({d['status']})" for d in documents)
    extraction, _ = ctx.ai.extract_vendor_docs(doc_text or "No documents on file")
    ctx.record_step("OCR extract vendor details", detail={"ai_extraction": extraction})

    vendor = ctx.sap.get_vendor(vendor_code)
    if vendor is None:
        return RecipeOutcome("Exception", "Exception raised: vendor not found in SAP", "Duplicate vendor found in SAP")
    ctx.record_step("Run duplicate vendor check in SAP", detail={"vendor": vendor["name"]})

    from datetime import date as _date

    insurance_expiry = _date.fromisoformat(vendor["insurance_expiry"]) if vendor.get("insurance_expiry") else None
    compliance = evaluate_vendor_compliance(
        insurance_expiry=insurance_expiry, gst_number=vendor.get("gstin"), is_duplicate_gst_or_bank=False,
    )
    ctx.record_step("Validate KYC/compliance documents", detail={"decision": compliance.decision, "reasons": compliance.reasons})

    if compliance.decision in ("EXPIRED_INSURANCE", "MISSING_KYC", "DUPLICATE_VENDOR_FLAG"):
        reason_map = {
            "EXPIRED_INSURANCE": "Insurance certificate expired",
            "MISSING_KYC": "Missing GST/tax certificate",
            "DUPLICATE_VENDOR_FLAG": "Duplicate vendor found in SAP",
        }
        return RecipeOutcome("Exception", f"Exception raised: {compliance.recommended_action}", reason_map[compliance.decision])

    ctx.record_step("Create vendor master in SAP", detail={"vendor_code": vendor_code})
    ctx.record_step("Route to approval workflow", detail={"next_approver": "Department Head"})
    return RecipeOutcome("Completed", f"Completed successfully — vendor {vendor['name']} passed compliance and is routed for approval.")
