import React, { useState } from 'react';
import { 
  Users, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  HelpCircle, 
  ArrowRight,
  ShieldCheck,
  Send,
  Mail,
  Building,
  Sparkles
} from 'lucide-react';
import { submitFacultyReview } from '../services/api';

export default function FacultyVerificationView({ 
  circularId, 
  matches = [], 
  facultyDirectory = [], 
  onReviewSubmitted,
  onProceedToSend
}) {
  const [reviews, setReviews] = useState({});
  const [replacements, setReplacements] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const ambiguousCount = matches.filter((m) => {
    const selectedFaculty = facultyDirectory.find((f) => f.id === replacements[m.original_reference]);
    if (selectedFaculty?.email) return false;
    return (
      m.verification_status === 'AMBIGUOUS' ||
      !m.is_verified ||
      m.faculty_id === 'UNKNOWN' ||
      !m.email
    );
  }).length;

  const handleAction = (ref, action) => {
    const selectedFacultyId = replacements[ref];
    const nextAction = action === 'CONFIRM' && selectedFacultyId ? 'REPLACE' : action;

    setReviews((prev) => ({
      ...prev,
      [ref]: nextAction,
    }));

    if (action === 'REJECT') {
      setReplacements((prev) => {
        const next = { ...prev };
        delete next[ref];
        return next;
      });
    }
  };

  const handleReplacement = (ref, targetFacultyId) => {
    if (!targetFacultyId) {
      setReplacements((prev) => {
        const next = { ...prev };
        delete next[ref];
        return next;
      });
      setReviews((prev) => {
        const next = { ...prev };
        if (next[ref] === 'REPLACE') delete next[ref];
        return next;
      });
      return;
    }

    setReviews((prev) => ({
      ...prev,
      [ref]: 'REPLACE',
    }));
    setReplacements((prev) => ({
      ...prev,
      [ref]: targetFacultyId,
    }));
  };

  const handleSaveReviews = async (autoSend = false) => {
    try {
      setSubmitting(true);
      setError(null);

      const payload = Object.entries(reviews).map(([ref, action]) => ({
        original_reference: ref,
        faculty_id: matches.find((m) => m.original_reference === ref)?.faculty_id || 'UNKNOWN',
        action: action,
        replacement_faculty_id: replacements[ref] || null,
      }));

      // If user clicks "Confirm All & Proceed", ensure all unreviewed are confirmed
      if (payload.length === 0 && autoSend) {
        matches.forEach((m) => {
          payload.push({
            original_reference: m.original_reference,
            faculty_id: m.faculty_id,
            action: 'CONFIRM',
            replacement_faculty_id: null,
          });
        });
      }

      await submitFacultyReview(circularId, payload, autoSend);
      onReviewSubmitted();
    } catch (err) {
      setError(err.message || 'Failed to submit review decisions');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900">Faculty Identification & Resolution</h2>
            <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-medium border border-indigo-200">
              {matches.length} Candidates
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Intended recipients extracted strictly from <strong>To:</strong> and <strong>Copy To:</strong> sections and resolved against institutional directory.
          </p>
        </div>

        {ambiguousCount > 0 ? (
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs font-medium">
            <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
            <span>{ambiguousCount} {ambiguousCount === 1 ? 'match' : 'matches'} requires review</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs font-medium">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            <span>All identities verified</span>
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs">
          {error}
        </div>
      )}

      {/* Matches List */}
      {matches.length === 0 ? (
        <div className="p-8 text-center text-slate-500">
          <Users className="h-8 w-8 text-slate-300 mx-auto mb-2" />
          <p className="text-sm font-medium">No faculty recipients identified yet.</p>
          <p className="text-xs text-slate-400 mt-1">
            Ensure the circular has readable "To:" or "Copy To:" sections.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {matches.map((m, idx) => {
            const currentDecision = reviews[m.original_reference];
            const isAmbiguous = m.verification_status === 'AMBIGUOUS';
            const isRejected = currentDecision === 'REJECT' || m.verification_status === 'REJECTED';
            const selectedFaculty = facultyDirectory.find((f) => f.id === replacements[m.original_reference]);
            const resolvedName = selectedFaculty?.standard_name || m.standard_name;
            const resolvedId = selectedFaculty?.id || m.faculty_id;
            const resolvedDepartment = selectedFaculty?.department || m.department;
            const resolvedEmail = selectedFaculty?.email || m.email;
            const scorePercent = Math.round(m.similarity_score * 100);

            return (
              <div 
                key={`${m.original_reference}-${idx}`}
                className={`p-4 sm:p-5 rounded-xl border transition-all ${
                  isRejected 
                    ? 'border-slate-200 bg-slate-50/70 opacity-60'
                    : isAmbiguous && !currentDecision
                    ? 'border-amber-300 bg-amber-50/40 ring-1 ring-amber-300'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
              >
                <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                  {/* Left Column: Faculty Details */}
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        Section: {m.section_found}
                      </span>
                      <StatusPill status={currentDecision ? `MANUAL: ${currentDecision}` : m.verification_status} />
                      {selectedFaculty ? (
                        <span className="text-xs text-emerald-700 font-medium">Manual faculty selection</span>
                      ) : m.similarity_score > 0 && (
                        <span className="text-xs text-slate-500 font-mono">
                          Confidence: <strong>{scorePercent}%</strong>
                        </span>
                      )}
                    </div>

                    <div className="pt-1">
                      <div className="text-xs text-slate-400 uppercase tracking-wider font-medium">
                        Extracted In Document:
                      </div>
                      <div className="text-sm font-semibold text-slate-900 font-mono">
                        "{m.original_reference}"
                      </div>
                    </div>

                    <div className="pt-1">
                      <div className="text-xs text-slate-400 uppercase tracking-wider font-medium">
                        Resolved Canonical Faculty:
                      </div>
                      <div className="text-sm font-bold text-indigo-900 flex items-center gap-2">
                        <span>{resolvedName}</span>
                        {resolvedId !== 'UNKNOWN' && (
                          <span className="text-xs font-mono bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200 font-normal">
                            {resolvedId}
                          </span>
                        )}
                      </div>
                      {resolvedDepartment && (
                        <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                          <Building className="h-3 w-3 text-slate-400" />
                          <span>{resolvedDepartment}</span>
                        </div>
                      )}
                      {resolvedEmail && (
                        <div className="text-xs text-slate-600 flex items-center gap-1 mt-0.5 font-mono">
                          <Mail className="h-3 w-3 text-slate-400" />
                          <span>{resolvedEmail}</span>
                        </div>
                      )}
                    </div>

                    {/* Explanations */}
                    <div className="bg-slate-50/80 p-3 rounded-lg border border-slate-100 text-xs space-y-1 mt-2">
                      <div className="text-slate-700">
                        <strong className="text-slate-900">Evidence:</strong> {m.supporting_evidence || 'Direct entry in recipient list'}
                      </div>
                      <div className="text-slate-600">
                        <strong className="text-slate-900">Reasoning:</strong> {m.matching_explanation}
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Manual Resolution Actions */}
                  <div className="flex flex-col sm:flex-row lg:flex-col items-start lg:items-end gap-2 shrink-0 pt-2 lg:pt-0">
                    <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                      Verification Action
                    </span>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        disabled={submitting || (m.faculty_id === 'UNKNOWN' && !selectedFaculty)}
                        onClick={() => handleAction(m.original_reference, 'CONFIRM')}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors flex items-center gap-1 ${
                          currentDecision === 'CONFIRM' || currentDecision === 'REPLACE' || (!currentDecision && m.verification_status === 'AUTO_VERIFIED')
                            ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                            : 'bg-white hover:bg-emerald-50 text-emerald-700 border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed'
                        }`}
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Confirm
                      </button>

                      <button
                        type="button"
                        onClick={() => handleAction(m.original_reference, 'REJECT')}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors flex items-center gap-1 ${
                          currentDecision === 'REJECT'
                            ? 'bg-rose-600 text-white border-rose-600 shadow-sm'
                            : 'bg-white hover:bg-rose-50 text-rose-700 border-slate-200'
                        }`}
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        Exclude
                      </button>
                    </div>

                    {/* Replacement dropdown */}
                    <div className="w-full sm:w-auto mt-1">
                      <select
                        value={replacements[m.original_reference] || ''}
                        onChange={(e) => handleReplacement(m.original_reference, e.target.value)}
                        className="text-xs bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 hover:border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500 max-w-[210px] truncate"
                      >
                        <option value="">Map to Other Faculty...</option>
                        {facultyDirectory.map((f) => (
                          <option key={f.id} value={f.id}>
                            {f.standard_name} ({f.id})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Bottom Actions Bar */}
      {matches.length > 0 && (
        <div className="border-t border-slate-100 pt-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-xs text-slate-500">
            Only verified and confirmed recipients will be queued for email notification.
          </p>

          <div className="flex items-center gap-3">
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleSaveReviews(false)}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-medium rounded-lg transition-colors"
            >
              {submitting ? 'Saving...' : 'Save Decisions'}
            </button>

            <button
              type="button"
              disabled={submitting}
              onClick={() => handleSaveReviews(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
            >
              <CheckCircle2 className="h-4 w-4" />
              <span>Confirm & Proceed to Dispatch</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function StatusPill({ status }) {
  const isAuto = status === 'AUTO_VERIFIED';
  const isAmbiguous = status === 'AMBIGUOUS';
  const isRejected = status === 'REJECTED' || status.includes('REJECT');
  const isManual = status.includes('MANUAL') || status === 'MANUALLY_CONFIRMED';

  if (isAuto) {
    return (
      <span className="text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full inline-flex items-center gap-1">
        <CheckCircle2 className="h-3 w-3" /> Auto-Verified
      </span>
    );
  }
  if (isAmbiguous) {
    return (
      <span className="text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-300 px-2 py-0.5 rounded-full inline-flex items-center gap-1">
        <AlertTriangle className="h-3 w-3" /> Ambiguous / Needs Review
      </span>
    );
  }
  if (isRejected) {
    return (
      <span className="text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 px-2 py-0.5 rounded-full inline-flex items-center gap-1">
        <XCircle className="h-3 w-3" /> Excluded
      </span>
    );
  }
  return (
    <span className="text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full inline-flex items-center gap-1">
      <CheckCircle2 className="h-3 w-3" /> Confirmed
    </span>
  );
}
