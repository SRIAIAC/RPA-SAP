import json
import logging
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.audit import log_action
from app.database import get_session
from app.deps import get_current_user, require_min_level
from app.mailroom_schemas import (
    AttachmentOut,
    ClassifyAllOut,
    ClassifyResultOut,
    ImportGmailOut,
    InvoiceExtractionOut,
    MailMessageDetailOut,
    MailMessageListOut,
)
from app.models import Department, InvoiceExtraction, Level, MailAttachment, MailMessage, User
from app.services.classifier import classify_message
from app.services.gmail_import import fetch_recent_messages

logger = logging.getLogger("app.mailroom")

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "uploaded_attachments"
ALLOWED_UPLOAD_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "application/pdf"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

router = APIRouter(prefix="/api/mailroom", tags=["mailroom"])
_require_senior_manager = require_min_level(Level.SENIOR_MANAGER)


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
        source=message.source,
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


@router.post("/upload", response_model=MailMessageDetailOut)
async def upload_document(
    file: UploadFile = File(...),
    subject: str = Form(default=""),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Upload a real invoice/document (PNG/JPG/PDF) to test the classifier/
    OCR pipeline against real data — no external account needed. OCR only
    reads image files; a PDF is stored and classified on its email-wrapper
    signals alone (same graceful degradation as any other non-image
    attachment in this pipeline)."""
    if file.content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Use PNG, JPG, or PDF.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 10MB).")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "upload")
    file_path = UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}_{safe_name}"
    file_path.write_bytes(contents)

    message = MailMessage(
        sender=f"{user.username}@manual-upload.local",
        sender_name=user.username,
        subject=subject.strip() or f"Uploaded document: {file.filename}",
        body="Manually uploaded for testing the OCR/classifier pipeline against a real document.",
        department=Department.ADMIN,
        has_attachment=True,
        source="upload",
    )
    session.add(message)
    session.commit()
    session.refresh(message)

    attachment = MailAttachment(
        mail_message_id=message.id,
        filename=file.filename or "upload",
        content_type=file.content_type,
        file_path=str(file_path),
    )
    session.add(attachment)
    session.commit()
    session.refresh(attachment)

    log_action(
        session,
        actor=user,
        action="mailroom.document_upload",
        target_type="MailMessage",
        target_id=message.id,
        detail={"filename": file.filename, "content_type": file.content_type},
    )

    return MailMessageDetailOut(
        id=message.id,
        sender=message.sender,
        sender_name=message.sender_name,
        subject=message.subject,
        body=message.body,
        department=message.department,
        received_at=message.received_at,
        has_attachment=True,
        source=message.source,
        attachment=AttachmentOut.model_validate(attachment),
        extraction=None,
    )


@router.post("/manual-entry", response_model=MailMessageDetailOut)
async def create_manual_entry(
    subject: str = Form(...),
    body: str = Form(...),
    department: str = Form(...),
    sender_name: str = Form(default=""),
    sender: str = Form(default=""),
    file: Optional[UploadFile] = File(default=None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Add a mail message by hand — every field (sender, subject, body,
    department) entered directly rather than pulled from Gmail or inferred
    from an uploaded file. Attachment is optional. Lets a user file a message
    (e.g. one they sent/received outside the mock inbox) that the classifier/
    OCR pipeline can then be run against like any other message."""
    subject = subject.strip()
    body = body.strip()
    if not subject:
        raise HTTPException(status_code=400, detail="Subject is required.")
    if not body:
        raise HTTPException(status_code=400, detail="Body is required.")
    try:
        dept = Department(department)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid department: {department}")

    sender_name = sender_name.strip() or user.username
    sender = sender.strip() or f"{user.username}@manual-entry.local"

    has_attachment = False
    file_path: Optional[Path] = None
    if file is not None and file.filename:
        if file.content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Use PNG, JPG, or PDF.",
            )
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty file.")
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=400, detail="File too large (max 10MB).")
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "upload")
        file_path = UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}_{safe_name}"
        file_path.write_bytes(contents)
        has_attachment = True

    message = MailMessage(
        sender=sender,
        sender_name=sender_name,
        subject=subject,
        body=body,
        department=dept,
        has_attachment=has_attachment,
        source="manual",
    )
    session.add(message)
    session.commit()
    session.refresh(message)

    attachment_out: Optional[AttachmentOut] = None
    if has_attachment and file_path is not None:
        attachment = MailAttachment(
            mail_message_id=message.id,
            filename=file.filename or "upload",
            content_type=file.content_type,
            file_path=str(file_path),
        )
        session.add(attachment)
        session.commit()
        session.refresh(attachment)
        attachment_out = AttachmentOut.model_validate(attachment)

    log_action(
        session,
        actor=user,
        action="mailroom.manual_entry",
        target_type="MailMessage",
        target_id=message.id,
        detail={"subject": subject, "department": dept.value, "has_attachment": has_attachment},
    )

    return MailMessageDetailOut(
        id=message.id,
        sender=message.sender,
        sender_name=message.sender_name,
        subject=message.subject,
        body=message.body,
        department=message.department,
        received_at=message.received_at,
        has_attachment=has_attachment,
        source=message.source,
        attachment=attachment_out,
        extraction=None,
    )


@router.post("/import-gmail", response_model=ImportGmailOut)
def import_gmail(
    limit: int = 10,
    session: Session = Depends(get_session),
    user: User = Depends(_require_senior_manager),
):
    try:
        imported = fetch_recent_messages(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Gmail import failed")
        raise HTTPException(status_code=502, detail=f"Gmail import failed: {exc}")

    created = 0
    skipped = 0
    for item in imported:
        existing = session.exec(
            select(MailMessage).where(MailMessage.external_id == item.external_id)
        ).first()
        if existing is not None:
            skipped += 1
            continue

        message = MailMessage(
            sender=item.sender,
            sender_name=item.sender_name,
            subject=item.subject,
            body=item.body,
            department=Department.ADMIN,
            received_at=item.received_at,
            has_attachment=item.attachment is not None,
            source="gmail_import",
            external_id=item.external_id,
        )
        session.add(message)
        session.commit()
        session.refresh(message)

        if item.attachment is not None:
            session.add(
                MailAttachment(
                    mail_message_id=message.id,
                    filename=item.attachment.filename,
                    content_type=item.attachment.content_type,
                    file_path=item.attachment.file_path,
                )
            )
            session.commit()
        created += 1

    log_action(
        session,
        actor=user,
        action="mailroom.gmail_import",
        target_type="MailMessage",
        target_id=None,
        detail={"imported": created, "skipped_duplicates": skipped, "total_fetched": len(imported)},
    )

    return ImportGmailOut(imported=created, skipped_duplicates=skipped, total_fetched=len(imported))


@router.get("/attachments/{attachment_id}/file")
def get_attachment_file(
    attachment_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)
):
    attachment = session.get(MailAttachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(attachment.file_path, media_type=attachment.content_type, filename=attachment.filename)
