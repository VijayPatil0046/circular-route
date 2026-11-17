import os
import json
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..core.config import settings
from ..core.state import ProcessingState, is_state_unresolved
from ..models.schemas import (
    CircularStatusResponse,
    FacultyMatch,
    EmailRecipientRecord,
    DashboardStats,
)

class StorageService:
    def __init__(self, circulars_dir: Path = settings.CIRCULARS_DIR):
        self.circulars_dir = circulars_dir
        self.circulars_dir.mkdir(parents=True, exist_ok=True)

    def generate_next_circular_id(self) -> str:
        """Finds the next circular ID in sequence: CIRCULAR_001, CIRCULAR_002, etc."""
        existing = [d.name for d in self.circulars_dir.iterdir() if d.is_dir() and d.name.startswith("CIRCULAR_")]
        max_id = 0
        for name in existing:
            parts = name.split("_")
            if len(parts) >= 2 and parts[1].isdigit():
                max_id = max(max_id, int(parts[1]))
        return f"CIRCULAR_{max_id + 1:03d}"

    def get_circular_dir(self, circular_id: str) -> Path:
        return self.circulars_dir / circular_id

    def has_unresolved_circular(self) -> Optional[str]:
        """
        Checks if there is an unresolved circular that prevents new uploads.
        Returns the unresolved circular ID if found, else None.
        """
        for c in self.list_all_circulars():
            if is_state_unresolved(c.current_state):
                return c.circular_id
        return None

    def create_circular_folder(self, circular_id: str, original_filename: str, file_type: str, file_size: int, page_count: int = 1) -> Path:
        circ_dir = self.get_circular_dir(circular_id)
        circ_dir.mkdir(parents=True, exist_ok=True)
        
        now = datetime.now().isoformat()
        status_data = {
            "circular_id": circular_id,
            "filename": original_filename,
            "file_type": file_type,
            "file_size_bytes": file_size,
            "page_count": page_count,
            "current_state": ProcessingState.UPLOADED.value,
            "created_at": now,
            "updated_at": now,
            "error_message": None,
            "summary": None,
            "has_extracted_text": False,
            "matches_count": 0,
            "verified_matches_count": 0,
            "pending_review_count": 0,
            "emails_sent_count": 0,
            "emails_failed_count": 0,
        }
        self.save_status(circular_id, status_data)
        return circ_dir

    def get_status_path(self, circular_id: str) -> Path:
        return self.get_circular_dir(circular_id) / "status.json"

    def load_status(self, circular_id: str) -> Optional[Dict[str, Any]]:
        status_file = self.get_status_path(circular_id)
        if not status_file.exists():
            return None
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_status(self, circular_id: str, status_data: Dict[str, Any]) -> None:
        status_data["updated_at"] = datetime.now().isoformat()
        status_file = self.get_status_path(circular_id)
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2)

    def update_state(self, circular_id: str, state: ProcessingState, error_message: Optional[str] = None) -> None:
        status = self.load_status(circular_id) or {}
        status["current_state"] = state.value
        if error_message:
            status["error_message"] = error_message
        self.save_status(circular_id, status)

    def save_extracted_text(self, circular_id: str, text: str) -> None:
        circ_dir = self.get_circular_dir(circular_id)
        txt_path = circ_dir / "extracted_text.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        status = self.load_status(circular_id) or {}
        status["has_extracted_text"] = bool(text.strip())
        self.save_status(circular_id, status)

    def get_extracted_text(self, circular_id: str) -> str:
        txt_path = self.get_circular_dir(circular_id) / "extracted_text.txt"
        if not txt_path.exists():
            return ""
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def save_summary(self, circular_id: str, summary: str) -> None:
        circ_dir = self.get_circular_dir(circular_id)
        summary_path = circ_dir / "summary.txt"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)
            
        status = self.load_status(circular_id) or {}
        status["summary"] = summary
        self.save_status(circular_id, status)

    def get_summary(self, circular_id: str) -> str:
        summary_path = self.get_circular_dir(circular_id) / "summary.txt"
        if not summary_path.exists():
            return ""
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def save_faculty_matches(self, circular_id: str, matches: List[Dict[str, Any]]) -> None:
        circ_dir = self.get_circular_dir(circular_id)
        matches_path = circ_dir / "faculty_matches.json"
        with open(matches_path, "w", encoding="utf-8") as f:
            json.dump(matches, f, indent=2)
            
        status = self.load_status(circular_id) or {}
        status["matches_count"] = len(matches)
        status["verified_matches_count"] = sum(1 for m in matches if m.get("is_verified", False))
        status["pending_review_count"] = sum(1 for m in matches if m.get("verification_status") == "AMBIGUOUS" or not m.get("is_verified", False))
        self.save_status(circular_id, status)

    def get_faculty_matches(self, circular_id: str) -> List[Dict[str, Any]]:
        matches_path = self.get_circular_dir(circular_id) / "faculty_matches.json"
        if not matches_path.exists():
            return []
        try:
            with open(matches_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_email_records(self, circular_id: str, records: List[Dict[str, Any]]) -> None:
        circ_dir = self.get_circular_dir(circular_id)
        email_path = circ_dir / "email_records.json"
        with open(email_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
            
        status = self.load_status(circular_id) or {}
        status["emails_sent_count"] = sum(1 for r in records if r.get("status") in ("SENT", "DELIVERED"))
        status["emails_failed_count"] = sum(1 for r in records if r.get("status") == "FAILED")
        self.save_status(circular_id, status)

    def get_email_records(self, circular_id: str) -> List[Dict[str, Any]]:
        email_path = self.get_circular_dir(circular_id) / "email_records.json"
        if not email_path.exists():
            return []
        try:
            with open(email_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def get_document_path(self, circular_id: str) -> Optional[Path]:
        circ_dir = self.get_circular_dir(circular_id)
        if not circ_dir.exists():
            return None
        # Look for original.* or original.pdf
        for ext in settings.SUPPORTED_EXTENSIONS:
            cand = circ_dir / f"original{ext}"
            if cand.exists():
                return cand
        # Also check any file starting with original
        for f in circ_dir.iterdir():
            if f.name.startswith("original."):
                return f
        return None

    def list_all_circulars(self) -> List[CircularStatusResponse]:
        results = []
        if not self.circulars_dir.exists():
            return []
            
        dirs = [d for d in self.circulars_dir.iterdir() if d.is_dir() and d.name.startswith("CIRCULAR_")]
        # Sort descending by ID / creation
        dirs.sort(key=lambda d: d.name, reverse=True)
        
        for d in dirs:
            status_data = self.load_status(d.name)
            if status_data:
                state = ProcessingState(status_data.get("current_state", ProcessingState.UPLOADED.value))
                can_send = state in (ProcessingState.FACULTY_IDENTIFIED, ProcessingState.READY_TO_SEND)
                can_retry = status_data.get("emails_failed_count", 0) > 0
                
                resp = CircularStatusResponse(
                    circular_id=status_data.get("circular_id", d.name),
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
                    can_proceed_to_send=can_send,
                    can_retry_emails=can_retry,
                )
                results.append(resp)
        return results

    def get_dashboard_stats(self) -> DashboardStats:
        circulars = self.list_all_circulars()
        total = len(circulars)
        total_sent = sum(c.emails_sent_count for c in circulars)
        total_failed = sum(c.emails_failed_count for c in circulars)
        awaiting_review = sum(1 for c in circulars if c.current_state == ProcessingState.REQUIRES_REVIEW)
        active_unresolved = self.has_unresolved_circular()
        
        return DashboardStats(
            total_circulars=total,
            total_emails_sent=total_sent,
            total_emails_failed=total_failed,
            circulars_awaiting_review=awaiting_review,
            active_unresolved_circular=active_unresolved,
            recent_circulars=circulars[:10],
        )

storage_service = StorageService()
