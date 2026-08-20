export type Department = "Procurement" | "Maintenance" | "Finance" | "HSE" | "Production" | "Admin";
export type Level = "Manager" | "Senior Manager" | "Department Head" | "Admin";
export type RunStatus = "Running" | "Completed" | "Exception";
export type ExceptionStatus = "Open" | "Resolved";

export interface User {
  id: number;
  username: string;
  full_name: string;
  department: Department;
  level: Level;
  active: boolean;
}

export interface Workflow {
  id: number;
  key: string;
  name: string;
  department: Department;
  description: string;
  sap_systems: string;
  non_sap_systems: string;
  steps: string[];
  can_run: boolean;
}

export interface LogEntry {
  step: string;
  index: number;
  ts: string;
  status: string;
}

export interface Run {
  id: number;
  workflow_id: number;
  workflow_name: string;
  triggered_by_id: number;
  triggered_by_name: string;
  department: Department;
  status: RunStatus;
  current_step: number;
  total_steps: number;
  log: LogEntry[];
  started_at: string;
  finished_at: string | null;
  result_summary: string | null;
}

export interface ExceptionItem {
  id: number;
  run_id: number;
  workflow_id: number;
  workflow_name: string;
  department: Department;
  reason: string;
  status: ExceptionStatus;
  raised_at: string;
  resolved_at: string | null;
  resolved_by_name: string | null;
  resolution_note: string | null;
}

export interface DashboardStats {
  department: Department;
  workflows_available: number;
  runs_today: number;
  completed_today: number;
  open_exceptions: number;
}

export type HealthStatus = "HEALTHY" | "DEGRADED" | "DOWN";

export interface IntegrationServiceHealth {
  status: HealthStatus;
  detail: unknown;
  base_url: string;
}

export interface IntegrationCall {
  provider: string;
  system: string;
  endpoint: string;
  method: string;
  success: boolean;
  latency_ms: number;
  request_summary?: string | null;
  response_summary?: string | null;
  error?: string | null;
  created_at: string;
}

export interface IntegrationSummary {
  provider: string;
  system: string;
  requests: number;
  successes: number;
  failures: number;
  success_rate_pct: number;
  avg_latency_ms: number;
  last_success_at: string | null;
  last_error: string | null;
  last_error_at: string | null;
}

export interface IntegrationStatusResponse {
  services: Record<string, IntegrationServiceHealth>;
  integrations: IntegrationSummary[];
}

export interface AIDecision {
  id: number;
  workflow_run_id: number | null;
  use_case: string;
  correlation_id: string;
  input_summary: string;
  classification: string | null;
  confidence: number | null;
  recommendation: string | null;
  final_decision: string | null;
  human_decision: string | null;
  created_at: string;
}

export interface AuditLogEntry {
  id: number;
  actor_user_id: number | null;
  actor_name: string;
  action: string;
  target_type: string;
  target_id: number | null;
  detail: string | null;
  created_at: string;
}

export interface WorkflowKpi {
  workflow_id: number;
  workflow_key: string;
  workflow_name: string;
  department: string;
  total_runs: number;
  completed: number;
  exceptions: number;
  automation_rate_pct: number;
  avg_processing_seconds: number;
  manual_processing_minutes: number;
  transactions: number;
  estimated_hours_saved: number;
}

export interface DepartmentKpi {
  department: string;
  total_runs: number;
  completed: number;
  exceptions: number;
  automation_rate_pct: number;
  human_intervention_rate_pct: number;
  estimated_hours_saved: number;
}

export interface OrgKpi {
  total_runs: number;
  completed: number;
  exceptions: number;
  automation_rate_pct: number;
  human_intervention_rate_pct: number;
  avg_processing_seconds: number;
  estimated_hours_saved: number;
}

export interface AnalyticsDashboard {
  org: OrgKpi;
  departments: DepartmentKpi[];
  workflows: WorkflowKpi[];
}

export interface DemoScenario {
  id: string;
  category: string;
  label: string;
  variant: "Successful" | "Exception" | "Critical";
  workflow_key: string;
  scenario: string | null;
}

export interface WorkflowStepDetail {
  index: number;
  name: string;
  status: string;
  detail: Record<string, unknown> | null;
  started_at: string;
}

export interface ExceptionActionEntry {
  id: number;
  action: string;
  actor_name: string;
  note: string | null;
  created_at: string;
}

export interface WorkflowDetail extends Workflow {
  exception_reasons: string[];
  total_runs: number;
  completed: number;
  exceptions: number;
  recent_runs: Run[];
}

export interface SystemHealthResponse {
  app_mode: string;
  backend: { status: HealthStatus; db: string };
  mock_sap: { status: HealthStatus; base_url: string };
  mock_non_sap: { status: HealthStatus; base_url: string };
  providers: { sap: string; ai: string; rpa: string; event_bus: string };
}

export interface ExceptionDetail extends ExceptionItem {
  ai_explanation: { classification?: string; confidence?: number; recommendation?: string } | null;
  steps: WorkflowStepDetail[];
  sap_calls: IntegrationCall[];
  nonsap_calls: IntegrationCall[];
  ai_decisions: AIDecision[];
  audit_history: { action: string; actor_name: string; detail: string | null; created_at: string }[];
  actions: ExceptionActionEntry[];
  available_actions: string[];
}
