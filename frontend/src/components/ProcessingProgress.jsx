import React from 'react';
import { 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  XCircle, 
  Loader2, 
  FileText, 
  Users, 
  Send,
  Eye
} from 'lucide-react';
import { StateBadge } from './Dashboard';

export default function ProcessingProgress({ 
  circular, 
  activeView, 
  setActiveView 
}) {
  if (!circular) return null;

  const {
    circular_id,
    filename,
    file_type,
    page_count,
    current_state,
    error_message,
    matches_count,
    verified_matches_count,
    pending_review_count,
    emails_sent_count,
    emails_failed_count
  } = circular;

  const steps = [
    { id: 'ocr', label: '1. OCR & Preprocessing', desc: 'PyMuPDF, PaddleOCR, TrOCR', done: ['OCR_COMPLETED', 'IDENTIFYING_FACULTY', 'FACULTY_IDENTIFIED', 'REQUIRES_REVIEW', 'READY_TO_SEND', 'SENDING_EMAILS', 'COMPLETED', 'PARTIALLY_COMPLETED'].includes(current_state), active: current_state === 'PROCESSING_OCR' },
    { id: 'faculty', label: '2. Faculty Resolution', desc: 'To/Copy To, Embeddings, Groq', done: ['FACULTY_IDENTIFIED', 'REQUIRES_REVIEW', 'READY_TO_SEND', 'SENDING_EMAILS', 'COMPLETED', 'PARTIALLY_COMPLETED'].includes(current_state), active: current_state === 'IDENTIFYING_FACULTY' },
    { id: 'review', label: '3. Verification & Summary', desc: 'Ambiguities check & 2-3 line summary', done: ['READY_TO_SEND', 'SENDING_EMAILS', 'COMPLETED', 'PARTIALLY_COMPLETED'].includes(current_state), active: current_state === 'REQUIRES_REVIEW', alert: current_state === 'REQUIRES_REVIEW' },
    { id: 'email', label: '4. Resend Delivery', desc: 'PDF attachment & independent status', done: ['COMPLETED'].includes(current_state), active: current_state === 'SENDING_EMAILS', partial: current_state === 'PARTIALLY_COMPLETED', failed: current_state === 'FAILED' },
  ];

  const isProcessing = ['PROCESSING_OCR', 'IDENTIFYING_FACULTY', 'SENDING_EMAILS'].includes(current_state);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 sm:p-6 space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-slate-900 text-base">{circular_id}</span>
            <StateBadge state={current_state} />
            {isProcessing && (
              <span className="flex items-center gap-1 text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded font-medium">
                <Loader2 className="h-3 w-3 animate-spin" />
                Working...
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            File: <strong>{filename}</strong> • {page_count} {page_count === 1 ? 'page' : 'pages'} • Type: {file_type.toUpperCase()}
          </p>
        </div>

        {/* View Switcher Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={() => setActiveView('text')}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors flex items-center gap-1.5 ${
              activeView === 'text'
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
            }`}
          >
            <FileText className="h-3.5 w-3.5" />
            Extracted Text
          </button>

          <button
            onClick={() => setActiveView('faculty')}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors flex items-center gap-1.5 ${
              activeView === 'faculty'
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
            }`}
          >
            <Users className="h-3.5 w-3.5" />
            Faculty ({verified_matches_count})
            {pending_review_count > 0 && (
              <span className="h-2 w-2 rounded-full bg-amber-500" />
            )}
          </button>

          <button
            onClick={() => setActiveView('summary')}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors flex items-center gap-1.5 ${
              activeView === 'summary'
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
            }`}
          >
            <Eye className="h-3.5 w-3.5" />
            Summary
          </button>

          <button
            onClick={() => setActiveView('email')}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors flex items-center gap-1.5 ${
              activeView === 'email'
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
            }`}
          >
            <Send className="h-3.5 w-3.5" />
            Emails ({emails_sent_count})
            {emails_failed_count > 0 && (
              <span className="bg-rose-500 text-white text-[10px] px-1 rounded-full font-bold">
                {emails_failed_count}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Stepper Progress Pipeline */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {steps.map((st, idx) => {
          let borderClass = 'border-slate-200 bg-slate-50/50';
          let icon = <Clock className="h-4 w-4 text-slate-400" />;

          if (st.done) {
            borderClass = 'border-emerald-300 bg-emerald-50/40 text-emerald-950';
            icon = <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
          } else if (st.active) {
            borderClass = 'border-indigo-400 bg-indigo-50/60 ring-2 ring-indigo-200';
            icon = <Loader2 className="h-4 w-4 text-indigo-600 animate-spin" />;
          } else if (st.alert) {
            borderClass = 'border-amber-400 bg-amber-50/70 ring-2 ring-amber-200';
            icon = <AlertTriangle className="h-4 w-4 text-amber-600 animate-pulse" />;
          } else if (st.failed) {
            borderClass = 'border-rose-300 bg-rose-50/40';
            icon = <XCircle className="h-4 w-4 text-rose-600" />;
          }

          return (
            <div key={st.id} className={`p-3.5 rounded-lg border transition-all ${borderClass}`}>
              <div className="flex items-center gap-2">
                {icon}
                <span className="text-xs font-semibold text-slate-900">{st.label}</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1 pl-6 leading-tight">
                {st.desc}
              </p>
            </div>
          );
        })}
      </div>

      {/* Error banner if failed */}
      {error_message && (
        <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5">
          <XCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">Notice / Error Detail:</div>
            <div className="mt-0.5 text-rose-700">{error_message}</div>
          </div>
        </div>
      )}
    </div>
  );
}
