import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchAnalyticsDashboard } from "../api";
import type { AnalyticsDashboard } from "../types";

const CHART_COLORS = ["#4f7cff", "#34c78a", "#f2b84b", "#ef6a6a", "#8fd6b0", "#7fa8ff"];

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalyticsDashboard()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  return (
    <div className="stack-lg">
      <h2 className="section-title">Analytics</h2>
      <p className="section-subtitle">
        Every number below is computed live from real WorkflowRun data — automated processing time is
        measured, not assumed; only each workflow's manual-baseline minutes is a documented estimate.
      </p>
      {error && <div className="form-error">{error}</div>}

      {data && (
        <>
          <div className="hours-saved-hero">
            <div className="hours-saved-value">{data.org.estimated_hours_saved.toLocaleString()} hrs</div>
            <div className="hours-saved-label">Estimated hours saved across all automated workflows</div>
          </div>

          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-dept">Total runs</div>
              <div className="kpi-value">{data.org.total_runs}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-dept">Automation rate</div>
              <div className="kpi-value">{data.org.automation_rate_pct}%</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-dept">Human intervention rate</div>
              <div className="kpi-value">{data.org.human_intervention_rate_pct}%</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-dept">Avg processing time</div>
              <div className="kpi-value">{data.org.avg_processing_seconds.toFixed(1)}s</div>
            </div>
          </div>

          <div className="chart-grid">
            <div className="chart-card">
              <h3 className="chart-card-title">Runs by department</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.departments}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="department" stroke="var(--text-dim)" fontSize={11} />
                  <YAxis stroke="var(--text-dim)" fontSize={11} />
                  <Tooltip contentStyle={{ background: "var(--panel)", border: "1px solid var(--border)" }} />
                  <Legend />
                  <Bar dataKey="completed" name="Completed" fill="#34c78a" />
                  <Bar dataKey="exceptions" name="Exceptions" fill="#ef6a6a" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <h3 className="chart-card-title">Hours saved by department</h3>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={data.departments}
                    dataKey="estimated_hours_saved"
                    nameKey="department"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label={(entry) => `${entry.department}: ${entry.estimated_hours_saved}h`}
                  >
                    {data.departments.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "var(--panel)", border: "1px solid var(--border)" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <h3 className="section-title" style={{ fontSize: 15 }}>
            Workflow KPIs
          </h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Workflow</th>
                  <th>Department</th>
                  <th>Runs</th>
                  <th>Automation rate</th>
                  <th>Avg time</th>
                  <th>Manual baseline</th>
                  <th>Hours saved</th>
                </tr>
              </thead>
              <tbody>
                {data.workflows.map((w) => (
                  <tr key={w.workflow_id}>
                    <td>{w.workflow_name}</td>
                    <td>
                      <span className="tag tag-dept">{w.department}</span>
                    </td>
                    <td>{w.total_runs}</td>
                    <td>{w.automation_rate_pct}%</td>
                    <td>{w.avg_processing_seconds.toFixed(1)}s</td>
                    <td>{w.manual_processing_minutes} min</td>
                    <td>{w.estimated_hours_saved}h</td>
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
