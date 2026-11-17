import base64
import logging
import uuid
import threading
import httpx
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from ..core.config import settings
from ..core.state import ProcessingState
from ..models.schemas import EmailRecipientRecord, FacultyMatch
from .storage_service import storage_service
from .faculty_service import faculty_service

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self._dispatch_guard = threading.Lock()
        self._active_dispatches = set()
        self._http_client = httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=60.0, write=180.0, pool=10.0)
        )

    def is_dispatching(self, circular_id: str) -> bool:
        with self._dispatch_guard:
            return circular_id in self._active_dispatches

    def prepare_recipient_records(
        self,
        circular_id: str,
        matches: List[FacultyMatch]
    ) -> List[EmailRecipientRecord]:
        """
        Filters and validates verified faculty recipients.
        Looks up canonical email from faculty.json.
        Excludes ambiguous or unverified recipients.
        Deduplicates by faculty identity. Two faculty members may share an address,
        but both must remain visible and independently tracked as recipients.
        """
        records: List[EmailRecipientRecord] = []
        seen_faculty_ids = set()

        for m in matches:
            # Exclude unverified or ambiguous matches
            if not m.is_verified or m.verification_status not in ("AUTO_VERIFIED", "MANUALLY_CONFIRMED"):
                continue

            # Look up verified faculty member strictly from local directory
            faculty = faculty_service.get_faculty_by_id(m.faculty_id)
            if not faculty or not faculty.email:
                logger.warning(f"Skipping match {m.faculty_id}: No verified email found in directory.")
                continue

            if faculty.id in seen_faculty_ids:
                continue

            seen_faculty_ids.add(faculty.id)
            rec_id = f"REC_{uuid.uuid4().hex[:8]}"
            idempotency_key = f"{circular_id}_{faculty.id}_{uuid.uuid4().hex[:6]}"

            records.append(EmailRecipientRecord(
                recipient_id=rec_id,
                faculty_id=faculty.id,
                standard_name=faculty.standard_name,
                email=faculty.email,
                status="PENDING",
                resend_message_id=None,
                sent_at=None,
                error_message=None,
                retry_count=0,
                idempotency_key=idempotency_key
            ))

        return records

    def send_circular_emails(
        self,
        circular_id: str,
        subject: Optional[str] = None,
        summary_override: Optional[str] = None
    ) -> List[EmailRecipientRecord]:
        with self._dispatch_guard:
            if circular_id in self._active_dispatches:
                logger.warning(f"Email dispatch already active for {circular_id}; ignoring duplicate request.")
                existing = storage_service.get_email_records(circular_id)
                return [EmailRecipientRecord(**r) for r in existing]
            self._active_dispatches.add(circular_id)

        try:
            return self._send_circular_emails_once(circular_id, subject, summary_override)
        finally:
            with self._dispatch_guard:
                self._active_dispatches.discard(circular_id)

    def _send_circular_emails_once(
        self,
        circular_id: str,
        subject: Optional[str] = None,
        summary_override: Optional[str] = None
    ) -> List[EmailRecipientRecord]:
        """
        Sends emails to all PENDING or FAILED recipients for this circular.
        Attaches the original circular PDF.
        Tracks per-recipient status independently.
        """
        # Load or initialize email records
        existing_records_raw = storage_service.get_email_records(circular_id)
        if existing_records_raw:
            records = [EmailRecipientRecord(**r) for r in existing_records_raw]
            # Reconcile older queues that may have dropped a person because another
            # faculty member shared the same email address.
            matches_raw = storage_service.get_faculty_matches(circular_id)
            matches = [FacultyMatch(**m) for m in matches_raw]
            existing_faculty_ids = {r.faculty_id for r in records}
            records.extend(
                r for r in self.prepare_recipient_records(circular_id, matches)
                if r.faculty_id not in existing_faculty_ids
            )
        else:
            matches_raw = storage_service.get_faculty_matches(circular_id)
            matches = [FacultyMatch(**m) for m in matches_raw]
            records = self.prepare_recipient_records(circular_id, matches)

        if not records:
            logger.warning(f"No eligible recipients for circular {circular_id}")
            storage_service.update_state(circular_id, ProcessingState.READY_TO_SEND, "No verified recipients to email.")
            return []

        # Update state to SENDING_EMAILS
        storage_service.update_state(circular_id, ProcessingState.SENDING_EMAILS)

        summary = summary_override or storage_service.get_summary(circular_id)
        if not summary:
            summary = "Please find the attached institutional circular for your reference and necessary action."

        doc_path = storage_service.get_document_path(circular_id)
        attachment_payload = None
        if doc_path and doc_path.exists():
            try:
                with open(doc_path, "rb") as f:
                    file_bytes = f.read()
                    b64_content = base64.b64encode(file_bytes).decode("utf-8")
                    attachment_payload = {
                        "filename": doc_path.name,
                        "content": b64_content
                    }
            except Exception as e:
                logger.error(f"Error reading document attachment: {e}")

        email_subject = subject or f"[CircularRoute Notification] Institutional Circular – {circular_id}"

        # Send to each eligible recipient
        all_sent = True
        any_sent = False

        for rec in records:
            # Skip if already SENT or DELIVERED
            if rec.status in ("SENT", "DELIVERED"):
                any_sent = True
                continue

            rec.status = "SENDING"
            storage_service.save_email_records(circular_id, [r.dict() for r in records])

            success, message_id, err_msg = self._dispatch_single_email(
                recipient=rec,
                subject=email_subject,
                summary=summary,
                attachment=attachment_payload
            )

            if success:
                rec.status = "SENT"
                rec.resend_message_id = message_id
                rec.sent_at = datetime.now().isoformat()
                rec.error_message = None
                any_sent = True
            else:
                rec.status = "FAILED"
                rec.error_message = err_msg
                all_sent = False

            rec.retry_count += 1
            storage_service.save_email_records(circular_id, [r.dict() for r in records])

        # Update final circular state
        if all_sent and len(records) > 0:
            storage_service.update_state(circular_id, ProcessingState.COMPLETED)
        elif any_sent:
            storage_service.update_state(circular_id, ProcessingState.PARTIALLY_COMPLETED, "Some emails failed delivery.")
        else:
            storage_service.update_state(circular_id, ProcessingState.FAILED, "All email deliveries failed.")

        return records

    def retry_failed_emails(
        self,
        circular_id: str,
        recipient_ids: Optional[List[str]] = None
    ) -> List[EmailRecipientRecord]:
        """
        Retries failed email deliveries.
        Never resends messages that have already been SENT/DELIVERED.
        """
        if self.is_dispatching(circular_id):
            logger.warning(f"Ignoring retry for {circular_id}; an email dispatch is already active.")
            return [EmailRecipientRecord(**r) for r in storage_service.get_email_records(circular_id)]

        existing_records_raw = storage_service.get_email_records(circular_id)
        if not existing_records_raw:
            return []

        records = [EmailRecipientRecord(**r) for r in existing_records_raw]
        
        # Mark target failed records as PENDING
        for r in records:
            if r.status == "FAILED":
                if recipient_ids is None or r.recipient_id in recipient_ids:
                    r.status = "PENDING"

        storage_service.save_email_records(circular_id, [r.dict() for r in records])
        return self.send_circular_emails(circular_id)

    def _dispatch_single_email(
        self,
        recipient: EmailRecipientRecord,
        subject: str,
        summary: str,
        attachment: Optional[Dict[str, str]]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Dispatches an email through Resend API.
        If RESEND_API_KEY is not configured, provides simulated test delivery.
        """
        from_address = f"{settings.RESEND_FROM_NAME} <{settings.RESEND_FROM_EMAIL}>"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 24px; }}
        .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .header {{ background-color: #4f46e5; color: #ffffff; padding: 20px 24px; }}
        .header h1 {{ margin: 0; font-size: 20px; font-weight: 600; }}
        .content {{ padding: 24px; }}
        .greeting {{ font-size: 16px; margin-bottom: 16px; font-weight: 500; }}
        .summary-box {{ background-color: #f1f5f9; border-left: 4px solid #4f46e5; padding: 14px 18px; margin: 16px 0; border-radius: 4px; font-size: 15px; color: #334155; }}
        .footer {{ padding: 16px 24px; border-top: 1px solid #f1f5f9; font-size: 12px; color: #64748b; background-color: #fafafa; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>CircularRoute Notification</h1>
        </div>
        <div class="content">
            <div class="greeting">Dear {recipient.standard_name},</div>
            <p>An institutional circular has been issued and addressed to you. Please find the executive summary below:</p>
            <div class="summary-box">
                {summary}
            </div>
            <p>The complete official document is attached to this email for your detailed review.</p>
        </div>
        <div class="footer">
            Delivered automatically via CircularRoute Institutional Notification System.<br>
            Please do not reply directly to this automated email.
        </div>
    </div>
</body>
</html>"""

        # Check API key
        if not settings.RESEND_API_KEY or settings.RESEND_API_KEY.strip() == "your_resend_api_key":
            logger.info(f"Simulating email delivery to {recipient.email} (RESEND_API_KEY not configured).")
            # In test mode without key, mark as sent with simulated ID
            sim_id = f"sim_{uuid.uuid4().hex[:12]}"
            return True, sim_id, None

        payload = {
            "from": from_address,
            "to": [recipient.email],
            "subject": subject,
            "html": html_content,
        }

        if attachment:
            payload["attachments"] = [{
                "filename": attachment["filename"],
                "content": attachment["content"]
            }]

        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json"
        }

        if recipient.idempotency_key:
            headers["Idempotency-Key"] = recipient.idempotency_key

        try:
            # Keep a longer write timeout for the base64 circular attachment while
            # bounding connection setup and response waits separately.
            resp = self._http_client.post(
                "https://api.resend.com/emails",
                headers=headers,
                json=payload,
            )

            if resp is not None and resp.status_code in (200, 201):
                data = resp.json()
                msg_id = data.get("id")
                return True, msg_id, None
            elif resp is not None:
                err_text = resp.text
                logger.error(f"Resend API error ({resp.status_code}): {err_text}")
                return False, None, f"Resend API Error {resp.status_code}: {err_text}"
        except httpx.TimeoutException as e:
            logger.error(f"Resend request timed out ({type(e).__name__}): {e}")
            return False, None, (
                f"Resend {type(e).__name__} after waiting for the upload or response. "
                "Delivery may be uncertain; retry is safe because this recipient has an idempotency key."
            )
        except httpx.RequestError as e:
            logger.error(f"Network error sending via Resend: {e}")
            return False, None, f"Could not reach Resend ({type(e).__name__}): {e}. Check the network and retry."
        except Exception as e:
            logger.error(f"Unexpected error sending via Resend: {e}", exc_info=True)
            return False, None, f"Unexpected email dispatch error ({type(e).__name__}): {e}"

email_service = EmailService()
