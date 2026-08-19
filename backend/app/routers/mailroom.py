import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.mailroom_schemas import (
    AttachmentOut,
    ClassifyAllOut,
    ClassifyResultOut,
    InvoiceExtractionOut,
    MailMessageDetailOut,
    MailMessageListOut,
)
from app.models import InvoiceExtraction, MailAttachment, MailMessage, User
from app.services.classifier import classify_message

router = APIRouter(prefix="/api/mailroom", tags=["mailroom"])


def _extraction_out(extraction: InvoiceExtraction) -> InvoiceExtractionOut:
    return InvoiceExtractionOut(
        is_invoice=extraction.is_invoice,
        classifier_confidence=extraction.classifier_confidence,
        classifier_reasons=json.loads(extraction.classifier_reasons) if extraction.classifier_reasons else [],
        vendor_name=extraction.vendor_name,
        invoice_number=extraction.invoice_number,
        invoice_date=extraction.invoice_date,
        po_number=extraction.po_number,
        total_amount=extraction.total_amount,
        currency=extraction.currency,
        raw_ocr_text=extraction.raw_ocr_text,
    )


def _run_and_store_classification(session: Session, message: MailMessage) -> InvoiceExtraction:
    attachment = session.exec(
        select(MailAttachment).where(MailAttachment.mail_message_id == message.id)
    ).first()

    existing = None
    if attachment is not None:
        existing = session.exec(
            select(InvoiceExtraction).where(InvoiceExtraction.mail_attachment_id == attachment.id)
        ).first()
        if existing is not None:
            return existing

    result = classify_message(message, attachment)

    if attachment is None:
        # No attachment to key InvoiceExtraction off; still classify but don't
        # persist a row (schema requires a mail_attachment_id). Callers get
        # the transient result via the response, not a cached row.
        return InvoiceExtraction(
            mail_attachment_id=0,
            is_invoice=result.is_invoice,
            classifier_confidence=result.confidence,
            classifier_reasons=json.dumps(result.reasons),
            raw_ocr_text=result.ocr_text,
        )

    extracted_fields = {}
    if result.ocr_text:
        from app.services.ocr import extract_invoice_fields

        extracted_fields = extract_invoice_fields(result.ocr_text)

    extraction = InvoiceExtraction(
        mail_attachment_id=attachment.id,
        is_invoice=result.is_invoice,
        classifier_confidence=result.confidence,
        classifier_reasons=json.dumps(result.reasons),
        vendor_name=extracted_fields.get("vendor_name"),
        invoice_number=extracted_fields.get("invoice_number"),
        invoice_date=extracted_fields.get("invoice_date"),
        po_number=extracted_fields.get("po_number"),
        total_amount=extracted_fields.get("total_amount"),
        currency=extracted_fields.get("currency"),
        raw_ocr_text=result.ocr_text,
    )
    session.add(extraction)
    session.commit()
    session.refresh(extraction)
    return extraction


@router.get("/messages", response_model=list[MailMessageListOut])
def list_messages(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    messages = session.exec(select(MailMessage).order_by(MailMessage.received_at)).all()
    return [MailMessageListOut.model_validate(m) for m in messages]


@router.get("/messages/{message_id}", response_model=MailMessageDetailOut)
def get_message(
    message_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)
):
    message = session.get(MailMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    attachment = session.exec(
        select(MailAttachment).where(MailAttachment.mail_message_id == message.id)
    ).first()
    extraction = None
    if attachment is not None:
        extraction_row = session.exec(
            select(InvoiceExtraction).where(InvoiceExtraction.mail_attachment_id == attachment.id)
        ).first()
        if extraction_row is not None:
            extraction = _extraction_out(extraction_row)

    return MailMessageDetailOut(
        id=message.id,
        sender=message.sender,
        sender_name=message.sender_name,
        subject=message.subject,
        body=message.body,
        department=message.department,
        received_at=message.received_at,
        has_attachment=message.has_attachment,
        attachment=AttachmentOut.model_validate(attachment) if attachment else None,
        extraction=extraction,
    )


@router.post("/messages/{message_id}/classify", response_model=ClassifyResultOut)
def classify_single(
    message_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)
):
    message = session.get(MailMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    extraction = _run_and_store_classification(session, message)
    return ClassifyResultOut(
        message_id=message.id,
        subject=message.subject,
        is_invoice=extraction.is_invoice,
        classifier_confidence=extraction.classifier_confidence,
        classifier_reasons=json.loads(extraction.classifier_reasons) if extraction.classifier_reasons else [],
        extraction=_extraction_out(extraction),
    )


@router.post("/classify-all", response_model=ClassifyAllOut)
def classify_all(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    messages = session.exec(select(MailMessage).order_by(MailMessage.received_at)).all()
    results = []
    flagged = 0
    for message in messages:
        extraction = _run_and_store_classification(session, message)
        if extraction.is_invoice:
            flagged += 1
        results.append(
            ClassifyResultOut(
                message_id=message.id,
                subject=message.subject,
                is_invoice=extraction.is_invoice,
                classifier_confidence=extraction.classifier_confidence,
                classifier_reasons=json.loads(extraction.classifier_reasons) if extraction.classifier_reasons else [],
                extraction=_extraction_out(extraction),
            )
        )
    return ClassifyAllOut(total=len(messages), flagged_as_invoice=flagged, results=results)


@router.get("/attachments/{attachment_id}/file")
def get_attachment_file(
    attachment_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)
):
    attachment = session.get(MailAttachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(attachment.file_path, media_type=attachment.content_type, filename=attachment.filename)
