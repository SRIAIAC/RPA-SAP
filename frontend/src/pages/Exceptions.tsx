import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchExceptions, resolveException } from "../api";
import type { ExceptionItem } from "../types";

export default function ExceptionsPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<ExceptionItem[]>([]);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setItems(await fetchExceptions());
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 4000);
    return () => clearInterval(interval);
  }, []);

  async function handleResolve(id: number) {
    setError(null);
    setBusyId(id);
    try {
      await resolveException(id, notes[id]?.trim() || "Reviewed and resolved.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve exception");
    } finally {
      setBusyId(null);
    }
  }

  const open = items.filter((i) => i.status === "Open");
  const resolved = items.filter((i) => i.status === "Resolved");

  return (
    <div className="stack-lg">
      <h2 className="section-title">Exception queue</h2>
      <p className="section-subtitle">
        Runs the bots couldn't complete automatically. Senior Manager level and above can review and resolve.
      </p>
      {error && <div className="form-error">{error}</div>}

      <div className="exception-list">
        {open.length === 0 && <div className="empty-row">No open exceptions. Clean queue.</div>}
        {open.map((item) => (
          <div className="exception-card" key={item.id}>
            <div className="exception-head">
              <span className="exception-workflow">{item.workflow_name}</span>
              <span className="tag tag-dept">{item.department}</span>
            </div>
            <div className="exception-reason">{item.reason}</div>
            <div className="exception-meta">Raised {new Date(item.raised_at).toLocaleString()}</div>
            <div className="exception-actions">
              <input
                placeholder="Resolution note (optional)"
                value={notes[item.id] ?? ""}
                onChange={(e) => setNotes((prev) => ({ ...prev, [item.id]: e.target.value }))}
              />
              <button className="btn-primary" disabled={busyId === item.id} onClick={() => handleResolve(item.id)}>
                {busyId === item.id ? "Resolving…" : "Mark resolved"}
              </button>
              <Link to={`/exceptions/${item.id}`} className="btn-ghost">
                View full trace
              </Link>
            </div>
          </div>
        ))}
      </div>

      {resolved.length > 0 && (
        <>
          <h3 className="dept-heading">Recently resolved</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Workflow</th>
                  <th>Department</th>
                  <th>Reason</th>
                  <th>Resolved by</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {resolved.map((item) => (
                  <tr key={item.id} className="row-clickable" onClick={() => navigate(`/exceptions/${item.id}`)}>
                    <td>{item.workflow_name}</td>
                    <td>{item.department}</td>
                    <td>{item.reason}</td>
                    <td>{item.resolved_by_name}</td>
                    <td>{item.resolution_note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
