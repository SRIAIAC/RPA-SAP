from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models import Department


class AttachmentOut(BaseModel):
    id: int
    filename: str
    content_type: str

    class Config:
        from_attributes = True


class MailMessageListOut(BaseModel):
    id: int
    sender: str
    sender_name: str
    subject: str
    department: Department
    received_at: datetime
    has_attachment: bool

    class Config:
        from_attributes = True


class InvoiceExtractionOut(BaseModel):
    is_invoice: bool
    classifier_confidence: float
    classifier_reasons: List[str]
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    po_number: Optional[str] = None
    total_amount: Optional[str] = None
    currency: Optional[str] = None
    raw_ocr_text: Optional[str] = None


class MailMessageDetailOut(BaseModel):
    id: int
    sender: str
    sender_name: str
    subject: str
    body: str
    department: Department
    received_at: datetime
    has_attachment: bool
    attachment: Optional[AttachmentOut] = None
    extraction: Optional[InvoiceExtractionOut] = None

    class Config:
        from_attributes = True


class ClassifyResultOut(BaseModel):
    message_id: int
    subject: str
    is_invoice: bool
    classifier_confidence: float
    classifier_reasons: List[str]
    extraction: Optional[InvoiceExtractionOut] = None


class ClassifyAllOut(BaseModel):
    total: int
    flagged_as_invoice: int
    results: List[ClassifyResultOut]
