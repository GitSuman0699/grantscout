/**
 * GrantScout API Service Layer
 * 
 * Centralized client for all FastAPI backend REST calls.
 * Base URL and API Key are injected via Vite env variables.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || '';

/**
 * Authenticated headers (for agent action endpoints that require X-API-Key).
 */
const authHeaders = () => ({
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY,
});

/**
 * Public headers (for read-only endpoints).
 */
const publicHeaders = () => ({
  'Content-Type': 'application/json',
});

// ─────────────────────────────────────────────
//  Health & System
// ─────────────────────────────────────────────

export async function fetchHealthCheck() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────
//  Dashboard & Stats
// ─────────────────────────────────────────────

export async function fetchDashboardStats() {
  const res = await fetch(`${BASE_URL}/api/dashboard/stats`);
  if (!res.ok) throw new Error(`Dashboard stats failed: ${res.status}`);
  return res.json();
}

export async function fetchActivity() {
  const res = await fetch(`${BASE_URL}/api/dashboard/activity`);
  if (!res.ok) throw new Error(`Activity fetch failed: ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────
//  Grants Pipeline
// ─────────────────────────────────────────────

export async function fetchGrants(status = '') {
  const url = status ? `${BASE_URL}/api/grants?status=${status}` : `${BASE_URL}/api/grants`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Grants fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchGrantById(grantId) {
  const res = await fetch(`${BASE_URL}/api/grants/${grantId}`);
  if (!res.ok) throw new Error(`Grant ${grantId} fetch failed: ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────
//  Organization Profile
// ─────────────────────────────────────────────

export async function fetchOrgProfile() {
  const res = await fetch(`${BASE_URL}/api/org/profile`);
  if (!res.ok) throw new Error(`Org profile fetch failed: ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────
//  RAG Knowledge Base
// ─────────────────────────────────────────────

export async function fetchDocuments() {
  const res = await fetch(`${BASE_URL}/api/documents`);
  if (!res.ok) throw new Error(`Documents fetch failed: ${res.status}`);
  return res.json();
}

export async function searchDocuments(query, topK = 3, category = null) {
  const body = { query, top_k: topK };
  if (category) body.category = category;

  const res = await fetch(`${BASE_URL}/api/documents/search`, {
    method: 'POST',
    headers: publicHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Document search failed: ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────
//  Application Drafts
// ─────────────────────────────────────────────

export async function fetchApplications() {
  const res = await fetch(`${BASE_URL}/api/applications`);
  if (!res.ok) throw new Error(`Applications fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchApplicationById(draftId) {
  const res = await fetch(`${BASE_URL}/api/applications/${draftId}`);
  if (!res.ok) throw new Error(`Application ${draftId} fetch failed: ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────
//  Cost & Token Optimization
// ─────────────────────────────────────────────

export async function fetchTokenUsage() {
  const res = await fetch(`${BASE_URL}/api/optimization/token-usage`);
  if (!res.ok) throw new Error(`Token usage fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchCacheStats() {
  const res = await fetch(`${BASE_URL}/api/optimization/cache-stats`);
  if (!res.ok) throw new Error(`Cache stats fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchModelTiers() {
  const res = await fetch(`${BASE_URL}/api/optimization/model-tiers`);
  if (!res.ok) throw new Error(`Model tiers fetch failed: ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────
//  Agent Actions (Authenticated)
// ─────────────────────────────────────────────

export async function triggerScan() {
  const res = await fetch(`${BASE_URL}/api/agent/scan`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Scan trigger failed: ${res.status}`);
  }
  return res.json();
}

export async function triggerOrchestrate() {
  const res = await fetch(`${BASE_URL}/api/agent/orchestrate`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Orchestration trigger failed: ${res.status}`);
  }
  return res.json();
}

export async function triggerDraft(grantId) {
  const res = await fetch(`${BASE_URL}/api/grants/${grantId}/draft`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Draft trigger failed: ${res.status}`);
  }
  return res.json();
}

// ─────────────────────────────────────────────
//  SSE Real-Time Stream
// ─────────────────────────────────────────────

export function createSSEStream(onEvent, onError) {
  const eventSource = new EventSource(`${BASE_URL}/api/dashboard/stream`);

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent(data);
    } catch {
      onEvent({ raw: e.data });
    }
  };

  eventSource.addEventListener('scan_completed', (e) => {
    onEvent({ type: 'scan_completed', data: e.data });
  });

  eventSource.addEventListener('application_drafted', (e) => {
    onEvent({ type: 'application_drafted', data: e.data });
  });

  eventSource.addEventListener('heartbeat', () => {
    // Ignore heartbeat pings
  });

  eventSource.onerror = (err) => {
    if (onError) onError(err);
  };

  return eventSource;
}
