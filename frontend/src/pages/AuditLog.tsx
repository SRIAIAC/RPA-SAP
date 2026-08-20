import { Fragment, useEffect, useState } from "react";
import { fetchAuditLog } from "../api";
import type { AuditLogEntry } from "../types";

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    fetchAuditLog()
      .then(setEntries)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  return (
    <div className="stack-lg">
      <h2 className="section-title">Audit Log</h2>
      <p className="section-subtitle">
        Every login/logout, workflow execution, exception action, access grant, and admin change — most
        recent 500 entries visible to your account.
      </p>
      {error && <div className="form-error">{error}</div>}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Target</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 && (
              <tr>
                <td colSpan={5} className="empty-row">
                  No audit entries yet.
                </td>
              </tr>
            )}
            {entries.map((entry) => (
              <Fragment key={entry.id}>
                <tr className="row-clickable" onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}>
                  <td>{new Date(entry.created_at).toLocaleString()}</td>
                  <td>{entry.actor_name}</td>
                  <td>
                    <span className="tag tag-dept">{entry.action}</span>
                  </td>
                  <td>
                    {entry.target_type}
                    {entry.target_id ? ` #${entry.target_id}` : ""}
                  </td>
                  <td>
                    <button className="btn-ghost">{expanded === entry.id ? "Hide" : "Details"}</button>
                  </td>
                </tr>
                {expanded === entry.id && entry.detail && (
                  <tr>
                    <td colSpan={5}>
                      <div className="trace-card">
                        <pre>{JSON.stringify(JSON.parse(entry.detail), null, 2)}</pre>
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
