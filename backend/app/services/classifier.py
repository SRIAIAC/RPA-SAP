"""Transparent heuristic "invoice-bearing email" classifier.

This stands in for an AI/LLM classifier — there is no LLM API key available in
this demo environment, so instead of pretending to call one, we implement an
explainable, deterministic scoring function over a handful of signals a real
AP-mailroom triage model would also look at: is there an attachment shaped
like an invoice, does the subject/body contain invoice-ish keywords and
patterns (INV-#### style numbers, "remit", "payment due", "PO #", currency
amounts), does the sender look like an external vendor, and — if there's an
attachment — does OCR of that attachment actually contain invoice-shaped
text (an "INVOICE" header, a total, a PO reference, etc).

Each signal contributes a bounded weight to a 0-1 confidence score, and each
contribution is recorded in a human-readable list of reasons so the verdict
is auditable rather than a black box.
"""

import re
from dataclasses import dataclass, field

from app.models import MailAttachment, MailMessage
from app.services import ocr as ocr_service

CONFIDENCE_THRESHOLD = 0.6

INVOICE_NUMBER_PATTERN = re.compile(r"\bINV[-\s]?\d{3,8}\b", re.IGNORECASE)
PO_REFERENCE_PATTERN = re.compile(r"\bPO[\s#\-]?\d{4,10}\b", re.IGNORECASE)
CURRENCY_AMOUNT_PATTERN = re.compile(r"\b(?:INR|USD|Rs\.?|\$)\s?[\d,]+(?:\.\d{2})?\b", re.IGNORECASE)
INVOICE_KEYWORDS = ["invoice", "remit", "payment due", "amount due", "billed", "please pay", "total due"]
ATTACHMENT_NAME_HINTS = ["invoice", "inv-", "inv_", "bill"]

# Domains/keywords that suggest a genuine external vendor sender rather than
# an internal colleague or a newsletter/noreply address.
VENDOR_SENDER_HINTS = ["accounts", "billing", "ap@", "invoices@", "finance@"]
NOISE_SENDER_HINTS = ["noreply", "newsletter", "no-reply", "notifications@"]


@dataclass
class ClassificationResult:
    is_invoice: bool
    confidence: float
    reasons: list[str] = field(default_factory=list)
    ocr_text: str | None = None


def classify_message(message: MailMessage, attachment: MailAttachment | None) -> ClassificationResult:
    score = 0.0
    reasons: list[str] = []
    ocr_text: str | None = None

    subject_body = f"{message.subject}\n{message.body}"

    # Signal 1: attachment presence + filename shape (strong signal, but not
    # sufficient alone — some emails have unrelated attachments).
    if attachment is not None:
        score += 0.25
        reasons.append("Has a file attachment (+0.25)")
        fname_lower = attachment.filename.lower()
        if any(hint in fname_lower for hint in ATTACHMENT_NAME_HINTS):
            score += 0.15
            reasons.append(f"Attachment filename '{attachment.filename}' looks invoice-shaped (+0.15)")
    else:
        reasons.append("No attachment (invoice submissions in this workflow always come with a document)")

    # Signal 2: invoice-number-style pattern (INV-12345) in subject/body.
    if INVOICE_NUMBER_PATTERN.search(subject_body):
        score += 0.15
        reasons.append("Subject/body contains an invoice-number pattern like INV-##### (+0.15)")

    # Signal 3: PO reference.
    if PO_REFERENCE_PATTERN.search(subject_body):
        score += 0.1
        reasons.append("Subject/body references a PO number (+0.10)")

    # Signal 4: currency amount mentioned.
    if CURRENCY_AMOUNT_PATTERN.search(subject_body):
        score += 0.1
        reasons.append("Subject/body contains a currency amount (+0.10)")

    # Signal 5: invoice-ish keywords (weak individually, keyword-matching
    # "invoice" alone should NOT be enough to flag — several tricky emails in
    # the mock inbox mention "invoice" or "PO" in passing without being one).
    keyword_hits = [kw for kw in INVOICE_KEYWORDS if kw in subject_body.lower()]
    if keyword_hits:
        score += min(0.1, 0.04 * len(keyword_hits))
        reasons.append(f"Invoice-related keywords present: {', '.join(keyword_hits)} (+{min(0.1, 0.04*len(keyword_hits)):.2f})")

    # Signal 6: sender heuristics.
    sender_lower = message.sender.lower()
    if any(hint in sender_lower for hint in VENDOR_SENDER_HINTS):
        score += 0.1
        reasons.append("Sender address looks like a vendor AP/billing contact (+0.10)")
    if any(hint in sender_lower for hint in NOISE_SENDER_HINTS):
        score -= 0.2
        reasons.append("Sender address looks automated/newsletter-like (-0.20)")

    # Signal 7: OCR content signal — the strongest, most reliable signal when
    # available, since it inspects the actual document rather than the email
    # wrapper text.
    if attachment is not None:
        ocr_text = ocr_service.run_ocr(attachment.file_path)
        ocr_upper = ocr_text.upper()
        ocr_score = 0.0
        if "INVOICE" in ocr_upper:
            ocr_score += 0.15
            reasons.append("OCR text contains an 'INVOICE' header (+0.15)")
        if INVOICE_NUMBER_PATTERN.search(ocr_text) or "INVOICE NUMBER" in ocr_upper:
            ocr_score += 0.1
            reasons.append("OCR text contains an invoice number field (+0.10)")
        if "TOTAL" in ocr_upper and re.search(r"\d+\.\d{2}", ocr_text):
            ocr_score += 0.1
            reasons.append("OCR text contains a total amount (+0.10)")
        score += ocr_score

    score = max(0.0, min(1.0, score))
    is_invoice = score >= CONFIDENCE_THRESHOLD

    reasons.append(
        f"Final confidence {score:.2f} {'>=' if is_invoice else '<'} threshold {CONFIDENCE_THRESHOLD} "
        f"-> classified as {'INVOICE' if is_invoice else 'NOT an invoice'}"
    )

    return ClassificationResult(is_invoice=is_invoice, confidence=round(score, 3), reasons=reasons, ocr_text=ocr_text)
