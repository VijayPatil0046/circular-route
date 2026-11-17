import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import UploadCircular from './components/UploadCircular';
import ProcessingProgress from './components/ProcessingProgress';
import ExtractedTextView from './components/ExtractedTextView';
import FacultyVerificationView from './components/FacultyVerificationView';
import SummaryView from './components/SummaryView';
import EmailStatusView from './components/EmailStatusView';
import CircularHistory from './components/CircularHistory';
import FacultyDirectoryModal from './components/FacultyDirectoryModal';
import SystemConfigModal from './components/SystemConfigModal';

import {
  fetchDashboard,
  fetchCirculars,
  fetchCircular,
  fetchCircularText,
  fetchCircularSummary,
  fetchCircularFaculty,
  fetchCircularEmails,
  fetchFaculties,
  fetchSystemConfig,
  dismissCircular,
  reprocessCircular,
  sendCircularEmails,
} from './services/api';

export default function App() {
  // Navigation
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard', 'active', 'history'
  const [activeView, setActiveView] = useState('faculty'); // 'text', 'faculty', 'summary', 'email'

  // Data
  const [dashboardStats, setDashboardStats] = useState(null);
  const [circulars, setCirculars] = useState([]);
  const [faculties, setFaculties] = useState([]);
  const [systemConfig, setSystemConfig] = useState(null);

  // Active circular details
  const [activeCircularId, setActiveCircularId] = useState(null);
  const [circularDetails, setCircularDetails] = useState(null);
  const [extractedText, setExtractedText] = useState('');
  const [summary, setSummary] = useState('');
  const [facultyMatches, setFacultyMatches] = useState([]);
  const [emailRecords, setEmailRecords] = useState([]);

  // Modals
  const [isFacultyModalOpen, setIsFacultyModalOpen] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);

  // Loading & refresh state
  const [loading, setLoading] = useState(false);

  // 1. Initial Load
  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);
      const [dash, circs, facs, conf] = await Promise.all([
        fetchDashboard().catch(() => null),
        fetchCirculars().catch(() => []),
        fetchFaculties().catch(() => []),
        fetchSystemConfig().catch(() => null),
      ]);

      if (dash) setDashboardStats(dash);
      if (circs) setCirculars(circs);
      if (facs) setFaculties(facs);
      if (conf) setSystemConfig(conf);

      // If there is an unresolved active circular, set it as current
      if (dash?.active_unresolved_circular && !activeCircularId) {
        setActiveCircularId(dash.active_unresolved_circular);
      }
    } catch (e) {
      console.error('Failed to load initial application data', e);
    } finally {
      setLoading(false);
    }
  }, [activeCircularId]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // 2. Load Selected Circular Deep Details
  const loadCircularData = useCallback(async (id) => {
    if (!id) return;
    try {
      const [details, txtResp, sumResp, facResp, emailsResp] = await Promise.all([
        fetchCircular(id).catch(() => null),
        fetchCircularText(id).catch(() => ({ extracted_text: '' })),
        fetchCircularSummary(id).catch(() => ({ summary: '' })),
        fetchCircularFaculty(id).catch(() => []),
        fetchCircularEmails(id).catch(() => []),
      ]);

      if (details) setCircularDetails(details);
      if (txtResp) setExtractedText(txtResp.extracted_text || '');
      if (sumResp) setSummary(sumResp.summary || '');
      if (facResp) setFacultyMatches(facResp || []);
      if (emailsResp) setEmailRecords(emailsResp || []);

      // Intelligent default subview
      if (details) {
        if (details.current_state === 'REQUIRES_REVIEW') {
          setActiveView('faculty');
        } else if (['SENDING_EMAILS', 'COMPLETED', 'PARTIALLY_COMPLETED'].includes(details.current_state)) {
          setActiveView('email');
        } else if (details.current_state === 'READY_TO_SEND') {
          setActiveView('summary');
        }
      }
    } catch (err) {
      console.error(`Error loading circular data for ${id}`, err);
    }
  }, []);

  useEffect(() => {
    if (activeCircularId) {
      loadCircularData(activeCircularId);
    }
  }, [activeCircularId, loadCircularData]);

  // 3. Polling for Active Processing States
  useEffect(() => {
    if (!activeCircularId || !circularDetails) return;

    const isProcessing = [
      'UPLOADED',
      'PROCESSING_OCR',
      'IDENTIFYING_FACULTY',
      'SENDING_EMAILS',
    ].includes(circularDetails.current_state);

    if (!isProcessing) return;

    const interval = setInterval(() => {
      loadCircularData(activeCircularId);
      fetchDashboard().then(setDashboardStats).catch(() => {});
    }, 2000);

    return () => clearInterval(interval);
  }, [activeCircularId, circularDetails, loadCircularData]);

  // Handlers
  const handleSelectCircular = (id) => {
    setActiveCircularId(id);
    setActiveTab('active');
  };

  const handleUploadSuccess = (newId) => {
    setActiveCircularId(newId);
    setActiveTab('active');
    loadInitialData();
  };

  const handleDismissCircular = async (id) => {
    try {
      await dismissCircular(id);
      loadInitialData();
      if (activeCircularId === id) {
        loadCircularData(id);
      }
    } catch (e) {
      alert(e.message || 'Failed to dismiss circular');
    }
  };

  const handleReprocessCircular = async (id) => {
    try {
      await reprocessCircular(id);
      loadInitialData();
      loadCircularData(id);
    } catch (e) {
      alert(e.message || 'Failed to reprocess circular');
    }
  };

  const handleSendEmails = async (subject, summaryOverride) => {
    if (!activeCircularId) return;
    try {
      await sendCircularEmails(activeCircularId, subject, summaryOverride);
      setActiveView('email');
      setTimeout(() => {
        loadCircularData(activeCircularId);
        loadInitialData();
      }, 1000);
    } catch (e) {
      alert(e.message || 'Failed to send emails');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemConfig={systemConfig}
        activeUnresolvedId={dashboardStats?.active_unresolved_circular}
        onOpenSettings={() => setIsConfigModalOpen(true)}
        onOpenFacultyDirectory={() => setIsFacultyModalOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Tab 1: Dashboard */}
        {activeTab === 'dashboard' && (
          <Dashboard
            stats={dashboardStats}
            circulars={circulars}
            loading={loading}
            onRefresh={loadInitialData}
            onSelectCircular={handleSelectCircular}
            onNavigateToUpload={() => {
              setActiveCircularId(null);
              setCircularDetails(null);
              setActiveTab('active');
            }}
            onDismissCircular={handleDismissCircular}
          />
        )}

        {/* Tab 2: Active Workflow / Upload */}
        {activeTab === 'active' && (
          <div className="space-y-6">
            {!activeCircularId || !circularDetails ? (
              <UploadCircular
                activeUnresolvedId={dashboardStats?.active_unresolved_circular}
                onUploadSuccess={handleUploadSuccess}
                onViewUnresolved={(id) => handleSelectCircular(id)}
                onDismissUnresolved={handleDismissCircular}
              />
            ) : (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <button
                    onClick={() => {
                      setActiveCircularId(null);
                      setCircularDetails(null);
                    }}
                    className="text-xs text-slate-500 hover:text-slate-800 transition-colors flex items-center gap-1 font-medium"
                  >
                    ← Upload Another Circular
                  </button>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleReprocessCircular(activeCircularId)}
                      className="px-2.5 py-1 text-xs text-indigo-700 hover:text-indigo-900 bg-indigo-50 hover:bg-indigo-100 rounded border border-indigo-200 transition-colors font-medium flex items-center gap-1"
                      title="Re-run OCR and extraction pipeline on current document"
                    >
                      ↻ Reprocess OCR
                    </button>
                    <button
                      onClick={() => handleDismissCircular(activeCircularId)}
                      className="px-2.5 py-1 text-xs text-slate-500 hover:text-slate-800 hover:bg-slate-200/60 rounded border border-slate-200 transition-colors"
                      title="Mark resolved to unlock new uploads"
                    >
                      Dismiss / Unlock
                    </button>
                    <button
                      onClick={() => loadCircularData(activeCircularId)}
                      className="px-2.5 py-1 text-xs text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 rounded border border-slate-200 transition-colors"
                    >
                      Refresh
                    </button>
                  </div>
                </div>

                <ProcessingProgress
                  circular={circularDetails}
                  activeView={activeView}
                  setActiveView={setActiveView}
                />

                {/* Sub-views */}
                {activeView === 'text' && (
                  <ExtractedTextView
                    circularId={activeCircularId}
                    extractedText={extractedText}
                    pageCount={circularDetails.page_count}
                  />
                )}

                {activeView === 'faculty' && (
                  <FacultyVerificationView
                    circularId={activeCircularId}
                    matches={facultyMatches}
                    facultyDirectory={faculties}
                    onReviewSubmitted={() => {
                      loadCircularData(activeCircularId);
                      loadInitialData();
                    }}
                    onProceedToSend={() => setActiveView('summary')}
                  />
                )}

                {activeView === 'summary' && (
                  <SummaryView
                    circularId={activeCircularId}
                    summary={summary}
                    onSendEmails={handleSendEmails}
                  />
                )}

                {activeView === 'email' && (
                  <EmailStatusView
                    circularId={activeCircularId}
                    records={emailRecords}
                    canProceedToSend={circularDetails.can_proceed_to_send}
                    canRetry={circularDetails.can_retry_emails}
                    onRefresh={() => {
                      loadCircularData(activeCircularId);
                      loadInitialData();
                    }}
                  />
                )}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: History */}
        {activeTab === 'history' && (
          <CircularHistory
            circulars={circulars}
            onSelectCircular={handleSelectCircular}
            onRefresh={loadInitialData}
          />
        )}
      </main>

      {/* Modals */}
      <FacultyDirectoryModal
        isOpen={isFacultyModalOpen}
        onClose={() => setIsFacultyModalOpen(false)}
        faculties={faculties}
      />

      <SystemConfigModal
        isOpen={isConfigModalOpen}
        onClose={() => setIsConfigModalOpen(false)}
        config={systemConfig}
        onConfigUpdated={loadInitialData}
      />
    </div>
  );
}
