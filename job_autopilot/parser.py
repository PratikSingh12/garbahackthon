"""
Email parser module supporting JSON and .mbox formats.
"""

import json
import mailbox
import os
import re
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from io import BytesIO, StringIO
from typing import List, Union
from dateutil import parser as dateutil_parser

from job_autopilot.models import EmailMessage


def extract_domain(email_address: str) -> str:
    """Extract domain from an email address (e.g., 'careers@airbnb.com' -> 'airbnb.com')."""
    if not email_address or "@" not in email_address:
        return ""
    parts = email_address.strip().split("@")
    return parts[-1].lower()


def parse_date(date_val: Union[str, datetime]) -> datetime:
    """Parse various date formats (ISO, RFC 2822, etc.) into timezone-aware datetime."""
    if isinstance(date_val, datetime):
        if date_val.tzinfo is None:
            return date_val.replace(tzinfo=timezone.utc)
        return date_val

    if not date_val:
        return datetime.now(timezone.utc)

    # Try RFC 2822 first (common in email headers)
    try:
        dt = parsedate_to_datetime(date_val)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    # Try dateutil parser
    try:
        dt = dateutil_parser.parse(date_val)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def extract_body_from_mbox_msg(msg: mailbox.mboxMessage) -> str:
    """Extract plain text payload from a mailbox message, handling multipart."""
    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        body_parts.append(payload.decode(charset, errors="replace"))
                    except Exception:
                        body_parts.append(payload.decode("utf-8", errors="replace"))
        # If no text/plain found, fallback to text/html stripped
        if not body_parts:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        html = payload.decode("utf-8", errors="replace")
                        clean = re.sub(r"<[^>]+>", " ", html)
                        body_parts.append(clean)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                body_parts.append(payload.decode(charset, errors="replace"))
            except Exception:
                body_parts.append(payload.decode("utf-8", errors="replace"))
        else:
            # Fallback if string payload
            raw_payload = msg.get_payload()
            if isinstance(raw_payload, str):
                body_parts.append(raw_payload)

    return "\n".join(body_parts).strip()


def load_from_json(content_or_path: Union[str, bytes]) -> List[EmailMessage]:
    """Parse JSON email list."""
    if isinstance(content_or_path, (str, bytes)) and os.path.exists(str(content_or_path)):
        with open(str(content_or_path), "r", encoding="utf-8") as f:
            data = json.load(f)
    elif isinstance(content_or_path, bytes):
        data = json.loads(content_or_path.decode("utf-8"))
    else:
        data = json.loads(content_or_path)

    if not isinstance(data, list):
        raise ValueError("JSON data must be a list of email objects")

    messages = []
    for idx, item in enumerate(data):
        msg_id = item.get("id") or f"json_msg_{idx + 1:03d}"
        sender_raw = item.get("sender") or item.get("from") or ""
        _, sender_email = parseaddr(sender_raw)
        sender_domain = extract_domain(sender_email)

        date_parsed = parse_date(item.get("date") or item.get("timestamp") or "")

        messages.append(
            EmailMessage(
                id=msg_id,
                sender=sender_raw,
                sender_email=sender_email,
                sender_domain=sender_domain,
                recipient=item.get("recipient") or item.get("to") or "",
                subject=item.get("subject") or "(No Subject)",
                date=date_parsed,
                body=item.get("body") or item.get("content") or item.get("text") or "",
            )
        )
    return messages


def load_from_mbox(file_path_or_bytes: Union[str, bytes]) -> List[EmailMessage]:
    """Parse .mbox file."""
    temp_path = None
    if isinstance(file_path_or_bytes, bytes):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mbox") as tmp:
            tmp.write(file_path_or_bytes)
            temp_path = tmp.name
        target_path = temp_path
    else:
        target_path = file_path_or_bytes

    mbox = mailbox.mbox(target_path)
    messages = []
    try:
        for idx, (key, msg) in enumerate(mbox.items()):
            msg_id = msg.get("Message-ID") or f"mbox_msg_{idx + 1:03d}"
            msg_id = msg_id.strip("<> ")
            sender_raw = msg.get("From", "")
            _, sender_email = parseaddr(sender_raw)
            sender_domain = extract_domain(sender_email)

            subject = msg.get("Subject", "(No Subject)")
            date_header = msg.get("Date", "")
            date_parsed = parse_date(date_header)

            body = extract_body_from_mbox_msg(msg)

            messages.append(
                EmailMessage(
                    id=msg_id,
                    sender=sender_raw,
                    sender_email=sender_email,
                    sender_domain=sender_domain,
                    recipient=msg.get("To", ""),
                    subject=subject,
                    date=date_parsed,
                    body=body,
                )
            )
        return messages
    finally:
        mbox.close()
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def load_inbox(source: Union[str, bytes], format_hint: str = "auto") -> List[EmailMessage]:
    """
    Unified inbox loader supporting both JSON and .mbox.
    Auto-detects format if format_hint is 'auto'.
    """
    if format_hint == "auto":
        if isinstance(source, str) and os.path.isfile(source):
            lower = source.lower()
            if lower.endswith(".json"):
                return load_from_json(source)
            elif lower.endswith(".mbox") or lower.endswith(".eml"):
                return load_from_mbox(source)

        # Content sniffing
        if isinstance(source, bytes):
            sample = source[:200].strip()
            if sample.startswith(b"[") or sample.startswith(b"{"):
                return load_from_json(source)
            else:
                return load_from_mbox(source)
        elif isinstance(source, str):
            sample = source.strip()[:100]
            if sample.startswith("[") or sample.startswith("{"):
                return load_from_json(source)
            elif "From " in sample or sample.startswith("From:"):
                # Write to temp mbox or try json
                return load_from_json(source)

    if format_hint == "json":
        return load_from_json(source)
    elif format_hint == "mbox":
        return load_from_mbox(source)

    # Fallback try json, then mbox
    try:
        return load_from_json(source)
    except Exception:
        return load_from_mbox(source)
