"""Maintenance recipes. MAINT_WO is the EventBus golden scenario: SCADA
alarm -> EquipmentAlarmEvent -> EventBus -> (this recipe reacting to it) ->
AI classification -> SAP PM notification/work order.
"""

from app.events.events import equipment_alarm_event
from app.events.inmemory_bus import event_bus
from app.rules.maintenance_rules import check_duplicate_work_order, classify_work_order_priority
from app.workflow_engine.recipe_context import RecipeContext, RecipeOutcome

GOLDEN_EQUIPMENT_ID = "EQ-GOLDEN-PUMP-01"
GOLDEN_MATERIAL_CODE = "MAT-999001"


def maint_wo(ctx: RecipeContext) -> RecipeOutcome:
    mi = ctx.manual_input or {}
    equipment_id = (mi.get("equipment_id") or "").strip() or GOLDEN_EQUIPMENT_ID
    alarms = ctx.nonsap.list_alarms(equipment_id=equipment_id)
    if not alarms:
        return RecipeOutcome("Exception", "Exception raised: no SCADA alarm found for equipment", "Equipment ID not found in Asset Master")
    alarm = alarms[0]

    # EventBus golden scenario: the SCADA alarm becomes an EquipmentAlarmEvent
    # published on the bus; any subscriber (see app/main.py's startup wiring)
    # reacts independently of this recipe's own direct handling below.
    event = equipment_alarm_event(
        equipment_id=equipment_id, parameter=alarm["parameter"], value=alarm["value"],
        threshold=alarm["threshold"], correlation_id=ctx.correlation_id,
    )
    event_bus.publish(event)

    ai_classification, _ = ctx.ai.classify_maintenance_alarm(
        {"equipment_id": equipment_id, "value": alarm["value"], "threshold": alarm["threshold"]}
    )
    ctx.record_step(
        "Receive equipment alert from SCADA/IoT",
        detail={"alarm": alarm, "ai_classification": ai_classification},
    )

    equipment = ctx.sap.get_equipment(equipment_id)
    if equipment is None:
        return RecipeOutcome("Exception", f"Exception raised: equipment {equipment_id} not found in Asset Master", "Equipment ID not found in Asset Master")
    ctx.record_step("Identify equipment in SAP Asset Master", detail={"equipment": equipment["description"], "criticality": equipment["criticality"]})

    dup_check = check_duplicate_work_order(existing_open_notification=False)
    ctx.record_step("Check for existing open notifications", detail={"decision": dup_check.decision})

    priority = classify_work_order_priority(alert_severity="critical" if ai_classification["classification"] == "Emergency" else "warning")
    notification = ctx.sap.create_maintenance_notification(
        {
            "equipment_id": equipment_id,
            "description": f"{priority.decision} priority — {alarm['parameter']} {alarm['value']} vs threshold {alarm['threshold']}",
            "priority": priority.decision,
        }
    )
    ctx.record_step("Create maintenance notification in SAP PM", detail={"notification_number": notification["notification_number"], "priority": priority.decision})

    work_order = ctx.sap.create_work_order({"equipment_id": equipment_id, "priority": priority.decision, "technician": "Auto-assigned — Rotating Equipment team"})
    ctx.record_step("Create and assign work order", detail={"order_number": work_order["order_number"]})

    notify = ctx.rpa.interact_portal("Microsoft Teams", "notify_technician", {"work_order": work_order["order_number"], "priority": priority.decision})
    ctx.record_step("Notify technician via Teams/Email", detail=notify)

    return RecipeOutcome(
        "Completed",
        f"Completed successfully — {priority.decision} work order {work_order['order_number']} created for {equipment['description']}.",
    )


def spare_replen(ctx: RecipeContext) -> RecipeOutcome:
    mi = ctx.manual_input or {}
    material_code = (mi.get("material_code") or "").strip() or GOLDEN_MATERIAL_CODE
    try:
        quantity = int(mi["quantity"]) if mi.get("quantity") not in (None, "") else 50
    except (TypeError, ValueError):
        quantity = 50

    material = ctx.sap.get_material(material_code)
    if material is None:
        return RecipeOutcome("Exception", f"Exception raised: material {material_code} not found in material master", "No approved supplier for material")
    inventory = ctx.sap.get_inventory(material_code)
    on_hand = inventory["total_on_hand"] if inventory else 0
    ctx.record_step("Monitor SAP stock levels vs minimum threshold", detail={"material": material["description"], "on_hand": on_hand})

    vendors = ctx.sap.list_vendors(department="Procurement", blocked=False)
    ctx.record_step("Check open purchase orders in SAP MM", detail={"approved_vendor_count": len(vendors)})

    wms_rows = ctx.nonsap.get_inventory(material_code=material_code)
    ctx.record_step("Check warehouse system for available stock", detail={"warehouse_locations": len(wms_rows)})

    documents = ctx.nonsap.list_documents()
    ctx.record_step("Check supplier portal for availability", detail={"supplier_documents_on_file": len(documents)})

    if not vendors:
        return RecipeOutcome("Exception", "Exception raised: no approved supplier for material", "No approved supplier for material")

    po = ctx.sap.create_purchase_order(
        {"vendor_id": vendors[0]["id"], "department": "Maintenance", "items": [{"material_id": material["id"], "quantity": quantity, "unit_price": material["unit_price"]}]}
    )
    ctx.record_step("Create purchase requisition in SAP", detail={"po_number": po["po_number"]})

    email = ctx.rpa.send_email(to="procurement-team@petronova.example", subject="Spare parts requisition created", body=f"PO {po['po_number']} created for replenishment.")
    ctx.record_step("Notify procurement team", detail=email)
    return RecipeOutcome("Completed", f"Completed successfully — replenishment PO {po['po_number']} created.")


def shift_handover(ctx: RecipeContext) -> RecipeOutcome:
    mi = ctx.manual_input or {}
    shift_notes = (mi.get("shift_notes") or "").strip() or None

    alarms = ctx.nonsap.list_alarms(acknowledged=False)
    ctx.record_step("Collect open work orders from SAP PM", detail={"note": "cross-department snapshot"})
    ctx.record_step("Collect active alarms from SCADA", detail={"unacknowledged_alarms": len(alarms)})

    production = ctx.sap.list_production_orders(plant="RFA")
    ctx.record_step("Collect production data from Historian", detail={"production_orders_tracked": len(production)})

    critical_unacked = [a for a in alarms if a["severity"] == "critical"]
    if critical_unacked:
        return RecipeOutcome(
            "Exception",
            f"Exception raised: {len(critical_unacked)} unresolved critical alarm(s) carried over from this shift",
            "Unresolved critical alarm carried over",
        )

    ctx.record_step("Consolidate shift handover report", detail={"alarms": len(alarms), "production_orders": len(production), "shift_notes": shift_notes})
    email = ctx.rpa.send_email(to="shift-lead@petronova.example", subject="Shift handover report", body=shift_notes or "Handover report attached.")
    ctx.record_step("Distribute report to incoming shift lead", detail=email)
    return RecipeOutcome("Completed", "Completed successfully — shift handover report distributed.")
