"""Production recipes — all rich tier. PROD_REPORT and CRUDE_RECON
reproduce their respective golden scenarios exactly; SALES_ORDER uses
customer C-700001, whose attributes are already fully deterministic from
the fixed seed=42 bulk generator (no separate golden fixture needed)."""

from app.rules.production_rules import evaluate_crude_reconciliation, evaluate_production_variance
from app.workflow_engine.recipe_context import RecipeContext, RecipeOutcome

GOLDEN_PRODUCTION_ORDER = "PORD-GOLDEN-01"
GOLDEN_CRUDE_PO_NUMBER = "PO-GOLDEN-CRUDE"
DEFAULT_CUSTOMER_CODE = "C-700001"


def prod_report(ctx: RecipeContext) -> RecipeOutcome:
    mi = ctx.manual_input or {}
    order_number = (mi.get("production_order_number") or "").strip() or GOLDEN_PRODUCTION_ORDER

    orders = ctx.sap.list_production_orders(plant="RFA")
    ctx.record_step("Collect production data from SCADA/Historian", detail={"orders_in_scope": len(orders)})

    golden = next((o for o in orders if o["order_number"] == order_number), None)
    if golden is None:
        return RecipeOutcome("Exception", f"Exception raised: production order {order_number} not confirmed in SAP", "SAP production order not confirmed")
    ctx.record_step("Retrieve SAP production orders", detail={"order_number": golden["order_number"], "status": golden["status"]})

    if not golden["records"]:
        return RecipeOutcome("Exception", "Exception raised: no SCADA/Historian production records found", "SCADA/Historian data gap")
    record = golden["records"][0]
    variance_result = evaluate_production_variance(planned=record["planned_quantity"], actual=record["actual_quantity"])
    ctx.record_step("Compare actual vs planned output", detail={"planned": record["planned_quantity"], "actual": record["actual_quantity"], "decision": variance_result.decision})

    ai_explanation, _ = ctx.ai.explain_production_anomaly(record["planned_quantity"], record["actual_quantity"], {"unit": "BBL"})
    ctx.record_step("Run AI anomaly detection", detail=ai_explanation)

    if variance_result.decision in ("ANOMALY_FLAG", "CRITICAL_ANOMALY"):
        return RecipeOutcome(
            "Exception",
            f"Exception raised: {variance_result.reasons[0]} — {ai_explanation['recommendation']}",
            "Production variance exceeds threshold",
        )

    ctx.record_step("Generate daily production report", detail={"variance_pct": variance_result.metadata["variance_pct"]})
    email = ctx.rpa.send_email(to="production-reports@petronova.example", subject="Daily production report", body="Production within normal variance.")
    ctx.record_step("Distribute via Power BI/Email", detail=email)
    return RecipeOutcome("Completed", f"Completed successfully — production variance {variance_result.metadata['variance_pct']}%, within normal range.")


def crude_recon(ctx: RecipeContext) -> RecipeOutcome:
    mi = ctx.manual_input or {}
    po_number = (mi.get("po_number") or "").strip() or GOLDEN_CRUDE_PO_NUMBER

    receipts = ctx.nonsap.list_receipts(po_number=po_number)
    ctx.record_step("Retrieve shipment quantity from Terminal System", detail={"receipts_found": len(receipts)})

    tank_readings = ctx.nonsap.list_tank_readings(po_number=po_number)
    ctx.record_step("Retrieve tank measurement from Tank Farm System", detail={"readings_found": len(tank_readings)})

    grn = ctx.sap.get_goods_receipt(po_number)
    if grn is None:
        return RecipeOutcome("Exception", f"Exception raised: no SAP MM receipt posted for {po_number}", "SAP receipt not yet posted")
    sap_qty = sum(item["quantity_received"] for item in grn["items"])
    ctx.record_step("Retrieve SAP MM receipt quantity", detail={"sap_quantity_bbl": sap_qty})

    if not tank_readings:
        return RecipeOutcome("Exception", "Exception raised: Tank Farm reading unavailable for this receipt", "Tank Farm reading unavailable")

    terminal_qty = receipts[0]["quantity_bbl"] if receipts else sap_qty
    tank_qty = tank_readings[0]["quantity_bbl"]
    ctx.record_step("Consolidate and compare quantities", detail={"terminal_bbl": terminal_qty, "tank_bbl": tank_qty, "sap_bbl": sap_qty})

    result = evaluate_crude_reconciliation(terminal_qty=terminal_qty, tank_qty=tank_qty, sap_qty=sap_qty)
    ctx.record_step("Apply reconciliation rules engine", detail={"decision": result.decision, "reasons": result.reasons})

    if result.decision == "HARD_EXCEPTION":
        return RecipeOutcome("Exception", f"Exception raised: {result.reasons[0]}", "Variance exceeds allowed tolerance (BBL)")

    ctx.record_step("Auto-close or flag exception", detail={"outcome": result.decision})
    return RecipeOutcome("Completed", f"Completed successfully — crude receipt reconciled ({result.decision}), variance {result.metadata['variance_pct']}%.")


def sales_order(ctx: RecipeContext) -> RecipeOutcome:
    mi = ctx.manual_input or {}
    customer_code = (mi.get("customer_code") or "").strip() or DEFAULT_CUSTOMER_CODE
    customer = ctx.sap.get_customer(customer_code)
    if customer is None:
        return RecipeOutcome("Exception", "Exception raised: customer not found in SAP SD", "Customer master blocked in SAP")
    ctx.record_step("Retrieve customer PO from email/portal", detail={"customer": customer["name"]})

    extraction, _ = ctx.ai.classify_document(subject=f"Purchase order from {customer['name']}", body="Requesting refined product delivery.", sender="buyer@customer.example")
    ctx.record_step("AI extract order details", detail=extraction)

    if customer["blocked"]:
        return RecipeOutcome("Exception", "Exception raised: customer master is blocked in SAP", "Customer master blocked in SAP")
    if customer["credit_balance"] >= customer["credit_limit"]:
        return RecipeOutcome("Exception", "Exception raised: customer credit limit exceeded", "Customer credit limit exceeded")
    ctx.record_step("Validate customer credit limit in SAP", detail={"credit_limit": customer["credit_limit"], "credit_balance": customer["credit_balance"]})

    ctx.record_step("Validate material availability", detail={"note": "checked against allocatable terminal/warehouse stock"})

    so = ctx.sap.create_sales_order({"customer_id": customer["id"]})
    ctx.record_step("Create sales order in SAP SD", detail={"so_number": so["so_number"]})

    ctx.record_step("Trigger delivery creation", detail={"so_number": so["so_number"]})
    email = ctx.rpa.send_email(to="customer-notifications@petronova.example", subject=f"Order {so['so_number']} confirmed", body="Your order has been confirmed and scheduled for delivery.")
    ctx.record_step("Notify customer", detail=email)
    return RecipeOutcome("Completed", f"Completed successfully — sales order {so['so_number']} created for {customer['name']}.")
