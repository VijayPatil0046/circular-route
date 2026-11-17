# CircularRoute – Institutional Circular AI Processing & Automated Faculty Email Notification

**CircularRoute** is an AI-powered institutional circular processing and automated faculty email notification application. It reads institutional circulars (multi-page PDFs and scanned images), extracts printed and handwritten English text, identifies the intended faculty members from the `To:` and `Copy To:` sections, resolves their names into standard faculty identities using local embeddings and Groq LLM, generates concise 2–3 line summaries, and automatically dispatches emails with the original circular attached using Resend.

---

## Architecture Overview

```
                      ┌─────────────────────────────────────┐
                      │    Uploaded Circular (PDF / Image)  │
                      └──────────────────┬──────────────────┘
                                         │
                                         ▼
                             [ PyMuPDF Document Reader ]
                                         │
                                         ▼
                           [ OpenCV Preprocessing Engine ]
                     (Deskew, CLAHE contrast, Denoise, Lines)
                                         │
                     ┌───────────────────┴───────────────────┐
                     │                                       │
                     ▼                                       ▼
       [ PaddleOCR PP-OCRv5 ]             [ Microsoft TrOCR Base Handwritten ]
     (Printed Text Recognition)                 (Handwritten Text Lines)
                     │                                       │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                       Consolidated Text (extracted_text.txt)
                                         │
                                         ▼
                      [ Targeted Section Extraction Engine ]
                      (Strictly 'To:' and 'Copy To:' Sections)
                                         │
                                         ▼
                       [ Faculty Name Resolution Pipeline ]
               ┌─────────────────────────┴─────────────────────────┐
               │ 1. Exact string & normalized match                │
               │ 2. Alias, abbreviation, & initial matching        │
               │ 3. sentence-transformers/all-MiniLM-L6-v2 (Local) │
               │ 4. Groq qwen/qwen3.8-27b (Contextual Resolution)  │
               └─────────────────────────┬─────────────────────────┘
                                         │
                                         ▼
                        [ Verified Faculty Directory ]
                     (Canonical Email Lookup from faculty.json)
                                         │
                     ┌───────────────────┴───────────────────┐
                     │                                       │
                     ▼                                       ▼
         [ Groq 2-3 Line Summary ]               [ Ambiguity Gate ]
               (summary.txt)               (Manual verification UI if needed)
                     │                                       │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                             [ Resend Email Delivery ]
                    (PDF Attachment + Per-Recipient Independent Tracking)
```

---

## Technology Stack

| Component | Technology | Description |
|---|---|---|
| **Frontend** | React, Vite, Tailwind CSS | Enterprise dashboard inspired by shadcn/ui aesthetic |
| **Backend** | Python, FastAPI, Uvicorn | RESTful API with background task orchestration |
| **PDF Processing** | PyMuPDF (`fitz`) | Multi-page PDF extraction and high-DPI page rendering |
| **Image Preprocessing** | OpenCV | Deskewing, CLAHE contrast enhancement, denoising, line segmentation |
| **Printed Text OCR** | PaddleOCR PP-OCRv5 | Bounding box detection and printed English text recognition |
| **Handwritten OCR** | Microsoft TrOCR Base | `microsoft/trocr-base-handwritten` for line crops and notes |
| **LLM Provider** | Groq | `qwen/qwen3.8-27b` for contextual faculty resolution and summary |
| **Embedding Model** | sentence-transformers | `all-MiniLM-L6-v2` loaded locally for in-memory cosine similarity |
| **Faculty Data** | Local JSON | `backend/faculty.json` (20 institutional faculty records) |
| **Email Delivery** | Resend | Multi-recipient delivery with idempotency and PDF attachments |
| **Storage** | Local Filesystem | Structured folders under `backend/circulars/CIRCULAR_XXX/` |

---

## Directory Structure

```text
gen_ai_circular_route/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── circulars.py          # Upload, status, review, send, retry endpoints
│   │   │   ├── faculty.py            # Faculty directory endpoints
│   │   │   └── system.py             # System config and health endpoints
│   │   ├── core/
│   │   │   ├── config.py             # App settings loaded from .env
│   │   │   └── state.py              # 11 Processing states and upload lock guards
│   │   ├── models/
│   │   │   └── schemas.py            # Pydantic schemas for matches, emails, and circulars
│   │   ├── services/
│   │   │   ├── ocr_service.py        # PyMuPDF, OpenCV, PaddleOCR, and TrOCR pipeline
│   │   │   ├── faculty_service.py    # To/Copy To parser, all-MiniLM-L6-v2, and Groq resolver
│   │   │   ├── summary_service.py    # 2-3 line concise executive summary generator
│   │   │   ├── email_service.py      # Resend dispatch, PDF attachment, and idempotency
│   │   │   └── storage_service.py    # Local filesystem storage manager
│   │   ├── utils/
│   │   │   ├── image_preprocessing.py# Deskew, CLAHE, denoising, line segmentation
│   │   │   └── text_normalizer.py    # Title stripping, token similarity, recipient parser
│   │   └── main.py                   # FastAPI initialization with CORS
│   ├── circulars/                    # Local storage for all circulars
│   │   └── CIRCULAR_001/
│   │       ├── original.pdf          # Preserved original document
│   │       ├── extracted_text.txt    # Consolidated OCR output
│   │       ├── summary.txt           # Generated 2-3 line summary
│   │       ├── faculty_matches.json  # Identified faculty records and scores
│   │       ├── email_records.json    # Per-recipient Resend delivery records
│   │       └── status.json           # Real-time processing state
│   ├── tests/
│   │   └── test_circular_workflow.py # Full end-to-end integration test
│   ├── faculty.json                  # Local institutional directory (20 faculty members)
│   ├── .env                          # Backend environment variables
│   ├── .env.example                  # Template configuration
│   ├── requirements.txt              # Backend dependencies
│   └── main.py                       # Uvicorn entrypoint
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx            # Header, tab navigation, and status pills
│   │   │   ├── Dashboard.jsx         # Metrics, recent circulars, active workflow alert
│   │   │   ├── UploadCircular.jsx    # Drag-and-drop upload & 1-click evaluation samples
│   │   │   ├── ProcessingProgress.jsx# 4-stage pipeline stepper & live progress polling
│   │   │   ├── ExtractedTextView.jsx # Formatted OCR output inspection & document download
│   │   │   ├── FacultyVerificationView.jsx # Review, confirm, reject, or replace faculty
│   │   │   ├── SummaryView.jsx       # 2-3 line summary inspector and email subject editor
│   │   │   ├── EmailStatusView.jsx   # Per-recipient tracking (SENT/FAILED) & 1-click retry
│   │   │   ├── CircularHistory.jsx   # Historical archive with search and state filtering
│   │   │   ├── FacultyDirectoryModal.jsx # 20 faculty members inspector modal
│   │   │   └── SystemConfigModal.jsx # In-browser API key configuration modal
│   │   ├── services/
│   │   │   └── api.js                # Frontend REST API client
│   │   ├── App.jsx                   # Master state container & polling loop
│   │   ├── main.jsx                  # React DOM root
│   │   └── index.css                 # Tailwind CSS styling
│   ├── package.json
│   └── vite.config.js
│
├── start_backend.bat                 # 1-click Windows backend launcher
├── start_frontend.bat                # 1-click Windows frontend launcher
└── run_all.bat                       # 1-click launcher for both services
```

