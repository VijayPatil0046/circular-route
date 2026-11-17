from enum import Enum
from typing import Optional
from pathlib import Path
import json

class ProcessingState(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING_OCR = "PROCESSING_OCR"
    OCR_COMPLETED = "OCR_COMPLETED"
    IDENTIFYING_FACULTY = "IDENTIFYING_FACULTY"
    FACULTY_IDENTIFIED = "FACULTY_IDENTIFIED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    READY_TO_SEND = "READY_TO_SEND"
    SENDING_EMAILS = "SENDING_EMAILS"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"

ACTIVE_PROCESSING_STATES = {
    ProcessingState.UPLOADED,
    ProcessingState.PROCESSING_OCR,
    ProcessingState.OCR_COMPLETED,
    ProcessingState.IDENTIFYING_FACULTY,
    ProcessingState.FACULTY_IDENTIFIED,
    ProcessingState.REQUIRES_REVIEW,
    ProcessingState.READY_TO_SEND,
    ProcessingState.SENDING_EMAILS,
}

TERMINAL_STATES = {
    ProcessingState.COMPLETED,
    ProcessingState.PARTIALLY_COMPLETED,
    ProcessingState.FAILED,
}

def is_state_unresolved(state: ProcessingState) -> bool:
    return state in ACTIVE_PROCESSING_STATES
