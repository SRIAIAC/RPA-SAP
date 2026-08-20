import { useEffect, useState } from "react";
import { fetchIntegrationStatus } from "../api";
import type { IntegrationStatusResponse } from "../types";
import StatusPill from "../components/StatusPill";

export default function IntegrationMonitorPage() {
  const [data, setData] = useState<IntegrationStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function load() {
      fetchIntegrationStatus()
        .then(setData)
        .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    }
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="stack-lg">
      <h2 className="section-title">Integration Monitor</h2>
      <p className="section-subtitle">
        Live health and call statistics for every mock SAP / non-SAP integration, aggregated from every
        SAPIntegrationService / NonSAPIntegrationService call made by the workflow engine.
      </p>
      {error && <div className="form-error">{error}</div>}

      {data && (
        <>
          <div className="integration-services">
            {Object.entries(data.services).map(([name, health]) => (
              <div key={name} className="integration-service-card">
                <div className="integration-service-name">{name}</div>
                <StatusPill status={health.status} />
                <div className="integration-service-url">{health.base_url}</div>
              </div>
            ))}
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>System</th>
                  <th>Requests</th>
                  <th>Success rate</th>
                  <th>Avg latency</th>
                  <th>Last success</th>
                  <th>Last error</th>
                </tr>
              </thead>
              <tbody>
                {data.integrations.length === 0 && (
                  <tr>
                    <td colSpan={7} className="empty-row">
                      No integration calls recorded yet — run a workflow to populate this view.
                    </td>
                  </tr>
                )}
                {data.integrations.map((row) => (
                  <tr key={`${row.provider}-${row.system}`}>
                    <td>{row.provider === "sap" ? "SAP" : "Non-SAP"}</td>
                    <td>{row.system}</td>
                    <td>
                      {row.requests} ({row.successes} ok / {row.failures} failed)
                    </td>
                    <td>{row.success_rate_pct}%</td>
                    <td>{row.avg_latency_ms} ms</td>
                    <td>{row.last_success_at ? new Date(row.last_success_at).toLocaleString() : "—"}</td>
                    <td>{row.last_error ? <span className="exception-reason">{row.last_error}</span> : "—"}</td>
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
