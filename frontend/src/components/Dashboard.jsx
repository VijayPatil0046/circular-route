import React, { useEffect, useState } from 'react';
import { 
  FileText, 
  Send, 
  AlertTriangle, 
  Clock, 
  ArrowRight, 
  CheckCircle, 
  XCircle,
  Upload,
  RefreshCw,
  ExternalLink,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

const CIRCULARS_PER_PAGE = 10;

export default function Dashboard({ 
  stats, 
  circulars = [],
  loading, 
  onRefresh, 
  onSelectCircular, 
  onNavigateToUpload,
  onDismissCircular
}) {
  const [currentPage, setCurrentPage] = useState(1);

  const {
    total_circulars = 0,
    total_emails_sent = 0,
    total_emails_failed = 0,
    circulars_awaiting_review = 0,
    active_unresolved_circular = null,
    recent_circulars = []
  } = stats || {};

  const circularList = circulars.length > 0 ? circulars : recent_circulars;
  const totalPages = Math.max(1, Math.ceil(circularList.length / CIRCULARS_PER_PAGE));
  const pageStart = (currentPage - 1) * CIRCULARS_PER_PAGE;
  const pageCirculars = circularList.slice(pageStart, pageStart + CIRCULARS_PER_PAGE);

  useEffect(() => {
    setCurrentPage(1);
  }, [circularList.length]);

  useEffect(() => {
    if (currentPage > totalPages) setCurrentPage(totalPages);
  }, [currentPage, totalPages]);

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="h-8 w-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Operations Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time status of institutional circular extraction, faculty resolution, and delivery.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onRefresh}
            className="p-2 text-slate-500 hover:text-slate-800 rounded-md border border-slate-200 hover:bg-slate-50 transition-colors"
            title="Refresh dashboard"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            onClick={onNavigateToUpload}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
          >
            <Upload className="h-4 w-4" />
            Upload Circular
          </button>
        </div>
      </div>

      {/* Active Unresolved Banner if present */}
      {active_unresolved_circular && (
        <div className="rounded-xl border border-amber-300 bg-amber-50/70 p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-amber-100 text-amber-800 rounded-lg shrink-0">
              <Clock className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-amber-900 text-sm">
                  Active Workflow in Progress: {active_unresolved_circular}
                </span>
                <span className="text-xs bg-amber-200/80 text-amber-800 px-2 py-0.5 rounded font-medium">
                  Uploads Locked
                </span>
              </div>
              <p className="text-xs text-amber-700 mt-0.5">
                A circular is currently being processed or awaiting review/email dispatch. New uploads are paused to maintain single-document consistency.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
            <button
              onClick={() => onSelectCircular(active_unresolved_circular)}
              className="px-3.5 py-1.5 bg-amber-800 hover:bg-amber-900 text-white text-xs font-medium rounded-md transition-colors flex items-center gap-1.5 shadow-sm"
            >
              Resume Workflow
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => onDismissCircular(active_unresolved_circular)}
              className="px-2.5 py-1.5 text-xs text-amber-800 hover:text-amber-950 hover:bg-amber-100 rounded-md border border-amber-300 transition-colors"
              title="Unlock upload by marking as resolved"
            >
              Dismiss / Unlock
            </button>
          </div>
        </div>
      )}

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Total Circulars */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Processed Circulars</span>
            <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600">
              <FileText className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-slate-900">{total_circulars}</span>
          </div>
          <div className="mt-2 text-xs text-slate-500">
            Institutional documents cataloged
          </div>
        </div>

        {/* Metric 2: Total Emails Sent */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Emails Dispatched</span>
            <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
              <Send className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-slate-900">{total_emails_sent}</span>
          </div>
          <div className="mt-2 text-xs text-emerald-600 flex items-center gap-1 font-medium">
            <CheckCircle className="h-3.5 w-3.5" /> Verified recipient deliveries
          </div>
        </div>

        {/* Metric 3: Failed Deliveries */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Delivery Failures</span>
            <div className={`p-2 rounded-lg ${total_emails_failed > 0 ? 'bg-rose-50 text-rose-600' : 'bg-slate-50 text-slate-400'}`}>
              <XCircle className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-slate-900">{total_emails_failed}</span>
          </div>
          <div className="mt-2 text-xs text-slate-500">
            {total_emails_failed > 0 ? (
              <span className="text-rose-600 font-medium">Eligible for 1-click retry</span>
            ) : (
              'All dispatches healthy'
            )}
          </div>
        </div>

        {/* Metric 4: Awaiting Review */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Awaiting Review</span>
            <div className={`p-2 rounded-lg ${circulars_awaiting_review > 0 ? 'bg-amber-50 text-amber-600' : 'bg-slate-50 text-slate-400'}`}>
              <AlertTriangle className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-slate-900">{circulars_awaiting_review}</span>
          </div>
          <div className="mt-2 text-xs text-slate-500">
            {circulars_awaiting_review > 0 ? (
              <span className="text-amber-600 font-medium">Requires faculty verification</span>
            ) : (
              'No pending ambiguities'
            )}
          </div>
        </div>
      </div>

      {/* Recent Circulars Section */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">Recently Processed Circulars</h2>
          <span className="text-xs text-slate-500">{circularList.length} total</span>
        </div>

        {circularList.length === 0 ? (
          <div className="p-8 text-center">
            <FileText className="h-10 w-10 text-slate-300 mx-auto mb-3" />
            <h3 className="text-sm font-medium text-slate-700">No circulars processed yet</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Upload your first institutional circular PDF or scanned image to begin automated OCR extraction, faculty resolution, and email delivery.
            </p>
            <button
              onClick={onNavigateToUpload}
              className="mt-4 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg inline-flex items-center gap-1.5"
            >
              <Upload className="h-3.5 w-3.5" />
              Upload Now
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50/80 border-b border-slate-200 text-xs font-medium text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">Circular ID</th>
                  <th className="px-5 py-3">Document</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-center">Recipients</th>
                  <th className="px-5 py-3 text-center">Emails Sent</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pageCirculars.map((circ) => {
                  return (
                    <tr key={circ.circular_id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-5 py-3.5 font-semibold text-slate-900 font-mono text-xs">
                        {circ.circular_id}
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="font-medium text-slate-800 text-sm truncate max-w-[220px]">
                          {circ.filename}
                        </div>
                        <div className="text-xs text-slate-400">
                          {circ.page_count} {circ.page_count === 1 ? 'page' : 'pages'} • {circ.file_type.toUpperCase()}
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <StateBadge state={circ.current_state} />
                      </td>
                      <td className="px-5 py-3.5 text-center text-xs text-slate-600">
                        <span className="font-semibold text-slate-900">{circ.verified_matches_count}</span>
                        {circ.pending_review_count > 0 && (
                          <span className="text-amber-600 ml-1">({circ.pending_review_count} pending)</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-center text-xs">
                        <span className="text-emerald-700 font-medium">{circ.emails_sent_count} sent</span>
                        {circ.emails_failed_count > 0 && (
                          <span className="text-rose-600 font-medium ml-1.5">• {circ.emails_failed_count} failed</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <button
                          onClick={() => onSelectCircular(circ.circular_id)}
                          className="px-3 py-1.5 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-700 text-xs font-medium rounded-md transition-colors inline-flex items-center gap-1"
                        >
                          View
                          <ArrowRight className="h-3 w-3" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {circularList.length > 0 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-slate-200 px-5 py-3">
            <p className="text-xs text-slate-500">
              Showing {pageStart + 1}–{Math.min(pageStart + CIRCULARS_PER_PAGE, circularList.length)} of {circularList.length} circulars
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                disabled={currentPage === 1}
                className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                Previous
              </button>
              <span className="min-w-[5rem] text-center text-xs text-slate-600">
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                disabled={currentPage === totalPages}
                className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function StateBadge({ state }) {
  const configs = {
    UPLOADED: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200', label: 'Uploaded' },
    PROCESSING_OCR: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', label: 'Processing OCR' },
    OCR_COMPLETED: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200', label: 'OCR Extracted' },
    IDENTIFYING_FACULTY: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200', label: 'Resolving Faculty' },
    FACULTY_IDENTIFIED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', label: 'Faculty Resolved' },
    REQUIRES_REVIEW: { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-300', label: 'Requires Review' },
    READY_TO_SEND: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', label: 'Ready to Send' },
    SENDING_EMAILS: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', label: 'Sending Emails' },
    COMPLETED: { bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200', label: 'Completed' },
    PARTIALLY_COMPLETED: { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200', label: 'Partially Sent' },
    FAILED: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', label: 'Failed' },
  };

  const c = configs[state] || { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200', label: state };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${c.bg} ${c.text} ${c.border}`}>
      {c.label}
    </span>
  );
}
