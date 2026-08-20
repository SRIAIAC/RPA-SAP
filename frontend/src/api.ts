import type {
  AIDecision,
  AnalyticsDashboard,
  AuditLogEntry,
  DashboardStats,
  DemoScenario,
  ExceptionDetail,
  ExceptionItem,
  IntegrationStatusResponse,
  Run,
  SystemHealthResponse,
  User,
  Workflow,
  WorkflowDetail,
} from "./types";

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
  if (options.body && !(options.body instanceof URLSearchParams) && !(options.body instanceof FormData)) {
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

export function fetchWorkflowDetail(id: number): Promise<WorkflowDetail> {
  return request(`/workflows/${id}`);
}

export function triggerRun(workflowId: number, manualInput?: Record<string, string | number>): Promise<Run> {
  const hasManualInput = manualInput && Object.keys(manualInput).length > 0;
  return request(`/runs?workflow_id=${workflowId}`, {
    method: "POST",
    body: hasManualInput ? JSON.stringify(manualInput) : undefined,
  });
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

export interface MailMessageListItem {
  id: number;
  sender: string;
  sender_name: string;
  subject: string;
  department: string;
  received_at: string;
  has_attachment: boolean;
  source: string;
}

export interface InvoiceExtraction {
  is_invoice: boolean;
  classifier_confidence: number;
  classifier_reasons: string[];
  vendor_name?: string | null;
  invoice_number?: string | null;
  invoice_date?: string | null;
  po_number?: string | null;
  total_amount?: string | null;
  currency?: string | null;
  raw_ocr_text?: string | null;
}

export interface ClassifyResult {
  message_id: number;
  subject: string;
  is_invoice: boolean;
  classifier_confidence: number;
  classifier_reasons: string[];
  extraction?: InvoiceExtraction | null;
}

export interface ClassifyAllResult {
  total: number;
  flagged_as_invoice: number;
  results: ClassifyResult[];
}

export function fetchMailMessages(): Promise<MailMessageListItem[]> {
  return request("/mailroom/messages");
}

export interface MailAttachment {
  id: number;
  filename: string;
  content_type: string;
}

export interface MailMessageDetail extends MailMessageListItem {
  body: string;
  attachment?: MailAttachment | null;
}

export function fetchMailMessageDetail(id: number): Promise<MailMessageDetail> {
  return request(`/mailroom/messages/${id}`);
}

// Attachment/raw-message endpoints require the Bearer token, so plain <a href>
// navigation 401s (the browser doesn't attach it) — fetch with auth and hand
// the caller a blob: URL to open instead.
async function fetchAsObjectUrl(path: string): Promise<string> {
  const token = getToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`/api${path}`, { headers });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export function fetchAttachmentObjectUrl(attachmentId: number): Promise<string> {
  return fetchAsObjectUrl(`/mailroom/attachments/${attachmentId}/file`);
}

export function fetchMessageJsonObjectUrl(messageId: number): Promise<string> {
  return fetchAsObjectUrl(`/mailroom/messages/${messageId}`);
}

export function classifyAllMail(): Promise<ClassifyAllResult> {
  return request("/mailroom/classify-all", { method: "POST" });
}

export interface ImportGmailResult {
  imported: number;
  skipped_duplicates: number;
  total_fetched: number;
}

// Senior Manager+ only (backend-enforced) — pulls real mail in read-only via
// IMAP for testing the classifier/OCR pipeline against real data.
export function importGmail(limit = 10): Promise<ImportGmailResult> {
  return request(`/mailroom/import-gmail?limit=${limit}`, { method: "POST" });
}

// Upload a real invoice/document (PNG/JPG/PDF) to run through the same
// classify/OCR pipeline as the seeded and Gmail-imported messages — no
// external account needed at all.
export function uploadDocument(file: File, subject?: string): Promise<MailMessageDetail> {
  const form = new FormData();
  form.append("file", file);
  if (subject) form.append("subject", subject);
  return request("/mailroom/upload", { method: "POST", body: form });
}

export interface ManualEntryInput {
  subject: string;
  body: string;
  department: string;
  senderName?: string;
  sender?: string;
  file?: File | null;
}

// Add a mail message by hand — every field entered directly rather than
// pulled from Gmail or a file. Attachment is optional.
export function submitManualEntry(entry: ManualEntryInput): Promise<MailMessageDetail> {
  const form = new FormData();
  form.append("subject", entry.subject);
  form.append("body", entry.body);
  form.append("department", entry.department);
  if (entry.senderName) form.append("sender_name", entry.senderName);
  if (entry.sender) form.append("sender", entry.sender);
  if (entry.file) form.append("file", entry.file);
  return request("/mailroom/manual-entry", { method: "POST", body: form });
}

// --- Integration Monitor -----------------------------------------------------
export function fetchIntegrationStatus(): Promise<IntegrationStatusResponse> {
  return request("/integrations/status");
}

// --- AI Decisions ------------------------------------------------------------
export function fetchAiDecisions(params?: { use_case?: string; workflow_run_id?: number }): Promise<AIDecision[]> {
  const qs = new URLSearchParams();
  if (params?.use_case) qs.set("use_case", params.use_case);
  if (params?.workflow_run_id) qs.set("workflow_run_id", String(params.workflow_run_id));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request(`/ai/decisions${suffix}`);
}

// --- Audit Log -----------------------------------------------------------------
export function fetchAuditLog(): Promise<AuditLogEntry[]> {
  return request("/admin/audit-log");
}

// --- Analytics -------------------------------------------------------------------
export function fetchAnalyticsDashboard(department?: string): Promise<AnalyticsDashboard> {
  const suffix = department ? `?department=${encodeURIComponent(department)}` : "";
  return request(`/analytics/dashboard${suffix}`);
}

// --- Demo Scenarios ------------------------------------------------------------------
export function fetchDemoScenarios(): Promise<DemoScenario[]> {
  return request("/demo/scenarios");
}

export function runDemoScenario(scenarioId: string): Promise<Run> {
  return request(`/demo/scenarios/${scenarioId}/run`, { method: "POST" });
}

// --- Exception detail + actions ------------------------------------------------------
export function fetchExceptionDetail(id: number): Promise<ExceptionDetail> {
  return request(`/exceptions/${id}`);
}

export function takeExceptionAction(id: number, action: string, note?: string): Promise<ExceptionDetail> {
  return request(`/exceptions/${id}/action`, { method: "POST", body: JSON.stringify({ action, note }) });
}

// --- System Health -----------------------------------------------------------------
export function fetchSystemHealth(): Promise<SystemHealthResponse> {
  return request("/system/health");
}

export { ApiError };
