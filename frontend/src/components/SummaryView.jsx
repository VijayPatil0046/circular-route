import React, { useState } from 'react';
import { 
  FileText, 
  Sparkles, 
  Edit3, 
  Check, 
  Send,
  Calendar,
  AlertCircle
} from 'lucide-react';

export default function SummaryView({ 
  circularId, 
  summary, 
  onSendEmails 
}) {
  const [editing, setEditing] = useState(false);
  const [customSummary, setCustomSummary] = useState(summary || '');
  const [subject, setSubject] = useState('');

  const currentSummary = editing ? customSummary : (summary || 'Generating summary...');

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900">Executive Circular Summary</h2>
            <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-medium border border-indigo-200 flex items-center gap-1">
              <Sparkles className="h-3 w-3" />
              Groq qwen/qwen3.8-27b
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Concise 2–3 line synthesis sent in the body of faculty notification emails.
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            if (editing) {
              setEditing(false);
            } else {
              setCustomSummary(summary);
              setEditing(true);
            }
          }}
          className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 transition-colors flex items-center gap-1.5 self-start sm:self-center"
        >
          <Edit3 className="h-3.5 w-3.5" />
          <span>{editing ? 'Lock Summary' : 'Edit Summary'}</span>
        </button>
      </div>

      {/* Summary Box */}
      <div className="rounded-xl border border-indigo-100 bg-indigo-50/30 p-5 space-y-3">
        <div className="flex items-center justify-between text-xs text-indigo-800 font-semibold uppercase tracking-wider">
          <span>Official Notification Excerpt</span>
          <span className="text-[11px] text-slate-400 font-normal">Approx 2–3 lines</span>
        </div>

        {editing ? (
          <textarea
            rows={4}
            value={customSummary}
            onChange={(e) => setCustomSummary(e.target.value)}
            className="w-full text-sm text-slate-800 bg-white border border-indigo-200 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-sans leading-relaxed"
            placeholder="Edit summary..."
          />
        ) : (
          <div className="text-sm font-medium text-slate-800 leading-relaxed pl-3 border-l-4 border-indigo-600 bg-white p-4 rounded-r-lg shadow-xs">
            {currentSummary}
          </div>
        )}
      </div>

      {/* Email Subject preview & custom action */}
      <div className="space-y-4 pt-2">
        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
            Outgoing Email Subject Line (Optional Customization)
          </label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder={`[CircularRoute Notification] Institutional Circular – ${circularId}`}
            className="w-full text-xs text-slate-800 bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-xs text-slate-500 flex items-center gap-2">
          <Calendar className="h-4 w-4 text-slate-400 shrink-0" />
          <span>
            Storage destination: <code className="text-slate-700">backend/circulars/{circularId}/summary.txt</code>
          </span>
        </div>

        <div className="border-t border-slate-100 pt-4 flex justify-end">
          <button
            type="button"
            onClick={() => onSendEmails(subject || null, editing ? customSummary : null)}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg shadow-sm transition-colors flex items-center gap-2"
          >
            <Send className="h-4 w-4" />
            <span>Approve & Dispatch Circular to Faculty</span>
          </button>
        </div>
      </div>
    </div>
  );
}
