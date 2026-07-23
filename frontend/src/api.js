/**
 * API client for Lead Intelligence backend.
 * Base URL points to the FastAPI server on localhost:8000.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

function buildQuery(base, params) {
  const url = new URL(base, API_BASE);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') {
      url.searchParams.set(k, v);
    }
  });
  return url.toString();
}

export async function getStats() {
  return fetchJSON(`${API_BASE}/stats`);
}

export async function getFilters() {
  return fetchJSON(`${API_BASE}/filters`);
}

export async function getCompanies(params = {}) {
  return fetchJSON(buildQuery(`${API_BASE}/companies`, params));
}

export async function getContacts(params = {}) {
  return fetchJSON(buildQuery(`${API_BASE}/contacts`, params));
}

export async function getContact(id) {
  return fetchJSON(`${API_BASE}/contacts/${id}`);
}

export async function runClassification() {
  const res = await fetch(`${API_BASE}/classify`, { method: 'POST' });
  if (!res.ok) throw new Error(`Classification error: ${res.status}`);
  return res.json();
}

export async function getEmailStatus() {
  return fetchJSON(`${API_BASE}/email-status`);
}

export async function getEmailTemplates() {
  return fetchJSON(`${API_BASE}/email-templates`);
}

export async function sendEmail({ contactId, template, customSubject, customBody, dryRun }) {
  const params = {
    contact_id: contactId,
    template: template || 'default',
    custom_subject: customSubject || undefined,
    custom_body: customBody || undefined,
    dry_run: dryRun || false,
  };
  const url = buildQuery(`${API_BASE}/send-email`, params);
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) throw new Error(`Send error: ${res.status}`);
  return res.json();
}

export async function sendBulkEmail({ contactIds, template, customSubject, customBody, dryRun, skipContacted }) {
  const url = new URL(`${API_BASE}/send-bulk`);
  contactIds.forEach(id => url.searchParams.append('contact_ids', id));
  if (template) url.searchParams.set('template', template);
  if (customSubject) url.searchParams.set('custom_subject', customSubject);
  if (customBody) url.searchParams.set('custom_body', customBody);
  if (dryRun) url.searchParams.set('dry_run', 'true');
  if (skipContacted !== undefined) url.searchParams.set('skip_contacted', String(skipContacted));

  const res = await fetch(url.toString(), { method: 'POST' });
  if (!res.ok) throw new Error(`Bulk send error: ${res.status}`);
  return res.json();
}

export async function matchCVLeads(file, params = {}) {
  const formData = new FormData();
  formData.append('file', file);

  const url = buildQuery(`${API_BASE}/match-cv-leads`, params);
  const res = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `CV match error: ${res.status}`);
  }
  return res.json();
}



