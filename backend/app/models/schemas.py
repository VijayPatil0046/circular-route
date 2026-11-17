from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from ..core.state import ProcessingState

class FacultyMember(BaseModel):
    id: str
    standard_name: str
    department: Optional[str] = ""
    designation: Optional[str] = ""
    aliases: List[str] = []
    email: str

class FacultyDirectory(BaseModel):
    faculties: List[FacultyMember]

class FacultyMatch(BaseModel):
    original_reference: str
    standard_name: str
    faculty_id: str
    department: Optional[str] = ""
    email: str
    similarity_score: float = 0.0
    matching_explanation: str
    supporting_evidence: str
    relevance_explanation: str
    section_found: str = "To"  # "To", "Copy To", or "Document Body"
    verification_status: str = "AUTO_VERIFIED"  # "AUTO_VERIFIED", "AMBIGUOUS", "MANUALLY_CONFIRMED", "REJECTED"
    is_verified: bool = True
    manual_override: bool = False

class EmailRecipientRecord(BaseModel):
    recipient_id: str
    faculty_id: str
    standard_name: str
    email: str
    status: str = "PENDING"  # PENDING, SENDING, SENT, DELIVERED, FAILED
    resend_message_id: Optional[str] = None
    sent_at: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    idempotency_key: Optional[str] = None

class CircularStatusResponse(BaseModel):
    circular_id: str
    filename: str
    file_type: str
    file_size_bytes: int = 0
    page_count: int = 1
    current_state: ProcessingState
    created_at: str
    updated_at: str
    error_message: Optional[str] = None
    summary: Optional[str] = None
    has_extracted_text: bool = False
    matches_count: int = 0
    verified_matches_count: int = 0
    pending_review_count: int = 0
    emails_sent_count: int = 0
    emails_failed_count: int = 0
    can_proceed_to_send: bool = False
    can_retry_emails: bool = False

class ReviewItem(BaseModel):
    original_reference: str
    faculty_id: str
    action: str = "CONFIRM"  # CONFIRM, REJECT, REPLACE
    replacement_faculty_id: Optional[str] = None

class ReviewSubmissionRequest(BaseModel):
    reviews: List[ReviewItem]
    auto_proceed_to_send: bool = False

class SendEmailRequest(BaseModel):
    subject: Optional[str] = None
    summary_override: Optional[str] = None

class RetryEmailRequest(BaseModel):
    recipient_ids: Optional[List[str]] = None

class DashboardStats(BaseModel):
    total_circulars: int
    total_emails_sent: int
    total_emails_failed: int
    circulars_awaiting_review: int
    active_unresolved_circular: Optional[str] = None
    recent_circulars: List[CircularStatusResponse] = []
