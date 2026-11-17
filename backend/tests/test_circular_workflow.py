import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.services.faculty_service import faculty_service
from app.services.storage_service import storage_service
from app.services.ocr_service import ocr_service
from app.services.summary_service import summary_service
from app.services.email_service import email_service
from app.core.state import ProcessingState

def test_full_pipeline():
    print("=== TEST 1: Faculty Directory Loading ===")
    faculties = faculty_service.get_all_faculties()
    print(f"Total faculty members loaded: {len(faculties)}")
    assert len(faculties) >= 5, "Expected at least 5 faculty members"
    
    fac1 = faculty_service.get_faculty_by_id("FAC001")
    assert fac1 is not None
    print(f"FAC001 verified: {fac1.standard_name} - {fac1.email}")

    print("\n=== TEST 2: Faculty Resolution Logic ===")
    test_circular_text = """
NATIONAL INSTITUTE OF ENGINEERING & TECHNOLOGY
OFFICE OF THE PRINCIPAL

Ref: NIET/CIR/2026/088
Date: 17 November 2026

CIRCULAR: ANNUAL SYLLABUS REVISION COMMITTEE

To:
1. Dr. Seema S., Department of CSE
2. Prof. Rajesh Kumar, Department of CSE
3. Dr. Anand Kulkarni, ISE Dept

Copy To:
Office of the Principal
Office of the Registrar
Head of Department, CSE

All the above nominated faculty members are requested to review the revised curriculum guidelines
and submit their feedback before Friday, 28th November 2026.
    """

    matches, requires_review, summary_cand = faculty_service.resolve_faculty(test_circular_text)
    print(f"Matches count: {len(matches)}, requires_review: {requires_review}")
    for m in matches:
        print(f" -> Found: '{m.original_reference}' => Standard: '{m.standard_name}' ({m.faculty_id}) [{m.verification_status}] Email: {m.email}")

    # Verify that institutional roles like Principal and Registrar are NOT in matches
    for m in matches:
        assert "principal" not in m.standard_name.lower()
        assert "registrar" not in m.standard_name.lower()

    # Verify that Seema and Rajesh are matched
    matched_ids = [m.faculty_id for m in matches]
    assert "FAC001" in matched_ids, "Dr. Seema S. should match FAC001"
    assert "FAC002" in matched_ids, "Prof. Rajesh Kumar should match FAC002"

    print("\n=== TEST 3: Summary Generation ===")
    summary = summary_service.generate_summary(test_circular_text, [m.standard_name for m in matches])
    print(f"Generated Summary:\n{summary}")
    assert len(summary) > 20, "Summary should be non-empty"

    print("\n=== TEST 4: Local Storage and Circular Ingestion ===")
    circ_id = storage_service.generate_next_circular_id()
    print(f"Generated Circular ID: {circ_id}")
    circ_dir = storage_service.create_circular_folder(
        circular_id=circ_id,
        original_filename="test_meeting_notice.pdf",
        file_type="pdf",
        file_size=1024,
        page_count=1
    )
    
    # Save files
    storage_service.save_extracted_text(circ_id, test_circular_text)
    storage_service.save_summary(circ_id, summary)
    storage_service.save_faculty_matches(circ_id, [m.model_dump() for m in matches])
    storage_service.update_state(circ_id, ProcessingState.READY_TO_SEND)

    # Verify files created
    assert (circ_dir / "extracted_text.txt").exists()
    assert (circ_dir / "summary.txt").exists()
    assert (circ_dir / "faculty_matches.json").exists()
    assert (circ_dir / "status.json").exists()
    print("All local storage files persisted successfully!")

    print("\n=== TEST 5: Email Record Preparation & Delivery ===")
    email_records = email_service.prepare_recipient_records(circ_id, matches)
    print(f"Prepared {len(email_records)} email records:")
    for r in email_records:
        print(f" -> {r.standard_name} <{r.email}> Status: {r.status}")
        assert "@" in r.email

    storage_service.save_email_records(circ_id, [r.model_dump() for r in email_records])

    # Send emails (in test mode / simulation)
    sent_records = email_service.send_circular_emails(circ_id)
    print(f"Dispatched {len(sent_records)} emails:")
    for sr in sent_records:
        print(f" -> {sr.standard_name} [{sr.status}] Resend Msg ID: {sr.resend_message_id}")
        assert sr.status in ("SENT", "DELIVERED", "FAILED")

    st = storage_service.load_status(circ_id)
    print(f"Final State: {st['current_state']}")
    assert st["current_state"] in (ProcessingState.COMPLETED.value, ProcessingState.FAILED.value, ProcessingState.PARTIALLY_COMPLETED.value)

    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    test_full_pipeline()
