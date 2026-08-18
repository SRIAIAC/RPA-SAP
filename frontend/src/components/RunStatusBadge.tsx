import type { RunStatus } from "../types";

const CLASS_MAP: Record<RunStatus, string> = {
  Running: "badge badge-running",
  Completed: "badge badge-completed",
  Exception: "badge badge-exception",
};

export default function RunStatusBadge({ status }: { status: RunStatus }) {
  return <span className={CLASS_MAP[status]}>{status}</span>;
}
