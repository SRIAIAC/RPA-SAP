// Per-workflow manual-entry field specs, keyed by Workflow.key. Drives the
// "Enter manually" form on the Dashboard/Workflow detail pages. Field
// `name`s must match what each backend recipe reads out of
// ctx.manual_input (see backend/app/workflow_engine/recipes/*.py).
//
// Every field is optional at the form layer: leaving one blank means "use
// the workflow's golden-fixture default", so a workflow stays runnable with
// zero input exactly like the old bare "Run now" button. A code/number
// typed here that doesn't exist in the mock SAP/non-SAP data correctly
// surfaces as a real "not found" exception from the recipe.

export type ManualFieldType = "text" | "number" | "textarea";

export interface ManualFieldSpec {
  name: string;
  label: string;
  type: ManualFieldType;
  placeholder?: string;
}

export const MANUAL_ENTRY_FIELDS: Record<string, ManualFieldSpec[]> = {
  PO_CREATE: [
    { name: "vendor_code", label: "Vendor code", type: "text", placeholder: "V-999001" },
    { name: "material_code", label: "Material code", type: "text", placeholder: "MAT-999001" },
    { name: "quantity", label: "Quantity", type: "number", placeholder: "10" },
  ],
  INV_MATCH: [
    { name: "invoice_number", label: "Invoice number", type: "text", placeholder: "INV-GOLDEN-01" },
    { name: "po_number", label: "PO number", type: "text", placeholder: "PO-GOLDEN-01" },
  ],
  VENDOR_ONBOARD: [{ name: "vendor_code", label: "Vendor code", type: "text", placeholder: "V-999001" }],
  MAINT_WO: [{ name: "equipment_id", label: "Equipment ID", type: "text", placeholder: "EQ-GOLDEN-PUMP-01" }],
  SPARE_REPLEN: [
    { name: "material_code", label: "Material code", type: "text", placeholder: "MAT-999001" },
    { name: "quantity", label: "Quantity to order", type: "number", placeholder: "50" },
  ],
  SHIFT_HANDOVER: [{ name: "shift_notes", label: "Shift notes (optional)", type: "textarea" }],
  EXPENSE_PROC: [
    { name: "employee_name", label: "Employee name", type: "text" },
    { name: "claim_amount", label: "Claim amount", type: "number" },
    { name: "expense_category", label: "Expense category", type: "text", placeholder: "Travel, meals, lodging…" },
  ],
  FUEL_RECON: [
    { name: "tank_quantity_bbl", label: "Tank reading (BBL)", type: "number" },
    { name: "sap_quantity_bbl", label: "SAP inventory balance (BBL)", type: "number" },
  ],
  CONTRACT_EXPIRY: [{ name: "contract_number", label: "Contract number", type: "text", placeholder: "CTR-GOLDEN-01" }],
  HSE_INCIDENT: [
    { name: "description", label: "Incident description", type: "textarea", placeholder: "Describe what happened…" },
    { name: "equipment_id", label: "Equipment ID (optional)", type: "text", placeholder: "EQ-GOLDEN-PUMP-01" },
    { name: "location", label: "Location", type: "text", placeholder: "PetroNova Refinery Alpha" },
  ],
  COMPLIANCE_DOC: [{ name: "vendor_id", label: "Vendor ID filter (optional)", type: "text" }],
  ENV_COMPLIANCE: [{ name: "reporting_period", label: "Reporting period (optional)", type: "text", placeholder: "Q1 2026" }],
  PROD_REPORT: [{ name: "production_order_number", label: "Production order number", type: "text", placeholder: "PORD-GOLDEN-01" }],
  CRUDE_RECON: [{ name: "po_number", label: "PO number", type: "text", placeholder: "PO-GOLDEN-CRUDE" }],
  SALES_ORDER: [{ name: "customer_code", label: "Customer code", type: "text", placeholder: "C-700001" }],
};
