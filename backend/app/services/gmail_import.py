"""Read-only Gmail ingestion for testing the Mailroom pipeline (classifier +
OCR) against real mail instead of the 15 synthetic seeded emails.

Opt-in: requires GMAIL_ADDRESS + GMAIL_APP_PASSWORD in backend/.env.
GMAIL_APP_PASSWORD must be a Google-generated App Password (Google Account ->
Security -> App passwords, requires 2FA on the account) — never the real
account password.

Never mutates the mailbox: `select(..., readonly=True)` plus
`BODY.PEEK[]` fetches mean this never sets \\Seen or otherwise changes
anything in the real inbox, and nothing here ever deletes or sends mail.
"""

import email
import imaplib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Optional

from app.config import settings

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
ATTACHMENTS_DIR = Path(__file__).resolve().parent.parent / "data" / "gmail_attachments"
MAX_IMPORT_LIMIT = 25


@dataclass
class ImportedAttachment:
    filename: str
    content_type: str
    file_path: str


@dataclass
class ImportedMessage:
    external_id: str
    sender: str
    sender_name: str
    subject: str
    body: str
    received_at: datetime
    attachment: Optional[ImportedAttachment]


def _decode(value: str) -> str:
    parts = decode_header(value or "")
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _safe_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name or "attachment")
    return f"{uuid.uuid4().hex[:8]}_{name}"


def _extract_body_and_attachment(msg: Message) -> tuple[str, Optional[ImportedAttachment]]:
    body = ""
    attachment: Optional[ImportedAttachment] = None

    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition") or "")
            content_type = part.get_content_type()

            if "attachment" in content_disposition and attachment is None:
                filename = _decode(part.get_filename() or "attachment")
                payload = part.get_payload(decode=True)
                if payload:
                    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
                    file_path = ATTACHMENTS_DIR / _safe_filename(filename)
                    file_path.write_bytes(payload)
                    attachment = ImportedAttachment(
                        filename=filename, content_type=content_type, file_path=str(file_path)
                    )
            elif content_type == "text/plain" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")

    return body.strip(), attachment


def fetch_recent_messages(limit: int = 10) -> list[ImportedMessage]:
    if not settings.gmail_address or not settings.gmail_app_password:
        raise RuntimeError(
            "GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in backend/.env "
            "to import Gmail messages. Use a Google App Password, not your "
            "real account password."
        )
    limit = max(1, min(limit, MAX_IMPORT_LIMIT))

    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        conn.login(settings.gmail_address, settings.gmail_app_password)
        # readonly=True: this connection can never mutate the mailbox.
        conn.select("INBOX", readonly=True)
        status, data = conn.search(None, "ALL")
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {status}")
        ids = data[0].split()
        recent_ids = ids[-limit:]

        messages: list[ImportedMessage] = []
        for msg_id in reversed(recent_ids):
            # BODY.PEEK[]: fetch without marking as read (plain BODY[] would).
            status, msg_data = conn.fetch(msg_id, "(BODY.PEEK[])")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            parsed = email.message_from_bytes(raw)

            message_id_header = parsed.get("Message-ID") or f"imap-{msg_id.decode()}"
            sender_name, sender_addr = parseaddr(_decode(parsed.get("From", "")))
            subject = _decode(parsed.get("Subject", "(no subject)"))
            try:
                received_at = parsedate_to_datetime(parsed.get("Date"))
            except (TypeError, ValueError):
                received_at = datetime.utcnow()

            body, attachment = _extract_body_and_attachment(parsed)

            messages.append(
                ImportedMessage(
                    external_id=message_id_header,
                    sender=sender_addr or "unknown@unknown",
                    sender_name=sender_name or sender_addr or "Unknown",
                    subject=subject,
                    body=body,
                    received_at=received_at,
                    attachment=attachment,
                )
            )
        return messages
    finally:
        conn.logout()
