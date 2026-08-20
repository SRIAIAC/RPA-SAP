const CLASS_MAP: Record<string, string> = {
  HEALTHY: "badge badge-completed",
  DEGRADED: "badge badge-running",
  DOWN: "badge badge-exception",
  Running: "badge badge-running",
  Completed: "badge badge-completed",
  Exception: "badge badge-exception",
  Open: "badge badge-running",
  Resolved: "badge badge-completed",
  WAITING_FOR_APPROVAL: "badge badge-running",
  Successful: "badge badge-completed",
  Critical: "badge badge-exception",
};

export default function StatusPill({ status }: { status: string }) {
  return <span className={CLASS_MAP[status] ?? "badge badge-running"}>{status}</span>;
}
