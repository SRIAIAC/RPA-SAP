import { useEffect, useState } from "react";
import { fetchSystemHealth } from "../api";
import type { SystemHealthResponse } from "../types";
import StatusPill from "../components/StatusPill";

export default function SystemHealthPage() {
  const [data, setData] = useState<SystemHealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function load() {
      fetchSystemHealth()
        .then(setData)
        .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    }
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="stack-lg">
      <h2 className="section-title">System Health</h2>
      <p className="section-subtitle">
        Platform mode: <strong>{data?.app_mode ?? "…"}</strong> — 100% self-contained, no external API keys
        or real SAP system required.
      </p>
      {error && <div className="form-error">{error}</div>}

      {data && (
        <>
          <div className="integration-services">
            <div className="integration-service-card">
              <div className="integration-service-name">Backend / Database</div>
              <StatusPill status={data.backend.status} />
              <div className="integration-service-url">{data.backend.db}</div>
            </div>
            <div className="integration-service-card">
              <div className="integration-service-name">Mock SAP</div>
              <StatusPill status={data.mock_sap.status} />
              <div className="integration-service-url">{data.mock_sap.base_url}</div>
            </div>
            <div className="integration-service-card">
              <div className="integration-service-name">Mock Non-SAP</div>
              <StatusPill status={data.mock_non_sap.status} />
              <div className="integration-service-url">{data.mock_non_sap.base_url}</div>
            </div>
          </div>

          <h3 className="section-title" style={{ fontSize: 15 }}>
            Active providers
          </h3>
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-dept">SAP</div>
              <div className="kpi-value">{data.providers.sap}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-dept">AI</div>
              <div className="kpi-value">{data.providers.ai}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-dept">RPA</div>
              <div className="kpi-value">{data.providers.rpa}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-dept">Event Bus</div>
              <div className="kpi-value">{data.providers.event_bus}</div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
