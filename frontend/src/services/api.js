const API_BASE = '/api';

export async function fetchDashboard() {
  const res = await fetch(`${API_BASE}/dashboard`);
  if (!res.ok) throw new Error('Failed to load dashboard metrics');
  return res.json();
}

export async function fetchCirculars() {
  const res = await fetch(`${API_BASE}/circulars`);
  if (!res.ok) throw new Error('Failed to load circulars history');
  return res.json();
}

export async function fetchCircular(id) {
  const res = await fetch(`${API_BASE}/circulars/${id}`);
  if (!res.ok) throw new Error(`Failed to load circular ${id}`);
  return res.json();
}

export async function fetchCircularStatus(id) {
  const res = await fetch(`${API_BASE}/circulars/${id}/status`);
  if (!res.ok) throw new Error(`Failed to poll status for ${id}`);
  return res.json();
}

export async function fetchCircularText(id) {
  const res = await fetch(`${API_BASE}/circulars/${id}/text`);
  if (!res.ok) throw new Error(`Failed to fetch text for ${id}`);
  return res.json();
}

export async function fetchCircularSummary(id) {
  const res = await fetch(`${API_BASE}/circulars/${id}/summary`);
  if (!res.ok) throw new Error(`Failed to fetch summary for ${id}`);
  return res.json();
}

export async function fetchCircularFaculty(id) {
  const res = await fetch(`${API_BASE}/circulars/${id}/faculty`);
  if (!res.ok) throw new Error(`Failed to fetch faculty for ${id}`);
  return res.json();
}

export async function submitFacultyReview(id, reviews, autoProceedToSend = false) {
  const res = await fetch(`${API_BASE}/circulars/${id}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reviews, auto_proceed_to_send: autoProceedToSend }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to submit review');
  }
  return res.json();
}

export async function sendCircularEmails(id, subject = null, summaryOverride = null) {
  const res = await fetch(`${API_BASE}/circulars/${id}/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, summary_override: summaryOverride }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to initiate email delivery');
  }
  return res.json();
}

export async function retryCircularEmails(id, recipientIds = null) {
  const res = await fetch(`${API_BASE}/circulars/${id}/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recipient_ids: recipientIds }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to retry email delivery');
  }
  return res.json();
}

export async function fetchCircularEmails(id) {
  const res = await fetch(`${API_BASE}/circulars/${id}/emails`);
  if (!res.ok) throw new Error(`Failed to fetch email records for ${id}`);
  return res.json();
}

export async function uploadCircular(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/circulars/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to upload circular');
  }
  return res.json();
}

export async function dismissCircular(id) {
  const res = await fetch(`${API_BASE}/circulars/${id}/dismiss`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to dismiss circular');
  return res.json();
}

export async function reprocessCircular(id) {
  const res = await fetch(`${API_BASE}/circulars/${id}/reprocess`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to reprocess circular');
  return res.json();
}

export async function fetchFaculties() {
  const res = await fetch(`${API_BASE}/faculties`);
  if (!res.ok) throw new Error('Failed to fetch faculty directory');
  return res.json();
}

export async function fetchSystemConfig() {
  const res = await fetch(`${API_BASE}/system/config`);
  if (!res.ok) throw new Error('Failed to fetch system config');
  return res.json();
}

export async function updateSystemConfig(config) {
  const res = await fetch(`${API_BASE}/system/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error('Failed to update config');
  return res.json();
}
