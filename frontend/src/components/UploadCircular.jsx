import React, { useState, useRef } from 'react';
import { 
  Upload, 
  FileText, 
  AlertCircle, 
  CheckCircle, 
  Clock, 
  ArrowRight,
  FileCheck,
  Sparkles,
  HelpCircle
} from 'lucide-react';
import { uploadCircular } from '../services/api';

export default function UploadCircular({ 
  activeUnresolvedId, 
  onUploadSuccess, 
  onViewUnresolved,
  onDismissUnresolved
}) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const isLocked = Boolean(activeUnresolvedId);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (isLocked) return;
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a circular document to upload.');
      return;
    }

    try {
      setUploading(true);
      setError(null);
      const res = await uploadCircular(file);
      onUploadSuccess(res.circular_id);
    } catch (err) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  // Helper to generate a mock realistic institutional circular PDF/image for instant 1-click test
  const handleLoadSample = (sampleType) => {
    let filename = 'Department_Circular_Meeting.pdf';
    let contentText = '';

    if (sampleType === 'academic') {
      filename = 'Academic_Council_Notice_2026.pdf';
      contentText = `%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 750 >> stream
BT
/F1 16 Tf
50 720 Td
(NATIONAL INSTITUTE OF ENGINEERING & TECHNOLOGY) Tj
/F1 12 Tf
0 -25 Td
(OFFICE OF THE PRINCIPAL & ACADEMIC CELL) Tj
0 -20 Td
(Ref: NIET/CIR/2026/042                                Date: 17th November 2026) Tj
0 -30 Td
(CIRCULAR: CURRICULUM REVISION & SYLLABUS COMMITTEE) Tj
/F1 10 Tf
0 -30 Td
(To:) Tj
0 -15 Td
(1. Dr. Seema S., Department of Computer Science & Engineering) Tj
0 -15 Td
(2. Prof. Rajesh Kumar, Department of Computer Science & Engineering) Tj
0 -15 Td
(3. Dr. Anand Kulkarni, Department of Information Science) Tj
0 -25 Td
(Copy To:) Tj
0 -15 Td
(Office of the Principal) Tj
0 -15 Td
(Office of the Registrar) Tj
0 -15 Td
(Head of Department, CSE) Tj
0 -30 Td
(The above faculty members are hereby appointed to the Curriculum Review Committee.) Tj
0 -15 Td
(You are requested to submit the revised module scheme for 2026-27 by Friday, Nov 27.) Tj
0 -15 Td
(A preparatory meeting is scheduled for Monday at 11:00 AM in Senate Hall.) Tj
0 -40 Td
(Sd/-) Tj
0 -15 Td
(Dean Academics) Tj
ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000224 00000 n 
0000001026 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
1104
%%EOF`;
    } else if (sampleType === 'exam') {
      filename = 'Exam_Duty_NBA_Circular.pdf';
      contentText = `%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 780 >> stream
BT
/F1 16 Tf
50 720 Td
(CONTROLLER OF EXAMINATIONS - AUTONOMOUS DIVISION) Tj
/F1 12 Tf
0 -25 Td
(Ref: COE/CIRCULAR/NOV/108                               Date: 17-11-2026) Tj
0 -30 Td
(CIRCULAR: SEMESTER END PRACTICAL EVALUATION & NBA DUTIES) Tj
/F1 10 Tf
0 -30 Td
(To:) Tj
0 -15 Td
(Prof. Sneha Patil, CSE Dept) Tj
0 -15 Td
(Dr. Meenakshi Sundaram, ECE Dept) Tj
0 -15 Td
(Prof. Kavitha Krishnan, ISE Dept) Tj
0 -25 Td
(Copy To:) Tj
0 -15 Td
(Controller of Examinations) Tj
0 -15 Td
(Dean Academics Nitin Gadre) Tj
0 -15 Td
(Accounts Section) Tj
0 -30 Td
(Subject: Mandatory appointment of Senior External & Internal Examiners for practical viva.) Tj
0 -15 Td
(Faculty members listed under 'To' are directed to collect question rubrics from the COE cell) Tj
0 -15 Td
(by 20th November 2026 and complete evaluation portals before 30th November.) Tj
0 -40 Td
(Sd/-) Tj
0 -15 Td
(Dr. Ramesh Babu, Autonomous Coordinator) Tj
ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000224 00000 n 
0000001056 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
1134
%%EOF`;
    }

    const blob = new Blob([contentText], { type: 'application/pdf' });
    const sampleFile = new File([blob], filename, { type: 'application/pdf' });
    setFile(sampleFile);
    setError(null);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Upload Lock Guard Alert */}
      {isLocked && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-5 shadow-sm">
          <div className="flex items-start gap-3.5">
            <Clock className="h-6 w-6 text-amber-600 shrink-0 mt-0.5 animate-pulse" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-amber-900">
                Upload Currently Locked – Unresolved Circular: {activeUnresolvedId}
              </h3>
              <p className="text-xs text-amber-700 mt-1 leading-relaxed">
                As per system design specifications, only one circular may be actively processed at a time.
                Circular <strong>{activeUnresolvedId}</strong> is currently active, awaiting review, or pending dispatch.
              </p>
              <div className="mt-3 flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => onViewUnresolved(activeUnresolvedId)}
                  className="px-3.5 py-1.5 bg-amber-800 hover:bg-amber-900 text-white text-xs font-medium rounded-lg inline-flex items-center gap-1.5 shadow-sm transition-colors"
                >
                  Go to Active Circular ({activeUnresolvedId})
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => onDismissUnresolved(activeUnresolvedId)}
                  className="px-3 py-1.5 text-xs font-medium text-amber-800 hover:text-amber-950 hover:bg-amber-100 rounded-lg border border-amber-300 transition-colors"
                >
                  Mark as Resolved & Unlock
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Card */}
      <div className={`bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8 transition-opacity ${isLocked ? 'opacity-50 pointer-events-none' : ''}`}>
        <div className="border-b border-slate-100 pb-4 mb-6">
          <h2 className="text-lg font-bold text-slate-900">Upload Institutional Circular</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Select a multi-page PDF or scanned photograph (PNG, JPG, JPEG, WEBP) of an official circular.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Dropzone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              dragOver
                ? 'border-indigo-500 bg-indigo-50/50'
                : file
                ? 'border-emerald-400 bg-emerald-50/20'
                : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50/50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp"
              onChange={handleFileChange}
              className="hidden"
            />

            {file ? (
              <div className="flex flex-col items-center">
                <div className="h-12 w-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mb-3">
                  <FileCheck className="h-6 w-6" />
                </div>
                <div className="text-sm font-semibold text-slate-900">{file.name}</div>
                <div className="text-xs text-slate-500 mt-1">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB • {file.type || 'Document'}
                </div>
                <span className="mt-3 text-xs text-indigo-600 hover:underline">
                  Click or drag to choose a different file
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="h-12 w-12 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
                  <Upload className="h-6 w-6" />
                </div>
                <div className="text-sm font-semibold text-slate-900">
                  Drag & drop circular document here, or <span className="text-indigo-600">browse</span>
                </div>
                <p className="text-xs text-slate-500 mt-1.5 max-w-sm">
                  Supports multi-page PDFs, high-resolution scans, printed and handwritten English text up to 25MB.
                </p>
              </div>
            )}
          </div>

          {/* Error display */}
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Submit Action */}
          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-slate-400">
              Files are processed locally and preserved in <code className="bg-slate-100 px-1 py-0.5 rounded">backend/circulars/</code>
            </span>

            <button
              type="submit"
              disabled={!file || uploading || isLocked}
              className={`px-5 py-2.5 text-sm font-medium rounded-lg shadow-sm transition-colors flex items-center gap-2 ${
                !file || uploading || isLocked
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white'
              }`}
            >
              {uploading ? (
                <>
                  <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Processing Upload...</span>
                </>
              ) : (
                <>
                  <FileText className="h-4 w-4" />
                  <span>Ingest & Start Extraction</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* 1-Click Sample Test Circulars */}
        <div className="mt-8 pt-6 border-t border-slate-100">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Instant 1-Click Evaluation Samples
              </span>
            </div>
            <span className="text-[11px] text-slate-400">Pre-generated official institutional circulars</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => handleLoadSample('academic')}
              className="p-3 rounded-lg border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40 text-left transition-colors group"
            >
              <div className="font-medium text-xs text-slate-800 group-hover:text-indigo-900">
                Sample A: Curriculum & Syllabus Circular
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                To: Dr. Seema S., Prof. Rajesh Kumar, Dr. Anand Kulkarni | Copy To: Principal, Registrar, HOD
              </div>
            </button>

            <button
              type="button"
              onClick={() => handleLoadSample('exam')}
              className="p-3 rounded-lg border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40 text-left transition-colors group"
            >
              <div className="font-medium text-xs text-slate-800 group-hover:text-indigo-900">
                Sample B: Examination & NBA Duty Notice
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                To: Prof. Sneha Patil, Dr. Meenakshi Sundaram, Prof. Kavitha Krishnan
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
