import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import FileResponse, PlainTextResponse

from ..core.config import settings
from ..core.state import ProcessingState, is_state_unresolved
from ..models.schemas import (
    CircularStatusResponse,
    FacultyMatch,
    EmailRecipientRecord,
    ReviewSubmissionRequest,
    SendEmailRequest,
    RetryEmailRequest,
    DashboardStats,
)
from ..services.storage_service import storage_service
from ..services.ocr_service import ocr_service
from ..services.faculty_service import faculty_service
from ..services.summary_service import summary_service
from ..services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Circulars"])

def execute_circular_pipeline(circular_id: str):
    """
    Background worker pipeline for automated circular processing:
    1. OCR extraction (PyMuPDF + OpenCV + PaddleOCR + TrOCR)
    2. Faculty Identification (To/Copy To + Aliases + Embeddings + Groq)
    3. Summary Generation (Groq 2-3 line summary)
    """
    try:
        logger.info(f"Starting automated pipeline for {circular_id}")
        doc_path = storage_service.get_document_path(circular_id)
        if not doc_path or not doc_path.exists():
            storage_service.update_state(circular_id, ProcessingState.FAILED, "Original document file missing.")
            return

        # Stage 1: OCR
        storage_service.update_state(circular_id, ProcessingState.PROCESSING_OCR)
        extracted_text, page_count = ocr_service.process_document(doc_path)
        
        # Save extracted text locally
        storage_service.save_extracted_text(circular_id, extracted_text)
        
        # Update page count in status
        st = storage_service.load_status(circular_id) or {}
        st["page_count"] = page_count
        storage_service.save_status(circular_id, st)

        storage_service.update_state(circular_id, ProcessingState.OCR_COMPLETED)

        # Stage 2: Faculty Identification & 2-Stage LLM Resolution
        storage_service.update_state(circular_id, ProcessingState.IDENTIFYING_FACULTY)
        matches, requires_review, _ = faculty_service.resolve_faculty(extracted_text)
        storage_service.save_faculty_matches(circular_id, [m.model_dump() for m in matches])

        # Stage 3: Summarize circular content separately from recipient extraction.
        verified_names = [m.standard_name for m in matches if m.is_verified]
        summary = summary_service.generate_summary(extracted_text, verified_names)
            
        storage_service.save_summary(circular_id, summary)

        # Stage 4: Determine next state
        if requires_review:
            storage_service.update_state(
                circular_id, 
                ProcessingState.REQUIRES_REVIEW,
                "Requires manual verification of faculty recipients or To/Copy To sections."
            )
        else:
            storage_service.update_state(circular_id, ProcessingState.READY_TO_SEND)
            
        logger.info(f"Pipeline completed for {circular_id}. Status: {storage_service.load_status(circular_id).get('current_state')}")

    except Exception as e:
        logger.error(f"Error in circular pipeline for {circular_id}: {e}", exc_info=True)
        storage_service.update_state(circular_id, ProcessingState.FAILED, f"Processing error: {str(e)}")

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard():
    """Retrieve high-level dashboard metrics and recent circulars."""
    return storage_service.get_dashboard_stats()

@router.get("/circulars", response_model=List[CircularStatusResponse])
def list_circulars():
    """Retrieve history of all processed circulars."""
    return storage_service.list_all_circulars()

