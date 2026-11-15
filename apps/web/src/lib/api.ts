export type ApiError = { status: number; code: string; message: string };

export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_RIVET_API_URL || "http://127.0.0.1:8080";
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const base = apiBaseUrl();
  const url = base ? `${base}${path}` : path;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const res = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
    if (!res.ok) {
      let code = "http_error";
      let message = res.statusText;
      try {
        const body = await res.json();
        code = body.code || code;
        message = body.message || message;
      } catch {}
      throw { status: res.status, code, message } as ApiError;
    }
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

export function isApiConfigured(): boolean {
  return Boolean(apiBaseUrl());
}

// Domain models matching Go API / Postgres contracts

export interface ApiIncident {
  id: string;
  title: string;
  description?: string;
  discovery_west?: number;
  discovery_south?: number;
  discovery_east?: number;
  discovery_north?: number;
  archived_at?: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface ApiAcquisition {
  id: string;
  incident_id: string;
  source_provider: string;
  granule_id: string;
  crid: string;
  product_maturity: string;
  created_at?: string;
}

export interface ApiEvidence {
  id: string;
  incident_id: string;
  acquisition_id?: string;
  claim_level: string;
  evidence_kind: string;
  title: string;
  summary: string;
  source_path: string;
  review_state: "draft" | "submitted" | "accepted" | "rejected" | "needs_investigation";
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface ApiDecision {
  id: string;
  incident_id: string;
  evidence_id: string;
  reviewer_id: string;
  decision: "accept" | "reject" | "needs_investigation";
  rationale?: string;
  created_at?: string;
}

export interface ApiJob {
  id: string;
  incident_id: string;
  job_type: string;
  state: "queued" | "claimed" | "running" | "succeeded" | "failed" | "cancelled";
  idempotency_key: string;
  claimed_by?: string;
  payload?: Record<string, unknown>;
  result?: Record<string, unknown>;
  started_at?: string;
  finished_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ApiReport {
  id: string;
  incident_id: string;
  title: string;
  content: Record<string, unknown>;
  generated_by: string;
  created_at?: string;
}

export interface ApiRoleResponse {
  incident_id: string;
  user_id: string;
  role: "owner" | "analyst" | "reviewer" | "viewer";
}

export interface ApiAuditEvent {
  id: string;
  actor_id: string;
  action: string;
  entity_table: string;
  entity_id: string;
  incident_id: string;
  occurred_at: string;
}

export interface WhoamiResponse {
  subject: string;
}

function authHeaders(token?: string): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Typed API operations
export async function getWhoami(token: string): Promise<WhoamiResponse> {
  return apiFetch<WhoamiResponse>("/api/v1/whoami", { headers: authHeaders(token) });
}

export async function listIncidents(token: string): Promise<ApiIncident[]> {
  return apiFetch<ApiIncident[]>("/api/v1/incidents", { headers: authHeaders(token) });
}

export async function createIncident(
  token: string,
  data: {
    title: string;
    description?: string;
    discovery_west?: number;
    discovery_south?: number;
    discovery_east?: number;
    discovery_north?: number;
  }
): Promise<ApiIncident> {
  return apiFetch<ApiIncident>("/api/v1/incidents", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
}

export async function getIncident(token: string, incidentId: string): Promise<ApiIncident> {
  return apiFetch<ApiIncident>(`/api/v1/incidents/${incidentId}`, { headers: authHeaders(token) });
}

export async function listAcquisitions(token: string, incidentId: string): Promise<ApiAcquisition[]> {
  return apiFetch<ApiAcquisition[]>(`/api/v1/incidents/${incidentId}/acquisitions`, {
    headers: authHeaders(token),
  });
}

export async function createAcquisition(
  token: string,
  incidentId: string,
  data: {
    source_provider: string;
    granule_id: string;
    crid: string;
    product_maturity?: string;
  }
): Promise<ApiAcquisition> {
  return apiFetch<ApiAcquisition>(`/api/v1/incidents/${incidentId}/acquisitions`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
}

export async function listEvidence(token: string, incidentId: string): Promise<ApiEvidence[]> {
  return apiFetch<ApiEvidence[]>(`/api/v1/incidents/${incidentId}/evidence`, {
    headers: authHeaders(token),
  });
}

export async function createEvidence(
  token: string,
  incidentId: string,
  data: {
    acquisition_id?: string;
    claim_level?: string;
    evidence_kind?: string;
    title: string;
    summary: string;
    source_path: string;
  }
): Promise<ApiEvidence> {
  return apiFetch<ApiEvidence>(`/api/v1/incidents/${incidentId}/evidence`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
}

export async function getEvidence(token: string, incidentId: string, evidenceId: string): Promise<ApiEvidence> {
  return apiFetch<ApiEvidence>(`/api/v1/incidents/${incidentId}/evidence/${evidenceId}`, {
    headers: authHeaders(token),
  });
}

export async function patchEvidence(
  token: string,
  incidentId: string,
  evidenceId: string,
  data: { title?: string; summary?: string }
): Promise<ApiEvidence> {
  return apiFetch<ApiEvidence>(`/api/v1/incidents/${incidentId}/evidence/${evidenceId}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
}

export async function createDecision(
  token: string,
  incidentId: string,
  evidenceId: string,
  data: {
    decision: "accept" | "reject" | "needs_investigation";
    rationale?: string;
  }
): Promise<ApiDecision> {
  return apiFetch<ApiDecision>(`/api/v1/incidents/${incidentId}/evidence/${evidenceId}/decisions`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
}

export async function listJobs(token: string, incidentId: string): Promise<ApiJob[]> {
  return apiFetch<ApiJob[]>(`/api/v1/incidents/${incidentId}/jobs`, { headers: authHeaders(token) });
}

export async function createJob(
  token: string,
  incidentId: string,
  data: { job_type: string; idempotency_key: string; payload?: Record<string, unknown> }
): Promise<ApiJob> {
  return apiFetch<ApiJob>(`/api/v1/incidents/${incidentId}/jobs`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
}

export async function getJob(token: string, incidentId: string, jobId: string): Promise<ApiJob> {
  return apiFetch<ApiJob>(`/api/v1/incidents/${incidentId}/jobs/${jobId}`, {
    headers: authHeaders(token),
  });
}

export async function listReports(token: string, incidentId: string): Promise<ApiReport[]> {
  return apiFetch<ApiReport[]>(`/api/v1/incidents/${incidentId}/reports`, {
    headers: authHeaders(token),
  });
}

export async function createReport(
  token: string,
  incidentId: string,
  data: { title: string; content: Record<string, unknown> }
): Promise<ApiReport> {
  return apiFetch<ApiReport>(`/api/v1/incidents/${incidentId}/reports`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
}

export async function getReport(token: string, incidentId: string, reportId: string): Promise<ApiReport> {
  return apiFetch<ApiReport>(`/api/v1/incidents/${incidentId}/reports/${reportId}`, {
    headers: authHeaders(token),
  });
}

export async function getIncidentRole(token: string, incidentId: string): Promise<ApiRoleResponse> {
  return apiFetch<ApiRoleResponse>(`/api/v1/incidents/${incidentId}/role`, {
    headers: authHeaders(token),
  });
}

export async function addIncidentMember(
  token: string,
  incidentId: string,
  data: { user_id: string; role: "analyst" | "reviewer" | "viewer" }
): Promise<ApiRoleResponse> {
  return apiFetch<ApiRoleResponse>(`/api/v1/incidents/${incidentId}/members`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
}

export async function listAuditEvents(token: string, incidentId: string): Promise<ApiAuditEvent[]> {
  return apiFetch<ApiAuditEvent[]>(`/api/v1/incidents/${incidentId}/audit`, {
    headers: authHeaders(token),
  });
}
