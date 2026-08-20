import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchExceptionDetail, takeExceptionAction } from "../api";
import type { ExceptionDetail } from "../types";
import StatusPill from "../components/StatusPill";

const ACTION_LABELS: Record<string, string> = {
  approve: "Approve",
  reject: "Reject",
  retry: "Retry",
  escalate: "Escalate",
  request_correction: "Request correction",
};

export default function ExceptionDetailPage() {
  const { exceptionId } = useParams();
  const navigate = useNavigate();
  const [item, setItem] = useState<ExceptionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  function load() {
    if (!exceptionId) return;
    fetchExceptionDetail(Number(exceptionId))
      .then(setItem)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }

  useEffect(load, [exceptionId]);

  async function act(action: string) {
    if (!item) return;
    setError(null);
    setBusy(action);
    try {
      const updated = await takeExceptionAction(item.id, action, note || undefined);
      setItem(updated);
      setNote("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  if (error && !item) return <div className="form-error">{error}</div>;
  if (!item) return <div className="page-loading">Loading…</div>;

  return (
    <div className="stack-lg">
      <Link to="/exceptions" className="back-link">
        ← Back to exception queue
      </Link>

      <div className="run-header">
        <div>
          <h2 className="section-title">{item.workflow_name}</h2>
          <div className="run-meta">
            {item.department} · Run #{item.run_id} · raised {new Date(item.raised_at).toLocaleString()}
          </div>
        </div>
        <StatusPill status={item.status} />
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="exception-card">
        <div className="exception-reason">{item.reason}</div>
        {item.resolution_note && (
          <div className="exception-meta">
            Resolved by {item.resolved_by_name} — {item.resolution_note}
          </div>
        )}
      </div>

      {item.ai_explanation && (
        <div className="trace-section">
          <h3 className="trace-section-title">AI explanation</h3>
          <div className="trace-card">
            <div className="trace-card-head">
              <strong>{item.ai_explanation.classification ?? "Explanation"}</strong>
              {item.ai_explanation.confidence != null && (
                <span className="exception-meta">{Math.round(item.ai_explanation.confidence * 100)}% confidence</span>
              )}
            </div>
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-dim)" }}>{item.ai_explanation.recommendation}</p>
          </div>
        </div>
      )}

      <div className="trace-section">
        <h3 className="trace-section-title">Evidence — workflow steps</h3>
        {item.steps.map((step) => (
          <div key={step.index} className="trace-card">
            <div className="trace-card-head">
              <strong>
                {step.index}. {step.name}
              </strong>
              <span className="exception-meta">{new Date(step.started_at).toLocaleTimeString()}</span>
            </div>
            {step.detail && <pre>{JSON.stringify(step.detail, null, 2)}</pre>}
          </div>
        ))}
      </div>

      {item.sap_calls.length > 0 && (
        <div className="trace-section">
          <h3 className="trace-section-title">Related SAP records</h3>
          {item.sap_calls.map((call, i) => (
            <div key={i} className="trace-card">
              <div className="trace-card-head">
                <strong>
                  {call.system} — {call.endpoint}
                </strong>
                <StatusPill status={call.success ? "Completed" : "Exception"} />
              </div>
              <pre>{call.response_summary ?? call.error}</pre>
            </div>
          ))}
        </div>
      )}

      {item.nonsap_calls.length > 0 && (
        <div className="trace-section">
          <h3 className="trace-section-title">Related non-SAP records</h3>
          {item.nonsap_calls.map((call, i) => (
            <div key={i} className="trace-card">
              <div className="trace-card-head">
                <strong>
                  {call.system} — {call.endpoint}
                </strong>
                <StatusPill status={call.success ? "Completed" : "Exception"} />
              </div>
              <pre>{call.response_summary ?? call.error}</pre>
            </div>
          ))}
        </div>
      )}

      <div className="trace-section">
        <h3 className="trace-section-title">Audit history</h3>
        {item.audit_history.length === 0 && <div className="exception-meta">No audit entries yet.</div>}
        {item.audit_history.map((entry, i) => (
          <div key={i} className="trace-card">
            <div className="trace-card-head">
              <strong>{entry.action}</strong>
              <span className="exception-meta">{new Date(entry.created_at).toLocaleString()}</span>
            </div>
            <span className="exception-meta">{entry.actor_name}</span>
          </div>
        ))}
      </div>

      {item.actions.length > 0 && (
        <div className="trace-section">
          <h3 className="trace-section-title">Actions taken</h3>
          {item.actions.map((a) => (
            <div key={a.id} className="trace-card">
              <div className="trace-card-head">
                <strong>{ACTION_LABELS[a.action] ?? a.action}</strong>
                <span className="exception-meta">{new Date(a.created_at).toLocaleString()}</span>
              </div>
              <span className="exception-meta">
                {a.actor_name}
                {a.note ? ` — ${a.note}` : ""}
              </span>
            </div>
          ))}
        </div>
      )}

      {item.available_actions.length > 0 && (
        <div className="trace-section">
          <h3 className="trace-section-title">Take action</h3>
          <input
            placeholder="Optional note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            style={{ background: "var(--panel-alt)", border: "1px solid var(--border)", color: "var(--text)", padding: "10px 12px", borderRadius: 8 }}
          />
          <div className="exception-actions">
            {item.available_actions.map((action) => (
              <button key={action} className="btn-primary" disabled={busy === action} onClick={() => act(action)}>
                {busy === action ? "Working…" : ACTION_LABELS[action] ?? action}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
