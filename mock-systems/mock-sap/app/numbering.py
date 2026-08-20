"""Document-number assignment, matching how a real SAP system assigns PO/
invoice/work-order numbers server-side rather than trusting the caller to
invent one. Callers may still pass an explicit number (useful for the
golden demo scenario fixtures); if omitted, one is generated here."""

from uuid import uuid4


def generate_number(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10].upper()}"