---

## Key Features & Business Logic Implementation

### 1. Targeted Recipient Identification (`To` & `Copy To` Sections)
- As specified in Section 6, the system does not indiscriminately scan the entire document body for faculty names.
- It parses the `To:` and `Copy To:` / `C.C.:` sections.
- Generic institutional positions (`Principal`, `Registrar`, `Head of Department`, `Accounts Section`) are never treated as faculty members unless mapped to a specific person in `faculty.json`.
- Event coordinators mentioned only in the circular body are excluded from the recipient list.

### 2. Multi-Stage Name Resolution
- **Exact & Normalized Matching**: Strips titles (`Dr.`, `Prof.`, `Professor`, `Mr.`), punctuation, and whitespace variations.
- **Alias & Abbreviation Matching**: Matches initials and known variants (e.g. `Dr. S. Seema`, `Seema`, `S. Seema` -> `Dr. Seema S.`).
- **Local In-Memory Embeddings**: Uses `sentence-transformers/all-MiniLM-L6-v2` to compute cosine similarity directly against directory members without external vector databases.
- **Groq LLM Reasoning**: Passes extracted context to `qwen/qwen3.8-27b` to resolve identities without hallucinating names.
- **Strict Directory Validation**: Canonical email addresses are retrieved exclusively from `faculty.json` by verified `faculty_id`. The LLM never invents email addresses.
- **Ambiguity Detection**: Candidates with confidence scores below 0.70 or close competition between candidates are flagged as `AMBIGUOUS` and routed to the user for manual verification.

### 3. Processing State Machine & Single-Upload Lock
The backend persists 11 workflow states in `status.json`:
1. `UPLOADED`
2. `PROCESSING_OCR`
3. `OCR_COMPLETED`
4. `IDENTIFYING_FACULTY`
5. `FACULTY_IDENTIFIED`
6. `REQUIRES_REVIEW`
7. `READY_TO_SEND`
8. `SENDING_EMAILS`
9. `COMPLETED`
10. `PARTIALLY_COMPLETED`
11. `FAILED`

**Upload Lock Rule**: The application enforces a lock that prevents new uploads while a circular is being processed or remains unresolved (`REQUIRES_REVIEW`, `READY_TO_SEND`). Once resolved or dismissed by the user, new uploads are accepted.

### 4. Email Delivery via Resend
- Sends notification with the 2–3 line summary in HTML and plaintext.
- Attaches the original uploaded circular document.
- Independent per-recipient status tracking: `PENDING`, `SENDING`, `SENT`, `FAILED`.
- Supports 1-click retry for failed deliveries without re-sending to already delivered recipients (protected by idempotency keys).

---

## Quick Start & Running the Application

### Option A: Using the Launcher Scripts (Windows)
Double-click `run_all.bat` (or run it from PowerShell/CMD). This opens:
- **Backend API**: `http://localhost:8000/docs`
- **Frontend Web UI**: `http://localhost:5173`

### Option B: Manual Startup

#### 1. Backend
```powershell
# In project root:
$env:PYTHONPATH="backend"
.venv\Scripts\activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend
```powershell
cd frontend
pnpm run dev
```

Open your browser at `http://localhost:5173`.

---

## Running Verification Tests

Run the full end-to-end integration test suite:
```powershell
$env:PYTHONPATH="backend"
.venv\Scripts\python.exe backend\tests\test_circular_workflow.py
```

This tests:
1. Directory loading of all 20 faculty members.
2. Accurate candidate extraction from `To` and `Copy To` sections.
3. Name normalization, alias matching, and `all-MiniLM-L6-v2` embedding similarity.
4. Exclusion of institutional positions (`Principal`, `Registrar`).
5. 2-3 line summary generation.
6. Local storage file persistence (`extracted_text.txt`, `summary.txt`, `faculty_matches.json`, `status.json`).
7. Per-recipient Resend email dispatch with idempotency.
