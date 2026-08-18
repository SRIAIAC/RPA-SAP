import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchRun } from "../api";
import RunStatusBadge from "../components/RunStatusBadge";
import type { Run } from "../types";

export default function RunDetail() {
  const { runId } = useParams();
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;

    async function poll() {
      try {
        const data = await fetchRun(Number(runId));
        if (cancelled) return;
        setRun(data);
        if (data.status === "Running") {
          setTimeout(poll, 1000);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load run");
      }
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  if (error) return <div className="form-error">{error}</div>;
  if (!run) return <div className="page-loading">Loading run…</div>;

  return (
    <div className="stack-lg">
      <Link to="/" className="back-link">
        ← Back to dashboard
      </Link>
      <div className="run-header">
        <div>
          <h2 className="section-title">{run.workflow_name}</h2>
          <div className="run-meta">
            {run.department} • triggered by {run.triggered_by_name} • started{" "}
            {new Date(run.started_at).toLocaleString()}
          </div>
        </div>
        <RunStatusBadge status={run.status} />
      </div>

      <div className="progress-track">
        <div
          className={`progress-fill ${run.status === "Exception" ? "progress-fill-exception" : ""}`}
          style={{ width: `${(run.current_step / run.total_steps) * 100}%` }}
        />
      </div>

      <ol className="step-list">
        {run.log.map((entry) => (
          <li key={entry.index} className="step-item step-done">
            <span className="step-index">{entry.index}</span>
            <span className="step-text">{entry.step}</span>
            <span className="step-ts">{new Date(entry.ts).toLocaleTimeString()}</span>
          </li>
        ))}
        {run.status === "Running" && (
          <li className="step-item step-active">
            <span className="step-index spinner" />
            <span className="step-text">Processing…</span>
          </li>
        )}
      </ol>

      {run.result_summary && (
        <div className={`result-banner ${run.status === "Exception" ? "result-exception" : "result-completed"}`}>
          {run.result_summary}
        </div>
      )}
    </div>
  );
}
