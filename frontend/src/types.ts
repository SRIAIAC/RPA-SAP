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
