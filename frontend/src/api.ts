import type { DashboardStats, ExceptionItem, Run, User, Workflow } from "./types";

const TOKEN_KEY = "rpa_sap_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`/api${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function login(username: string, password: string): Promise<{ access_token: string; user: User }> {
  const body = new URLSearchParams({ username, password });
  return request("/auth/login", { method: "POST", body });
}

export function fetchMe(): Promise<User> {
  return request("/auth/me");
}

export function fetchWorkflows(): Promise<Workflow[]> {
  return request("/workflows");
}

export function fetchDashboard(): Promise<DashboardStats[]> {
  return request("/workflows/dashboard");
}

export function triggerRun(workflowId: number): Promise<Run> {
  return request(`/runs?workflow_id=${workflowId}`, { method: "POST" });
}

export function fetchRuns(): Promise<Run[]> {
  return request("/runs");
}

export function fetchRun(runId: number): Promise<Run> {
  return request(`/runs/${runId}`);
}

export function fetchExceptions(): Promise<ExceptionItem[]> {
  return request("/exceptions");
}

export function resolveException(id: number, resolution_note: string): Promise<ExceptionItem> {
  return request(`/exceptions/${id}/resolve`, {
    method: "POST",
    body: JSON.stringify({ resolution_note }),
  });
}

export function fetchAdminUsers(): Promise<User[]> {
  return request("/admin/users");
}

export function fetchAdminWorkflows(): Promise<Workflow[]> {
  return request("/admin/workflows");
}

export function createAdminUser(payload: {
  username: string;
  password: string;
  full_name: string;
  department: string;
  level: string;
}): Promise<User> {
  return request("/admin/users", { method: "POST", body: JSON.stringify(payload) });
}

export function updateAdminUser(
  id: number,
  payload: { full_name?: string; level?: string; active?: boolean; password?: string }
): Promise<User> {
  return request(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function fetchUserAccess(userId: number): Promise<number[]> {
  return request(`/admin/users/${userId}/access`);
}

export function setUserAccess(userId: number, workflow_ids: number[]): Promise<number[]> {
  return request(`/admin/users/${userId}/access`, {
    method: "PUT",
    body: JSON.stringify({ workflow_ids }),
  });
}

export { ApiError };
