"""MockAIProvider: deterministic, explainable heuristic scorers standing in
for an LLM — no API key required, ever. Every method is a pure function of
its input (no randomness), so re-running the same scenario always produces
the same "AI" output — required for reproducible demo scenarios.

Two use cases reuse the repo's existing Mailroom heuristics instead of
reimplementing them:
  - extract_invoice()      -> app.services.ocr.extract_invoice_fields()
  - classify_document()    -> app.services.classifier.classify_message()
    (called via duck-typed SimpleNamespace stand-ins for MailMessage/
    MailAttachment, since classify_message only ever touches .subject/
    .body/.sender/.filename/.file_path — no SQLModel/DB dependency — so it
    works unmodified on arbitrary text without importing a DB session.)

The other six use cases (HSE, maintenance alarm, production anomaly,
contract clauses, exception explanation, vendor doc extraction) don't have
an existing analogue in the repo, so they're implemented here as new
deterministic regex/keyword heuristics, same spirit as the mailroom
classifier: bounded weighted signals with human-readable reasons.
"""

import os
import re
from types import SimpleNamespace
from typing import Any, Optional

from app.ai.base import AIProvider
from app.services import ocr as ocr_service
from app.services.classifier import classify_message

HSE_CRITICAL_KEYWORDS = [
    "fatality",
    "death",
    "explosion",
    "fire",
    "toxic release",
    "gas leak",
    "h2s",
    "amputation",
    "hospitalization",
]
HSE_HIGH_KEYWORDS = ["lost time injury", "serious injury", "medical treatment", "spill", "chemical exposure", "burn", "fracture"]
HSE_MEDIUM_KEYWORDS = ["near miss", "minor injury", "first aid", "injury"]

