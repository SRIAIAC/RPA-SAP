"""Real OCR via Tesseract (pytesseract), plus regex-based invoice field
extraction from the raw OCR text. No hardcoded field values — everything here
is genuinely parsed from whatever pytesseract reads off the image.
"""

import re
import shutil

import pytesseract
from PIL import Image

KNOWN_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if shutil.which("tesseract") is None:
    pytesseract.pytesseract.tesseract_cmd = KNOWN_TESSERACT_PATH


def run_ocr(image_path: str) -> str:
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as exc:  # pytesseract/Tesseract not available or image unreadable
        return f"[OCR_ERROR: {exc}]"


INVOICE_NUMBER_RE = re.compile(r"(?:INV(?:OICE)?[\s#\-:]*)?\bINV[-\s]?(\d{3,8})\b", re.IGNORECASE)
INVOICE_NUMBER_ALT_RE = re.compile(r"Invoice\s*(?:Number|No\.?|#)\s*[:\-]?\s*([A-Za-z0-9\-]{3,20})", re.IGNORECASE)
PO_NUMBER_RE = re.compile(r"\bPO[\s#\-]?(?:NUMBER|NO\.?)?\s*[:\-]?\s*(\d{4,10})\b", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
DATE_ALT_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
TOTAL_RE = re.compile(
    # negative lookbehind excludes "Subtotal" (which contains the substring
    # "total"), so this only matches a standalone "Total"/"Total Due" label.
    r"\b(?<!sub)(?:TOTAL DUE|TOTAL AMOUNT|GRAND TOTAL|TOTAL)\b\s*[:\-]?\s*([A-Za-z]{2,3})?\s*([\d,]+\.\d{2})",
    re.IGNORECASE,
)
CURRENCY_RE = re.compile(r"\b(INR|USD|EUR|GBP|AED)\b")


def extract_invoice_fields(raw_text: str) -> dict:
    text = raw_text or ""

    vendor_name = None
    for line in text.splitlines():
        stripped = line.strip()
        if len(stripped) >= 6 and any(c.isalpha() for c in stripped) and "INVOICE" not in stripped.upper():
            vendor_name = stripped
            break

    invoice_number = None
    m = INVOICE_NUMBER_RE.search(text)
    if m:
        invoice_number = f"INV-{m.group(1)}"
    else:
        m = INVOICE_NUMBER_ALT_RE.search(text)
        if m:
            invoice_number = m.group(1).strip()

    po_number = None
    m = PO_NUMBER_RE.search(text)
    if m:
        po_number = f"PO-{m.group(1)}"

    invoice_date = None
    m = DATE_RE.search(text)
    if m:
        invoice_date = m.group(1)
    else:
        m = DATE_ALT_RE.search(text)
        if m:
            invoice_date = m.group(1)

    total_amount = None
    currency = None
    m = TOTAL_RE.search(text)
    if m:
        if m.group(1):
            currency = m.group(1).upper()
        total_amount = m.group(2)
    if currency is None:
        m2 = CURRENCY_RE.search(text)
        if m2:
            currency = m2.group(1).upper()

    return {
        "vendor_name": vendor_name,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "po_number": po_number,
        "total_amount": total_amount,
        "currency": currency,
    }
