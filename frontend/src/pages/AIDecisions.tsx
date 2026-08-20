import { Fragment, useEffect, useState } from "react";
import { fetchAiDecisions } from "../api";
import type { AIDecision } from "../types";

export default function AIDecisionsPage() {
  const [decisions, setDecisions] = useState<AIDecision[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [useCaseFilter, setUseCaseFilter] = useState<string>("");

  useEffect(() => {
    fetchAiDecisions(useCaseFilter ? { use_case: useCaseFilter } : undefined)
      .then(setDecisions)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [useCaseFilter]);

  const useCases = Array.from(new Set(decisions.map((d) => d.use_case))).sort();

  return (
    <div className="stack-lg">
      <h2 className="section-title">AI Decisions</h2>
      <p className="section-subtitle">
        Every MockAIProvider call across every workflow — input, classification, confidence, and
        recommendation. AI never decides directly; see each run's Business Rules step for the final
        decision.
      </p>
      {error && <div className="form-error">{error}</div>}

      <div className="stack-md">
        <select
          value={useCaseFilter}
          onChange={(e) => setUseCaseFilter(e.target.value)}
          style={{ maxWidth: 280, background: "var(--panel-alt)", border: "1px solid var(--border)", color: "var(--text)", padding: "8px 10px", borderRadius: 8 }}
        >
          <option value="">All use cases</option>
          {useCases.map((uc) => (
            <option key={uc} value={uc}>
              {uc}
            </option>
          ))}
        </select>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Use case</th>
              <th>Classification</th>
              <th>Confidence</th>
              <th>Recommendation</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {decisions.length === 0 && (
              <tr>
                <td colSpan={6} className="empty-row">
                  No AI decisions recorded yet — run a workflow to populate this view.
                </td>
              </tr>
            )}
            {decisions.map((d) => (
              <Fragment key={d.id}>
                <tr className="row-clickable" onClick={() => setExpanded(expanded === d.id ? null : d.id)}>
                  <td>{new Date(d.created_at).toLocaleString()}</td>
                  <td>
                    <span className="tag tag-dept">{d.use_case}</span>
                  </td>
                  <td>{d.classification ?? "—"}</td>
                  <td>{d.confidence != null ? `${Math.round(d.confidence * 100)}%` : "—"}</td>
                  <td>{d.recommendation ?? "—"}</td>
                  <td>
                    <button className="btn-ghost">{expanded === d.id ? "Hide" : "Details"}</button>
                  </td>
                </tr>
                {expanded === d.id && (
                  <tr>
                    <td colSpan={6}>
                      <div className="trace-card">
                        <div className="trace-card-head">
                          <strong>Input</strong>
                          {d.workflow_run_id && <span className="exception-meta">Run #{d.workflow_run_id}</span>}
                        </div>
                        <pre>{d.input_summary}</pre>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
