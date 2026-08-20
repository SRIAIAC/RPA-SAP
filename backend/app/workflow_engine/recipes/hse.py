"""HSE recipes. HSE_INCIDENT is the rich tier and the AI-classification
golden scenario: incident description -> AI severity classification ->
rules-based escalation decision -> SAP EHS record."""

from app.rules.hse_rules import evaluate_hse_incident
from app.workflow_engine.recipe_context import RecipeContext, RecipeOutcome

GOLDEN_EQUIPMENT_ID = "EQ-GOLDEN-PUMP-01"

INCIDENT_SCENARIOS = {
    "critical": "Fire reported near the process unit at PetroNova Refinery Alpha, extinguished quickly by the site fire team, no injuries reported.",
    "low": "Routine safety walkthrough completed at PetroNova Refinery Alpha, no issues identified.",
}


def hse_incident(ctx: RecipeContext) -> RecipeOutcome:
    mi = ctx.manual_input or {}
    manual_description = (mi.get("description") or "").strip()
    description = manual_description or INCIDENT_SCENARIOS.get(ctx.scenario or "critical", INCIDENT_SCENARIOS["critical"])
    equipment_id = (mi.get("equipment_id") or "").strip() or GOLDEN_EQUIPMENT_ID
    location = (mi.get("location") or "").strip() or "PetroNova Refinery Alpha"

    ctx.record_step("Capture incident report from mobile app", detail={"description": description})

    ai_result, _ = ctx.ai.classify_hse_incident(description)
    ctx.record_step("AI classification of incident severity", detail=ai_result)

    equipment = ctx.sap.get_equipment(equipment_id)
    ctx.record_step(
        "Identify affected location/equipment",
        detail={"equipment": equipment["description"] if equipment else None, "found_in_asset_master": equipment is not None},
    )

    incident = ctx.sap.create_hse_incident(
        {"description": description, "severity": ai_result["classification"], "location": location, "equipment_id": equipment_id}
    )
    ctx.record_step("Create incident record in SAP EHS", detail={"incident_number": incident["incident_number"]})

    rules_result = evaluate_hse_incident(ai_severity=ai_result["classification"])
    if rules_result.decision == "AUTO_ESCALATE":
        return RecipeOutcome(
            "Exception",
            f"Exception raised: {rules_result.recommended_action}",
            "High-severity incident requires immediate escalation",
        )

    email = ctx.rpa.send_email(to="hse-manager@petronova.example", subject=f"Incident {incident['incident_number']} logged", body="Routine severity — logged for tracking.")
    ctx.record_step("Notify HSE manager", detail=email)
    ctx.record_step("Open investigation workflow", detail={"assigned_to": "Area Supervisor"})
    return RecipeOutcome("Completed", f"Completed successfully — incident {incident['incident_number']} logged at {ai_result['classification']} severity.")


def compliance_doc(ctx: RecipeContext) -> RecipeOutcome:
    mi = ctx.manual_input or {}
    vendor_id = (mi.get("vendor_id") or "").strip() or None
    documents = ctx.nonsap.list_documents(vendor_id=vendor_id) if vendor_id else ctx.nonsap.list_documents()
    pending = [d for d in documents if d["status"] == "Pending"]
    ctx.record_step("Identify vendors/employees with missing certificates", detail={"pending_documents": len(pending)})

    email = ctx.rpa.send_email(to="compliance-tracking@petronova.example", subject="Missing document reminder", body=f"{len(pending)} document(s) pending submission.")
    ctx.record_step("Auto-request documents via email", detail=email)

    ctx.record_step("Validate received documents", detail={"approved": len([d for d in documents if d["status"] == "Approved"])})
    ctx.record_step("Update compliance records in SAP")

    notify = ctx.rpa.send_email(to="hse-manager@petronova.example", subject="Outstanding compliance items", body=f"{len(pending)} item(s) still outstanding.")
    ctx.record_step("Notify HSE of outstanding items", detail=notify)
    return RecipeOutcome("Completed", f"Completed successfully — {len(pending)} outstanding compliance document(s) tracked, reminders sent.")


def env_compliance(ctx: RecipeContext) -> RecipeOutcome:
    # Reuses LIMS test results as the stand-in monitoring-station dataset —
    # no dedicated emissions-sensor model exists in this demo; the pass/fail
    # signal is real (from mock-non-sap), just borrowed from an adjacent
    # subsystem rather than a purpose-built one.
    mi = ctx.manual_input or {}
    reporting_period = (mi.get("reporting_period") or "").strip() or None

    results = ctx.nonsap.list_test_results()
    ctx.record_step("Collect emissions data from monitoring stations", detail={"readings_collected": len(results), "reporting_period": reporting_period})

    failures = [r for r in results if r["pass_fail"] == "Fail"]
    ctx.record_step("Compare against regulatory thresholds", detail={"non_conformances": len(failures)})

    if failures:
        return RecipeOutcome(
            "Exception",
            f"Exception raised: {len(failures)} reading(s) exceed regulatory threshold — non-conformance requires regulator notification",
            "Emissions reading exceeds regulatory limit",
        )

    ctx.record_step("Consolidate compliance report")
    portal = ctx.rpa.interact_portal("Regulator Portal", "submit_report", {"readings": len(results)})
    ctx.record_step("Submit report to regulator portal", detail=portal)
    ctx.record_step("Archive report in SAP EHS")
    return RecipeOutcome("Completed", "Completed successfully — emissions compliance report submitted, no non-conformances.")