@router.post("/circulars/upload", response_model=CircularStatusResponse)
async def upload_circular(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Uploads a circular document (PDF or image).
    Prevents new upload if an existing circular remains unresolved.
    Saves document and triggers background processing pipeline.
    """
    # 1. Enforce single active circular lock
    unresolved_id = storage_service.has_unresolved_circular()
    if unresolved_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot upload a new circular: Circular '{unresolved_id}' is currently active/unresolved. Please complete, send, or resolve it first."
        )

    # 2. Validate file extension
    filename = file.filename or "document.pdf"
    ext = Path(filename).suffix.lower()
    if ext not in settings.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats: {', '.join(settings.SUPPORTED_EXTENSIONS)}"
        )

    # 3. Read content and validate size
    content = await file.read()
    file_size = len(content)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
        )
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # 4. Generate new circular ID & create local storage directory
    circular_id = storage_service.generate_next_circular_id()
    circ_dir = storage_service.create_circular_folder(
        circular_id=circular_id,
        original_filename=filename,
        file_type=ext.lstrip("."),
        file_size=file_size,
        page_count=1
    )

    # 5. Save original document unmodified
    saved_doc_path = circ_dir / f"original{ext}"
    with open(saved_doc_path, "wb") as f:
        f.write(content)

    logger.info(f"Stored circular {circular_id} at {saved_doc_path}")

    # 6. Schedule background pipeline
    background_tasks.add_task(execute_circular_pipeline, circular_id)

    # 7. Return initial response
    status_data = storage_service.load_status(circular_id)
    return CircularStatusResponse(
        circular_id=circular_id,
        filename=filename,
        file_type=ext.lstrip("."),
        file_size_bytes=file_size,
        page_count=1,
        current_state=ProcessingState.UPLOADED,
        created_at=status_data.get("created_at", ""),
        updated_at=status_data.get("updated_at", ""),
        error_message=None,
        summary=None,
        has_extracted_text=False,
        matches_count=0,
        verified_matches_count=0,
        pending_review_count=0,
        emails_sent_count=0,
        emails_failed_count=0,
        can_proceed_to_send=False,
        can_retry_emails=False
    )

@router.get("/circulars/{circular_id}", response_model=CircularStatusResponse)
def get_circular_details(circular_id: str):
    """Retrieve circular metadata and status."""
    status_data = storage_service.load_status(circular_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Circular not found")
        
    state = ProcessingState(status_data.get("current_state", ProcessingState.UPLOADED.value))
    return CircularStatusResponse(
        circular_id=status_data.get("circular_id", circular_id),
        filename=status_data.get("filename", "document.pdf"),
        file_type=status_data.get("file_type", "pdf"),
        file_size_bytes=status_data.get("file_size_bytes", 0),
        page_count=status_data.get("page_count", 1),
        current_state=state,
        created_at=status_data.get("created_at", ""),
        updated_at=status_data.get("updated_at", ""),
        error_message=status_data.get("error_message"),
        summary=status_data.get("summary"),
        has_extracted_text=status_data.get("has_extracted_text", False),
        matches_count=status_data.get("matches_count", 0),
        verified_matches_count=status_data.get("verified_matches_count", 0),
        pending_review_count=status_data.get("pending_review_count", 0),
        emails_sent_count=status_data.get("emails_sent_count", 0),
        emails_failed_count=status_data.get("emails_failed_count", 0),
        can_proceed_to_send=state in (ProcessingState.FACULTY_IDENTIFIED, ProcessingState.READY_TO_SEND),
        can_retry_emails=status_data.get("emails_failed_count", 0) > 0
    )

@router.get("/circulars/{circular_id}/status")
def get_circular_status(circular_id: str):
    """Lightweight endpoint for frontend polling of current status."""
    status_data = storage_service.load_status(circular_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Circular not found")
    return status_data

@router.get("/circulars/{circular_id}/text")
def get_circular_extracted_text(circular_id: str):
    """Retrieve full consolidated extracted text."""
    text = storage_service.get_extracted_text(circular_id)
    return {"circular_id": circular_id, "extracted_text": text}

@router.get("/circulars/{circular_id}/summary")
def get_circular_summary(circular_id: str):
    """Retrieve generated 2-3 line summary."""
    summary = storage_service.get_summary(circular_id)
    return {"circular_id": circular_id, "summary": summary}

@router.get("/circulars/{circular_id}/faculty", response_model=List[FacultyMatch])
def get_circular_faculty_matches(circular_id: str):
    """Retrieve identified faculty matches."""
    matches_raw = storage_service.get_faculty_matches(circular_id)
    return [FacultyMatch(**m) for m in matches_raw]

@router.post("/circulars/{circular_id}/review", response_model=CircularStatusResponse)
def submit_faculty_review(
    circular_id: str,
    review_data: ReviewSubmissionRequest,
    background_tasks: BackgroundTasks
):
    """
    Submits user review decisions for ambiguous or identified faculty members.
    Allows confirming, rejecting, or replacing candidates with standard faculty.
    """
    status_data = storage_service.load_status(circular_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Circular not found")

    matches_raw = storage_service.get_faculty_matches(circular_id)
    matches_dict = {m["original_reference"]: m for m in matches_raw}

    for item in review_data.reviews:
        ref = item.original_reference
        if ref in matches_dict:
            target = matches_dict[ref]
            if item.action == "REJECT":
                target["verification_status"] = "REJECTED"
                target["is_verified"] = False
                target["manual_override"] = True
            elif item.replacement_faculty_id:
                rep_faculty = faculty_service.get_faculty_by_id(item.replacement_faculty_id)
                if not rep_faculty or not rep_faculty.email:
                    raise HTTPException(
                        status_code=400,
                        detail="Selected faculty does not have a usable email address."
                    )
                target["standard_name"] = rep_faculty.standard_name
                target["faculty_id"] = rep_faculty.id
                target["department"] = rep_faculty.department
                target["email"] = rep_faculty.email
                target["verification_status"] = "MANUALLY_CONFIRMED"
                target["is_verified"] = True
                target["manual_override"] = True
                target["matching_explanation"] = f"Manually assigned to {rep_faculty.standard_name} by user."
            elif item.action == "CONFIRM":
                faculty = faculty_service.get_faculty_by_id(target.get("faculty_id", ""))
                if faculty and faculty.email:
                    target["standard_name"] = faculty.standard_name
                    target["faculty_id"] = faculty.id
                    target["department"] = faculty.department
                    target["email"] = faculty.email
                    target["verification_status"] = "MANUALLY_CONFIRMED"
                    target["is_verified"] = True
                    target["manual_override"] = True

    updated_matches = list(matches_dict.values())
    storage_service.save_faculty_matches(circular_id, updated_matches)

    # Check if any ambiguous or unresolved candidates still remain
    still_ambiguous = any(
        m.get("verification_status") == "AMBIGUOUS"
        for m in updated_matches
    )

    if still_ambiguous:
        storage_service.update_state(circular_id, ProcessingState.REQUIRES_REVIEW)
    else:
        storage_service.update_state(circular_id, ProcessingState.READY_TO_SEND)

    # If requested to auto-send upon completing review
    if review_data.auto_proceed_to_send and not still_ambiguous:
        background_tasks.add_task(email_service.send_circular_emails, circular_id)

    return get_circular_details(circular_id)

@router.post("/circulars/{circular_id}/send")
def send_emails(
    circular_id: str,
    req: SendEmailRequest,
    background_tasks: BackgroundTasks
):
    """Initiates automated email delivery via Resend."""
    status_data = storage_service.load_status(circular_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Circular not found")
    if email_service.is_dispatching(circular_id) or status_data.get("current_state") == ProcessingState.SENDING_EMAILS:
        raise HTTPException(status_code=409, detail="Email delivery is already in progress for this circular.")

    background_tasks.add_task(
        email_service.send_circular_emails,
        circular_id,
        req.subject,
        req.summary_override
    )
    return {"message": "Email delivery initiated in background", "circular_id": circular_id}

@router.post("/circulars/{circular_id}/retry")
def retry_failed_emails(
    circular_id: str,
    req: RetryEmailRequest,
    background_tasks: BackgroundTasks
):
    """Retries sending failed emails without resending already delivered ones."""
    status_data = storage_service.load_status(circular_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Circular not found")
    if email_service.is_dispatching(circular_id) or status_data.get("current_state") == ProcessingState.SENDING_EMAILS:
        raise HTTPException(status_code=409, detail="Email delivery is already in progress for this circular.")

    background_tasks.add_task(
        email_service.retry_failed_emails,
        circular_id,
        req.recipient_ids
    )
    return {"message": "Email retries initiated in background", "circular_id": circular_id}

@router.get("/circulars/{circular_id}/emails", response_model=List[EmailRecipientRecord])
def get_circular_email_records(circular_id: str):
    """Retrieve detailed email delivery records for each recipient."""
    records_raw = storage_service.get_email_records(circular_id)
    return [EmailRecipientRecord(**r) for r in records_raw]

@router.get("/circulars/{circular_id}/document")
def download_circular_document(circular_id: str):
    """Serves the original uploaded document unmodified."""
    doc_path = storage_service.get_document_path(circular_id)
    if not doc_path or not doc_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found")
        
    media_type = "application/pdf" if doc_path.suffix.lower() == ".pdf" else f"image/{doc_path.suffix.lstrip('.')}"
    return FileResponse(
        path=str(doc_path),
        filename=doc_path.name,
        media_type=media_type
    )

@router.post("/circulars/{circular_id}/dismiss")
def dismiss_circular(circular_id: str):
    """
    Allows user to mark an unresolved or failed circular as resolved/dismissed,
    releasing the upload lock so another document can be processed.
    """
    status_data = storage_service.load_status(circular_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Circular not found")
        
    storage_service.update_state(circular_id, ProcessingState.COMPLETED, "Manually marked as resolved by user.")
    return {"message": f"Circular {circular_id} dismissed/resolved.", "circular_id": circular_id}

@router.post("/circulars/{circular_id}/reprocess", response_model=CircularStatusResponse)
def reprocess_circular(circular_id: str, background_tasks: BackgroundTasks):
    """
    Re-runs the automated OCR, faculty identification, and summary pipeline
    on the already uploaded document without requiring re-upload.
    """
    status_data = storage_service.load_status(circular_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Circular not found")

    background_tasks.add_task(execute_circular_pipeline, circular_id)
    storage_service.update_state(circular_id, ProcessingState.UPLOADED)
    return get_circular_details(circular_id)