CONTRACT_FIELD_PATTERNS = {
    "effective_date": re.compile(r"Effective Date\s*[:\-]?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.IGNORECASE),
    "expiry_date": re.compile(r"Expiry Date\s*[:\-]?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.IGNORECASE),
    "renewal_notice_days": re.compile(r"Renewal Notice Period\s*[:\-]?\s*(\d+)\s*days?", re.IGNORECASE),
    "termination_clause": re.compile(r"Termination Clause\s*[:\-]?\s*(.+)", re.IGNORECASE),
}

VENDOR_DOC_PATTERNS = {
    "gst_number": re.compile(r"\bGSTIN?\s*[:\-]?\s*([0-9A-Z]{10,15})\b", re.IGNORECASE),
    "insurance_expiry": re.compile(
        r"Insurance\s+(?:Certificate\s+)?Expiry\s*[:\-]?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.IGNORECASE
    ),
    "bank_account_last4": re.compile(r"Account\s*(?:No\.?|Number)?\s*[:\-]?\s*[\dXx*]*(\d{4})\b"),
}

EXCEPTION_RECOMMENDATIONS = [
    (["quantity mismatch", "qty mismatch"], "Review GRN and invoice line items; confirm the correct quantity before resubmitting."),
    (["price", "variance"], "Compare PO unit price against the invoice; escalate to procurement if the vendor changed pricing without an amendment."),
    (["duplicate"], "Confirm with AP whether this invoice was already posted; reject if it is a genuine duplicate."),
    (["missing grn", "grn"], "Confirm goods receipt was posted in SAP MM; if delivery is still in transit, hold payment until GRN exists."),
    (["expired", "compliance"], "Request updated documentation from the vendor/employee before proceeding."),
    (["blocked", "credit"], "Escalate to the account owner to clear the block before continuing the transaction."),
]


class MockAIProvider(AIProvider):
    # --- reused from existing Mailroom heuristics ---------------------------
    def extract_invoice(self, raw_text: str) -> dict[str, Any]:
        fields = ocr_service.extract_invoice_fields(raw_text)
        found = sum(1 for v in fields.values() if v)
        confidence = round(min(1.0, 0.15 + 0.17 * found), 3)
        return {
            "classification": "invoice" if found >= 3 else "unclear",
            "confidence": confidence,
            **fields,
            "reasons": [f"{found}/6 invoice fields extracted via regex over OCR text"],
        }

    def classify_document(
        self,
        subject: str,
        body: str,
        sender: str,
        attachment_filename: Optional[str] = None,
        attachment_text: Optional[str] = None,
    ) -> dict[str, Any]:
        message = SimpleNamespace(subject=subject, body=body, sender=sender, sender_name=sender)
        if attachment_filename is None:
            result = classify_message(message, None)
            return {
                "classification": "invoice" if result.is_invoice else "not_invoice",
                "confidence": result.confidence,
                "reasons": result.reasons,
            }
        # This method operates on arbitrary text, not a saved MailAttachment
        # row with a real file on disk — so there's usually no real path to
        # OCR. classify_message()'s internal run_ocr() call fails gracefully
        # on a bogus path (returns an "[OCR_ERROR: ...]" string that just
        # contributes zero signal), which is exactly what we want here: reuse
        # its filename/subject/body signals, then layer the OCR-text signal
        # back in manually using text the caller has already extracted.
        attachment = SimpleNamespace(filename=attachment_filename, file_path=os.devnull)
        result = classify_message(message, attachment)
        score = result.confidence
        reasons = list(result.reasons[:-1])  # drop the old final-verdict line, we re-add it below
        if attachment_text:
            ocr_upper = attachment_text.upper()
            if "INVOICE" in ocr_upper:
                score += 0.15
                reasons.append("OCR text contains an 'INVOICE' header (+0.15)")
            if "TOTAL" in ocr_upper and re.search(r"\d+\.\d{2}", attachment_text):
                score += 0.1
                reasons.append("OCR text contains a total amount (+0.10)")
        score = max(0.0, min(1.0, score))
        is_invoice = score >= 0.6
        reasons.append(f"Final confidence {score:.2f} -> classified as {'INVOICE' if is_invoice else 'NOT an invoice'}")
        return {
            "classification": "invoice" if is_invoice else "not_invoice",
            "confidence": round(score, 3),
            "reasons": reasons,
        }

    # --- new deterministic heuristics ----------------------------------------
    def extract_vendor_docs(self, raw_text: str) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        reasons = []
        for name, pattern in VENDOR_DOC_PATTERNS.items():
            m = pattern.search(raw_text)
            if m:
                fields[name] = m.group(1)
                reasons.append(f"Matched {name} via regex")
        confidence = round(min(1.0, 0.2 * len(fields)), 3)
        return {"classification": "vendor_document", "confidence": confidence, **fields, "reasons": reasons or ["No structured fields matched"]}

    def classify_hse_incident(self, description: str) -> dict[str, Any]:
        text = description.lower()
        if any(k in text for k in HSE_CRITICAL_KEYWORDS):
            severity, confidence = "Critical", 0.95
        elif any(k in text for k in HSE_HIGH_KEYWORDS):
            severity, confidence = "High", 0.85
        elif any(k in text for k in HSE_MEDIUM_KEYWORDS):
            severity, confidence = "Medium", 0.7
        else:
            severity, confidence = "Low", 0.6
        recommendation = {
            "Critical": "Immediate escalation to HSE Manager and site incident commander; initiate emergency response.",
            "High": "Escalate to HSE Manager within the hour; open a formal investigation.",
            "Medium": "Log and route to HSE Manager for review within 24 hours.",
            "Low": "Log for routine HSE tracking; no immediate escalation required.",
        }[severity]
        return {
            "classification": severity,
            "confidence": confidence,
            "recommendation": recommendation,
            "reasons": [f"Keyword-matched severity tier: {severity}"],
        }

    def classify_maintenance_alarm(self, alarm: dict[str, Any]) -> dict[str, Any]:
        value = float(alarm.get("value", 0) or 0)
        threshold = float(alarm.get("threshold", 1) or 1)
        ratio = value / threshold if threshold else 0
        if ratio >= 2.0:
            priority, confidence = "Emergency", 0.95
        elif ratio >= 1.5:
            priority, confidence = "Urgent", 0.85
        elif ratio >= 1.0:
            priority, confidence = "Routine", 0.7
        else:
            priority, confidence = "Informational", 0.5
        return {
            "classification": priority,
            "confidence": confidence,
            "recommendation": f"Create a {priority} work order for equipment {alarm.get('equipment_id', '?')}"
            f" — reading {value} vs threshold {threshold} ({ratio:.2f}x).",
            "reasons": [f"Reading/threshold ratio {ratio:.2f} mapped to {priority} priority tier"],
        }

    def explain_production_anomaly(
        self, planned: float, actual: float, context: dict[str, Any]
    ) -> dict[str, Any]:
        variance_pct = ((planned - actual) / planned * 100) if planned else 0.0
        if variance_pct >= 10:
            severity = "Critical"
            causes = "unplanned equipment downtime, major feedstock shortage, or a process upset"
        elif variance_pct >= 5:
            severity = "Warning"
            causes = "minor equipment derating, scheduling slippage, or measurement calibration drift"
        else:
            severity = "Normal"
            causes = "normal operating variance"
        unit = context.get("unit", "units")
        explanation = (
            f"Actual production of {actual:,.0f} {unit} is {variance_pct:.1f}% "
            f"{'below' if variance_pct >= 0 else 'above'} planned {planned:,.0f} {unit}. "
            f"Likely contributing factors: {causes}."
        )
        return {
            "classification": severity,
            "confidence": 0.75,
            "variance_pct": round(variance_pct, 2),
            "recommendation": explanation,
            "reasons": [f"Variance {variance_pct:.1f}% mapped to {severity} tier"],
        }

    def extract_contract_clauses(self, raw_text: str) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        reasons = []
        for name, pattern in CONTRACT_FIELD_PATTERNS.items():
            m = pattern.search(raw_text)
            if m:
                fields[name] = m.group(1).strip()
                reasons.append(f"Matched {name} via regex")
        confidence = round(min(1.0, 0.25 * len(fields)), 3)
        return {"classification": "contract", "confidence": confidence, **fields, "reasons": reasons or ["No structured clauses matched"]}

    def explain_exception(self, context: dict[str, Any]) -> dict[str, Any]:
        reason = str(context.get("reason", "")).lower()
        recommendation = "Escalate to a Senior Manager for manual review."
        for keywords, rec in EXCEPTION_RECOMMENDATIONS:
            if any(kw in reason for kw in keywords):
                recommendation = rec
                break
        workflow_name = context.get("workflow_name", "this workflow")
        explanation = f"{workflow_name} raised an exception: {context.get('reason', 'unspecified reason')}."
        return {
            "classification": "exception_explanation",
            "confidence": 0.8,
            "recommendation": recommendation,
            "explanation": explanation,
            "reasons": ["Recommendation mapped from exception reason keywords"],
        }
