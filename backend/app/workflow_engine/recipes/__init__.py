"""RECIPES: workflow.key -> recipe function lookup table used by
SimulatedWorkflowEngine. Every one of the 15 seeded workflows resolves to a
real recipe here — either "rich" (bespoke, multi-record business logic) or
"generic" (still calls real mock endpoints per step, still rule-driven, but
without bespoke reconciliation depth). Any future workflow key not present
here falls back to generic_fallback.run, so the engine never breaks on an
unrecognized key.
"""

from typing import Callable

from app.workflow_engine.recipe_context import RecipeContext, RecipeOutcome
from app.workflow_engine.recipes import finance, hse, maintenance, procurement, production

RECIPES: dict[str, Callable[[RecipeContext], RecipeOutcome]] = {
    # Procurement (rich)
    "PO_CREATE": procurement.po_create,
    "INV_MATCH": procurement.inv_match,
    "VENDOR_ONBOARD": procurement.vendor_onboard,
    # Maintenance
    "MAINT_WO": maintenance.maint_wo,
    "SPARE_REPLEN": maintenance.spare_replen,
    "SHIFT_HANDOVER": maintenance.shift_handover,
    # Finance
    "EXPENSE_PROC": finance.expense_proc,
    "FUEL_RECON": finance.fuel_recon,
    "CONTRACT_EXPIRY": finance.contract_expiry,
    # HSE
    "HSE_INCIDENT": hse.hse_incident,
    "COMPLIANCE_DOC": hse.compliance_doc,
    "ENV_COMPLIANCE": hse.env_compliance,
    # Production
    "PROD_REPORT": production.prod_report,
    "CRUDE_RECON": production.crude_recon,
    "SALES_ORDER": production.sales_order,
}
