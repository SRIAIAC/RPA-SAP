import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchWorkflowDetail, triggerRun } from "../api";
import type { Run, WorkflowDetail } from "../types";
import ManualEntryModal from "../components/ManualEntryModal";
import RunStatusBadge from "../components/RunStatusBadge";

export default function WorkflowDetailPage() {
  const { workflowId } = useParams();
  const navigate = useNavigate();
  const [workflow, setWorkflow] = useState<WorkflowDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [showManualEntry, setShowManualEntry] = useState(false);

  useEffect(() => {
    if (!workflowId) return;
    fetchWorkflowDetail(Number(workflowId))
      .then(setWorkflow)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [workflowId]);

  async function run() {
    if (!workflow) return;
    setStarting(true);
    try {
      const newRun = await triggerRun(workflow.id);
      navigate(`/runs/${newRun.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to trigger run");
      setStarting(false);
    }
  }

  function handleManualEntrySubmitted(run: Run) {
    setShowManualEntry(false);
    navigate(`/runs/${run.id}`);
  }

  if (error) return <div className="form-error">{error}</div>;
  if (!workflow) return <div className="page-loading">Loading…</div>;

  const automationRate = workflow.total_runs ? Math.round((workflow.completed / workflow.total_runs) * 100) : 0;

  return (
    <div className="stack-lg">
      <Link to="/" className="back-link">
        ← Back to dashboard
      </Link>

      <div className="run-header">
        <div>
          <h2 className="section-title">{workflow.name}</h2>
          <div className="run-meta">
            {workflow.department} · {workflow.total_runs} total run(s) · {automationRate}% automation rate
          </div>
        </div>
        {workflow.can_run ? (
          <div className="exception-actions">
            <button className="btn-primary" disabled={starting} onClick={run}>
              {starting ? "Starting…" : "Run now"}
            </button>
            <button className="btn-ghost" disabled={starting} onClick={() => setShowManualEntry(true)}>
              Enter manually
            </button>
          </div>
        ) : (
          <button className="btn-primary" disabled>
            Request access from Dept Head
          </button>
        )}
      </div>

      <p className="workflow-desc">{workflow.description}</p>

      <div className="workflow-systems">
        {workflow.sap_systems.split(",").map((s) => (
          <span key={s} className="tag tag-sap">
            {s.trim()}
          </span>
        ))}
        {workflow.non_sap_systems.split(",").map((s) => (
          <span key={s} className="tag tag-nonsap">
            {s.trim()}
          </span>
        ))}
      </div>

      <div className="trace-section">
        <h3 className="trace-section-title">Process steps</h3>
        <ol className="step-list">
          {workflow.steps.map((step, i) => (
            <li key={i} className="step-item">
              <span className="step-index">{i + 1}</span>
              <span className="step-text">{step}</span>
            </li>
          ))}
        </ol>
      </div>

      <div className="trace-section">
        <h3 className="trace-section-title">Known exception reasons</h3>
        <div className="workflow-systems">
          {workflow.exception_reasons.map((reason) => (
            <span key={reason} className="tag">
              {reason}
            </span>
          ))}
        </div>
      </div>

      <h3 className="section-title" style={{ fontSize: 15 }}>
        Recent runs
      </h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Started</th>
              <th>Triggered by</th>
              <th>Status</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {workflow.recent_runs.length === 0 && (
              <tr>
                <td colSpan={4} className="empty-row">
                  No runs yet.
                </td>
              </tr>
            )}
            {workflow.recent_runs.map((run) => (
              <tr key={run.id} className="row-clickable" onClick={() => navigate(`/runs/${run.id}`)}>
                <td>{new Date(run.started_at).toLocaleString()}</td>
                <td>{run.triggered_by_name}</td>
                <td>
                  <RunStatusBadge status={run.status} />
                </td>
                <td>{run.result_summary ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showManualEntry && (
        <ManualEntryModal
          workflow={workflow}
          onClose={() => setShowManualEntry(false)}
          onSubmitted={handleManualEntrySubmitted}
        />
      )}
    </div>
  );
}
