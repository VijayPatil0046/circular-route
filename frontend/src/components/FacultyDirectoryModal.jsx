import React, { useState } from 'react';
import { 
  X, 
  Users, 
  Search, 
  Building, 
  Mail, 
  Tag 
} from 'lucide-react';

export default function FacultyDirectoryModal({ 
  isOpen, 
  onClose, 
  faculties = [] 
}) {
  const [search, setSearch] = useState('');

  if (!isOpen) return null;

  const filtered = faculties.filter((f) => {
    const q = search.toLowerCase();
    return (
      f.standard_name.toLowerCase().includes(q) ||
      f.id.toLowerCase().includes(q) ||
      (f.department && f.department.toLowerCase().includes(q)) ||
      f.aliases.some((a) => a.toLowerCase().includes(q)) ||
      f.email.toLowerCase().includes(q)
    );
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-50 text-indigo-700 rounded-lg">
              <Users className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">Institutional Faculty Directory</h2>
              <p className="text-xs text-slate-500">
                Local directory (<code className="text-slate-700 font-mono">faculty.json</code>) • {faculties.length} Faculty Members
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Search */}
        <div className="px-6 py-3 border-b border-slate-100 bg-slate-50/50">
          <div className="relative">
            <Search className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search faculty by name, department, ID, alias, or email..."
              className="w-full text-xs bg-white border border-slate-200 rounded-lg pl-9 pr-3 py-2 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        </div>

        {/* Body List */}
        <div className="p-6 overflow-y-auto space-y-3 flex-1">
          {filtered.length === 0 ? (
            <div className="text-center py-8 text-slate-400 text-xs">
              No faculty found matching "{search}".
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {filtered.map((fac) => (
                <div
                  key={fac.id}
                  className="p-4 rounded-xl border border-slate-200 bg-white hover:border-indigo-200 hover:shadow-xs transition-all space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="font-bold text-slate-900 text-sm">{fac.standard_name}</div>
                      <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                        <Building className="h-3 w-3 text-slate-400" />
                        <span>{fac.department}</span>
                        {fac.designation && <span>• {fac.designation}</span>}
                      </div>
                    </div>
                    <span className="font-mono text-xs font-semibold bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                      {fac.id}
                    </span>
                  </div>

                  <div className="text-xs text-slate-600 flex items-center gap-1 font-mono">
                    <Mail className="h-3 w-3 text-slate-400" />
                    <span>{fac.email}</span>
                  </div>

                  {fac.aliases && fac.aliases.length > 0 && (
                    <div className="pt-1.5 border-t border-slate-100">
                      <div className="flex items-center gap-1 text-[11px] text-slate-400 mb-1">
                        <Tag className="h-2.5 w-2.5" />
                        <span>Known Aliases / OCR variations:</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {fac.aliases.map((alias, i) => (
                          <span
                            key={i}
                            className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono"
                          >
                            {alias}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-100 bg-slate-50 text-right">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-800 text-xs font-medium rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
