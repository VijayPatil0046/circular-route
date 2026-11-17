import React, { useState } from 'react';
import { 
  History, 
  Search, 
  Filter, 
  ArrowRight, 
  RefreshCw, 
  FileText, 
  Download,
  AlertTriangle,
  CheckCircle2
} from 'lucide-react';
import { StateBadge } from './Dashboard';

export default function CircularHistory({ 
  circulars = [], 
  onSelectCircular, 
  onRefresh 
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterState, setFilterState] = useState('ALL');

  const filtered = circulars.filter((c) => {
    const matchesSearch = 
      c.circular_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.filename.toLowerCase().includes(searchTerm.toLowerCase());

    if (!matchesSearch) return false;

    if (filterState === 'ALL') return true;
    if (filterState === 'REVIEW') return c.current_state === 'REQUIRES_REVIEW';
    if (filterState === 'COMPLETED') return c.current_state === 'COMPLETED';
    if (filterState === 'FAILED') return c.current_state === 'FAILED' || c.emails_failed_count > 0;
    return true;
  });

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900">Circular Archive & History</h2>
            <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium">
              {circulars.length} Total
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Historical catalog of all uploaded institutional circulars, extracted texts, and delivery statuses.
          </p>
        </div>

        <button
          type="button"
          onClick={onRefresh}
          className="p-2 border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-600 transition-colors self-start sm:self-center"
          title="Refresh history"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by ID or filename..."
            className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-2 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto">
          {['ALL', 'COMPLETED', 'REVIEW', 'FAILED'].map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilterState(f)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap ${
                filterState === f
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              {f === 'ALL' ? 'All' : f === 'REVIEW' ? 'Requires Review' : f.charAt(0) + f.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="p-8 text-center text-slate-500">
          <FileText className="h-8 w-8 text-slate-300 mx-auto mb-2" />
          <p className="text-sm font-medium">No circulars matching your criteria.</p>
        </div>
      ) : (
        <div className="overflow-x-auto border border-slate-200 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
              <tr>
                <th className="px-4 py-3">ID & Date</th>
                <th className="px-4 py-3">Filename</th>
                <th className="px-4 py-3">Processing State</th>
                <th className="px-4 py-3 text-center">Faculty Matches</th>
                <th className="px-4 py-3 text-center">Email Deliveries</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((c) => (
                <tr key={c.circular_id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="px-4 py-3.5">
                    <div className="font-mono font-bold text-slate-900">{c.circular_id}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      {c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="font-medium text-slate-800 truncate max-w-[200px]" title={c.filename}>
                      {c.filename}
                    </div>
                    <div className="text-[10px] text-slate-400">
                      {c.page_count} pages • {(c.file_size_bytes / 1024).toFixed(0)} KB
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    <StateBadge state={c.current_state} />
                  </td>
                  <td className="px-4 py-3.5 text-center">
                    <span className="font-semibold text-slate-900">{c.verified_matches_count}</span>
                    <span className="text-slate-400"> / {c.matches_count}</span>
                    {c.pending_review_count > 0 && (
                      <span className="text-amber-600 font-medium ml-1">({c.pending_review_count} review)</span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-center">
                    <span className="text-emerald-700 font-medium">{c.emails_sent_count} sent</span>
                    {c.emails_failed_count > 0 && (
                      <span className="text-rose-600 font-medium ml-1">• {c.emails_failed_count} failed</span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-right space-x-1.5 whitespace-nowrap">
                    <a
                      href={`/api/circulars/${c.circular_id}/document`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 text-slate-500 hover:text-slate-800 rounded hover:bg-slate-100 inline-flex transition-colors"
                      title="Download Original"
                    >
                      <Download className="h-3.5 w-3.5" />
                    </a>
                    <button
                      type="button"
                      onClick={() => onSelectCircular(c.circular_id)}
                      className="px-2.5 py-1 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-700 font-medium rounded transition-colors inline-flex items-center gap-1"
                    >
                      Inspect
                      <ArrowRight className="h-3 w-3" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
