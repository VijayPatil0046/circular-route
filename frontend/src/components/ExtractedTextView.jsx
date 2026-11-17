import React, { useState } from 'react';
import { 
  FileText, 
  Copy, 
  Check, 
  Download, 
  ExternalLink,
  Layers
} from 'lucide-react';

export default function ExtractedTextView({ 
  circularId, 
  extractedText, 
  pageCount 
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!extractedText) return;
    navigator.clipboard.writeText(extractedText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lineCount = extractedText ? extractedText.split('\n').length : 0;
  const wordCount = extractedText ? extractedText.trim().split(/\s+/).filter(Boolean).length : 0;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900">Extracted Document Text</h2>
            <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-medium">
              OCR Consolidated
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Preserved page breaks, printed and handwritten text lines, dates, stamps, and recipient headers.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-medium rounded-lg border border-slate-200 transition-colors flex items-center gap-1.5"
            title="Copy all extracted text"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-600" />
                <span className="text-emerald-700">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                <span>Copy Text</span>
              </>
            )}
          </button>

          <a
            href={`/api/circulars/${circularId}/document`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-medium rounded-lg border border-indigo-200 transition-colors flex items-center gap-1.5"
            title="View original uploaded PDF/image"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Original Document</span>
          </a>
        </div>
      </div>

      {/* Metrics bar */}
      <div className="flex items-center gap-4 text-xs text-slate-500 bg-slate-50 px-3 py-2 rounded-lg border border-slate-100 font-mono">
        <span>Lines: <strong className="text-slate-800">{lineCount}</strong></span>
        <span>•</span>
        <span>Words: <strong className="text-slate-800">{wordCount}</strong></span>
        <span>•</span>
        <span>Storage: <strong className="text-slate-800">backend/circulars/{circularId}/extracted_text.txt</strong></span>
      </div>

      {/* Text Area Content */}
      <div className="relative">
        <pre className="font-mono text-xs text-slate-800 bg-slate-900/5 p-4 rounded-lg overflow-x-auto max-h-[500px] whitespace-pre-wrap leading-relaxed border border-slate-200">
          {extractedText || '[No text extracted yet or document is processing...]'}
        </pre>
      </div>
    </div>
  );
}
