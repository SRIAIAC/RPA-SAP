import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchDashboard, fetchRuns, fetchWorkflows, triggerRun } from "../api";
import { useAuth } from "../auth/AuthContext";
import ManualEntryModal from "../components/ManualEntryModal";
import RunStatusBadge from "../components/RunStatusBadge";
import type { DashboardStats, Run, Workflow } from "../types";

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [triggering, setTriggering] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manualEntryWorkflow, setManualEntryWorkflow] = useState<Workflow | null>(null);

  async function refresh() {
    const [s, w, r] = await Promise.all([fetchDashboard(), fetchWorkflows(), fetchRuns()]);
    setStats(s);
    setWorkflows(w);
    setRuns(r);
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(() => {
      fetchRuns().then(setRuns).catch(() => {});
      fetchDashboard().then(setStats).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  async function handleRun(workflowId: number) {
    setError(null);
    setTriggering(workflowId);
    try {
      const run = await triggerRun(workflowId);
      await refresh();
      navigate(`/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to trigger run");
    } finally {
      setTriggering(null);
    }
  }

  function handleManualEntrySubmitted(run: Run) {
    setManualEntryWorkflow(null);
    refresh();
    navigate(`/runs/${run.id}`);
  }

  const byDept = groupBy(workflows, (w) => w.department);

  return (
    <div className="stack-lg">
      <section>
        <h2 className="section-title">Today at a glance</h2>
        <div className="kpi-grid">
          {stats.map((s) => (
            <div className="kpi-card" key={s.department}>
              <div className="kpi-dept">{s.department}</div>
              <div className="kpi-row">
                <div className="kpi-value">{s.workflows_available}</div>
                <div className="kpi-label">workflows you can run</div>
              </div>
              <div className="kpi-row">
                <div className="kpi-value">{s.runs_today}</div>
                <div className="kpi-label">runs today</div>
              </div>
              <div className="kpi-row">
                <div className="kpi-value">{s.completed_today}</div>
                <div className="kpi-label">completed</div>
              </div>
              <div className="kpi-row">
                <div className={`kpi-value ${s.open_exceptions > 0 ? "kpi-alert" : ""}`}>{s.open_exceptions}</div>
                <div className="kpi-label">open exceptions</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {error && <div className="form-error">{error}</div>}

      <section>
        <h2 className="section-title">RPA workflows</h2>
        {Object.entries(byDept).map(([dept, wfs]) => (
          <div key={dept} className="dept-block">
            {user?.level === "Admin" && <h3 className="dept-heading">{dept}</h3>}
            <div className="workflow-grid">
              {wfs.map((wf) => (
                <div className={`workflow-card ${wf.can_run ? "" : "locked"}`} key={wf.id}>
                  <div className="workflow-card-head">
                    <span className="workflow-name" style={{ cursor: "pointer" }} onClick={() => navigate(`/workflows/${wf.id}`)}>
                      {wf.name}
                    </span>
                    {!wf.can_run && <span className="lock-badge">No access</span>}
                  </div>
                  <p className="workflow-desc">{wf.description}</p>
                  <div className="workflow-systems">
                    <span className="tag tag-sap">{wf.sap_systems}</span>
                    <span className="tag tag-nonsap">{wf.non_sap_systems}</span>
                  </div>
                  {wf.can_run ? (
                    <div className="exception-actions">
                      <button
                        className="btn-primary"
                        style={{ flex: 1 }}
                        disabled={triggering === wf.id}
                        onClick={() => handleRun(wf.id)}
                      >
                        {triggering === wf.id ? "Starting…" : "Run now"}
                      </button>
                      <button
                        className="btn-ghost"
                        disabled={triggering === wf.id}
                        onClick={() => setManualEntryWorkflow(wf)}
                      >
                        Enter manually
                      </button>
                    </div>
                  ) : (
                    <button className="btn-primary btn-block" disabled>
                      Request access from Dept Head
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>

      <section>
        <h2 className="section-title">Recent runs</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Workflow</th>
                <th>Department</th>
                <th>Triggered by</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="row-clickable" onClick={() => navigate(`/runs/${run.id}`)}>
                  <td>{run.workflow_name}</td>
                  <td>{run.department}</td>
                  <td>{run.triggered_by_name}</td>
                  <td>
                    <RunStatusBadge status={run.status} />
                  </td>
                  <td>
                    {run.current_step}/{run.total_steps}
                  </td>
                  <td>{new Date(run.started_at).toLocaleTimeString()}</td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr>
                  <td colSpan={6} className="empty-row">
                    No runs yet — trigger a workflow above.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {manualEntryWorkflow && (
        <ManualEntryModal
          workflow={manualEntryWorkflow}
          onClose={() => setManualEntryWorkflow(null)}
          onSubmitted={handleManualEntrySubmitted}
        />
      )}
    </div>
  );
}

function groupBy<T, K extends string | number>(items: T[], keyFn: (item: T) => K): Record<K, T[]> {
  return items.reduce((acc, item) => {
    const key = keyFn(item);
    (acc[key] ??= []).push(item);
    return acc;
  }, {} as Record<K, T[]>);
}
