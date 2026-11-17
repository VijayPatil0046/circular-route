import React, { useState } from 'react';
import { 
  X, 
  Settings, 
  Key, 
  CheckCircle2, 
  AlertCircle, 
  Cpu, 
  Mail,
  ShieldAlert
} from 'lucide-react';
import { updateSystemConfig } from '../services/api';

export default function SystemConfigModal({ 
  isOpen, 
  onClose, 
  config, 
  onConfigUpdated 
}) {
  const [groqKey, setGroqKey] = useState('');
  const [resendKey, setResendKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  if (!isOpen) return null;

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      setMsg(null);
      const payload = {};
      if (groqKey) payload.groq_api_key = groqKey;
      if (resendKey) payload.resend_api_key = resendKey;

      await updateSystemConfig(payload);
      setMsg({ type: 'success', text: 'Backend configuration updated successfully.' });
      onConfigUpdated();
      setTimeout(() => {
        setMsg(null);
        onClose();
      }, 1200);
    } catch (err) {
      setMsg({ type: 'error', text: err.message || 'Failed to update config' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-50 text-indigo-700 rounded-lg">
              <Settings className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">System Configuration</h2>
              <p className="text-xs text-slate-500">Local model & external API credentials</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSave} className="p-6 space-y-5">
          {/* Status Overview */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className={`p-3 rounded-lg border ${config?.groq_configured ? 'border-emerald-200 bg-emerald-50/50 text-emerald-900' : 'border-amber-200 bg-amber-50/50 text-amber-900'}`}>
              <div className="font-semibold flex items-center gap-1.5">
                <Cpu className="h-3.5 w-3.5" />
                Groq LLM
              </div>
              <div className="text-[11px] mt-1 text-slate-600">Model: {config?.groq_model || 'qwen/qwen3.8-27b'}</div>
              <div className="text-[11px] mt-0.5 font-medium">
                {config?.groq_configured ? '✓ Configured' : '⚠ Using Local Heuristics'}
              </div>
            </div>

            <div className={`p-3 rounded-lg border ${config?.resend_configured ? 'border-emerald-200 bg-emerald-50/50 text-emerald-900' : 'border-amber-200 bg-amber-50/50 text-amber-900'}`}>
              <div className="font-semibold flex items-center gap-1.5">
                <Mail className="h-3.5 w-3.5" />
                Resend Email
              </div>
              <div className="text-[11px] mt-1 text-slate-600">From: {config?.resend_from_name || 'CircularRoute'}</div>
              <div className="text-[11px] mt-0.5 font-medium">
                {config?.resend_configured ? '✓ Live Delivery' : '⚠ Simulation Mode'}
              </div>
            </div>
          </div>

          {/* Groq Key Input */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
              Groq API Key (Optional Override)
            </label>
            <div className="relative">
              <Key className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="password"
                value={groqKey}
                onChange={(e) => setGroqKey(e.target.value)}
                placeholder={config?.groq_configured ? '••••••••••••••••••••••••' : 'gsk_...'}
                className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-2 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
              />
            </div>
            <p className="text-[11px] text-slate-400">
              Powers contextual resolution & 2-3 line summary via <code className="text-slate-600 font-mono">qwen/qwen3.8-27b</code>.
            </p>
          </div>

          {/* Resend Key Input */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
              Resend API Key (Optional Override)
            </label>
            <div className="relative">
              <Key className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="password"
                value={resendKey}
                onChange={(e) => setResendKey(e.target.value)}
                placeholder={config?.resend_configured ? '••••••••••••••••••••••••' : 're_...'}
                className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-2 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
              />
            </div>
            <p className="text-[11px] text-slate-400">
              Sender configured as: <code className="text-slate-600 font-mono">{config?.resend_from_email || 'notifications@circularroute.aclclouds.online'}</code>.
            </p>
          </div>

          {/* Local storage note */}
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-slate-500 text-[11px] flex items-start gap-2">
            <ShieldAlert className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
            <span>
              All keys are stored strictly in backend <code className="font-mono text-slate-700">backend/.env</code> and never exposed to the client or source control.
            </span>
          </div>

          {msg && (
            <div className={`p-3 rounded-lg text-xs flex items-center gap-2 ${msg.type === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'}`}>
              {msg.type === 'success' ? <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" /> : <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />}
              <span>{msg.text}</span>
            </div>
          )}

          <div className="border-t border-slate-100 pt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-800 rounded-lg hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-xs font-medium bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-sm transition-colors"
            >
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
