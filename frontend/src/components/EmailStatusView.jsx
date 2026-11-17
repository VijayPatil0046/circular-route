import React, { useState } from 'react';
import { 
  Send, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  RefreshCw, 
  AlertCircle, 
  Mail, 
  ExternalLink,
  ShieldCheck,
  FileCheck
} from 'lucide-react';
import { retryCircularEmails, sendCircularEmails } from '../services/api';

export default function EmailStatusView({ 
  circularId, 
  records = [], 
  canProceedToSend, 
  canRetry, 
  onRefresh 
}) {
  const [retrying, setRetrying] = useState(false);
  const [actionError, setActionError] = useState(null);

  const handleRetry = async (recipientId = null) => {
    try {
      setRetrying(true);
      setActionError(null);
      await retryCircularEmails(circularId, recipientId ? [recipientId] : null);
      setTimeout(onRefresh, 1000);
    } catch (err) {
      setActionError(err.message || 'Retry failed');
    } finally {
      setRetrying(false);
    }
  };

  const handleInitialSend = async () => {
    try {
      setRetrying(true);
      setActionError(null);
      await sendCircularEmails(circularId);
      setTimeout(onRefresh, 1000);
    } catch (err) {
      setActionError(err.message || 'Send failed');
    } finally {
      setRetrying(false);
    }
  };

  const sentCount = records.filter((r) => ['SENT', 'DELIVERED'].includes(r.status)).length;
  const failedCount = records.filter((r) => r.status === 'FAILED').length;
  const sendingCount = records.filter((r) => r.status === 'SENDING').length;
  const pendingCount = records.filter((r) => r.status === 'PENDING').length;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900">Email Delivery Tracking</h2>
            <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium">
              Resend Provider
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Independent per-recipient delivery statuses with idempotency protection and retry handling.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {failedCount > 0 && (
            <button
              type="button"
              disabled={retrying || sendingCount > 0}
              onClick={() => handleRetry(null)}
              className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${retrying ? 'animate-spin' : ''}`} />
              <span>Retry All Failed ({failedCount})</span>
            </button>
          )}

          {records.length === 0 && canProceedToSend && (
            <button
              type="button"
              disabled={retrying || sendingCount > 0}
              onClick={handleInitialSend}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
            >
              <Send className="h-4 w-4" />
              <span>Dispatch Emails Now</span>
            </button>
          )}

          <button
            type="button"
            onClick={onRefresh}
            className="p-2 border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-600 transition-colors"
            title="Refresh statuses"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {actionError && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs">
          {actionError}
        </div>
      )}

      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-emerald-50/50 border border-emerald-100 p-3 rounded-lg text-center">
          <div className="text-xl font-bold text-emerald-700">{sentCount}</div>
          <div className="text-[11px] font-medium text-emerald-800 uppercase tracking-wider mt-0.5">Dispatched</div>
        </div>
        <div className="bg-rose-50/50 border border-rose-100 p-3 rounded-lg text-center">
          <div className="text-xl font-bold text-rose-700">{failedCount}</div>
          <div className="text-[11px] font-medium text-rose-800 uppercase tracking-wider mt-0.5">Failed</div>
        </div>
        <div className="bg-amber-50/50 border border-amber-100 p-3 rounded-lg text-center">
          <div className="text-xl font-bold text-amber-700">{sendingCount}</div>
          <div className="text-[11px] font-medium text-amber-800 uppercase tracking-wider mt-0.5">Sending</div>
        </div>
        <div className="bg-slate-50 border border-slate-100 p-3 rounded-lg text-center">
          <div className="text-xl font-bold text-slate-700">{pendingCount}</div>
          <div className="text-[11px] font-medium text-slate-600 uppercase tracking-wider mt-0.5">Pending</div>
        </div>
      </div>

      {/* Recipient Table */}
      {records.length === 0 ? (
        <div className="p-8 text-center text-slate-500">
          <Mail className="h-8 w-8 text-slate-300 mx-auto mb-2" />
          <p className="text-sm font-medium">No email dispatches recorded yet for this circular.</p>
          <p className="text-xs text-slate-400 mt-1">
            Complete faculty verification and click Dispatch to initiate Resend delivery.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto border border-slate-200 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
              <tr>
                <th className="px-4 py-3">Faculty Recipient</th>
                <th className="px-4 py-3">Email Address</th>
                <th className="px-4 py-3">Delivery Status</th>
                <th className="px-4 py-3">Resend Message ID</th>
                <th className="px-4 py-3">Attempts</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {records.map((rec) => {
                const isSent = ['SENT', 'DELIVERED'].includes(rec.status);
                const isFailed = rec.status === 'FAILED';
                const isPending = rec.status === 'PENDING' || rec.status === 'SENDING';

                return (
                  <tr key={rec.recipient_id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">{rec.standard_name}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{rec.faculty_id}</div>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-700">
                      {rec.email}
                    </td>
                    <td className="px-4 py-3">
                      <EmailStatusBadge status={rec.status} />
                      {rec.error_message && (
                        <div className="text-[10px] text-rose-600 mt-1 max-w-[200px] truncate" title={rec.error_message}>
                          {rec.error_message}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-slate-500">
                      {rec.resend_message_id || '—'}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-600">
                      {rec.retry_count}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {isFailed ? (
                        <button
                          type="button"
                          disabled={retrying || sendingCount > 0}
                          onClick={() => handleRetry(rec.recipient_id)}
                          className="px-2.5 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded border border-rose-200 transition-colors font-medium inline-flex items-center gap-1"
                        >
                          <RefreshCw className="h-3 w-3" />
                          Retry
                        </button>
                      ) : isSent ? (
                        <span className="text-[11px] text-emerald-600 font-medium inline-flex items-center gap-1">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Delivered
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-400">Queued</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Attachment info note */}
      <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-xs text-slate-500 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileCheck className="h-4 w-4 text-emerald-600" />
          <span>Attachment: Original circular PDF attached automatically to every recipient email.</span>
        </div>
        <a
          href={`/api/circulars/${circularId}/document`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-600 hover:underline flex items-center gap-1 font-medium"
        >
          View Attachment
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  );
}

function EmailStatusBadge({ status }) {
  if (status === 'SENT' || status === 'DELIVERED') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
        <CheckCircle2 className="h-3 w-3" />
        {status}
      </span>
    );
  }
  if (status === 'FAILED') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
        <XCircle className="h-3 w-3" />
        FAILED
      </span>
    );
  }
  if (status === 'SENDING') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
        <Clock className="h-3 w-3 animate-spin" />
        SENDING
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
      <Clock className="h-3 w-3" />
      PENDING
    </span>
  );
}
