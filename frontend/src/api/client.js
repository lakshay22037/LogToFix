import { supabase } from "./supabaseClient";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body } = {}) {
  // Only reached from routes behind ProtectedRoute, which itself redirects
  // when Supabase isn't configured — but guard here too rather than assume
  // that always holds.
  const session = supabase ? (await supabase.auth.getSession()).data.session : null;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        ...(session ? { Authorization: `Bearer ${session.access_token}` } : {}),
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Could not reach the server. Is the backend running?", 0);
  }

  if (!response.ok) {
    let detail;
    try {
      detail = (await response.json()).detail;
    } catch {
      // ignore — fall through to the generic message below
    }
    throw new ApiError(detail || `Request failed (${response.status})`, response.status);
  }

  if (response.status === 204) return null;
  return response.json();
}

export function listProjects() {
  return request("/projects");
}

export function createProject(name) {
  return request("/projects", { method: "POST", body: { name } });
}

export function getProject(projectId) {
  return request(`/projects/${projectId}`);
}

export function updateProjectSettings(projectId, settings) {
  return request(`/projects/${projectId}`, { method: "PATCH", body: settings });
}

export function listLogSources(projectId) {
  return request(`/projects/${projectId}/sources`);
}

export function createLogSource(projectId, { name, sourceType, config }) {
  return request(`/projects/${projectId}/sources`, {
    method: "POST",
    body: { name, source_type: sourceType, config },
  });
}

export function listIssues(projectId, { limit = 20, offset = 0, status } = {}) {
  const params = new URLSearchParams({ limit, offset, ...(status ? { status } : {}) });
  return request(`/projects/${projectId}/issues?${params}`);
}

export function getIssue(projectId, issueId) {
  return request(`/projects/${projectId}/issues/${issueId}`);
}

export function updateIssueStatus(projectId, issueId, status) {
  return request(`/projects/${projectId}/issues/${issueId}`, { method: "PATCH", body: { status } });
}

export function openIssuePr(projectId, issueId, baseBranch = "main") {
  return request(`/projects/${projectId}/issues/${issueId}/open-pr`, {
    method: "POST",
    body: { base_branch: baseBranch },
  });
}

export function getAnalytics(projectId) {
  return request(`/projects/${projectId}/analytics`);
}

export function listMembers(projectId) {
  return request(`/projects/${projectId}/members`);
}

export function inviteMember(projectId, email) {
  return request(`/projects/${projectId}/members`, { method: "POST", body: { email } });
}

export function removeMember(projectId, memberId) {
  return request(`/projects/${projectId}/members/${memberId}`, { method: "DELETE" });
}

export { ApiError };
