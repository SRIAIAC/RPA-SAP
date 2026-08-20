import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchDemoScenarios, runDemoScenario } from "../api";
import type { DemoScenario } from "../types";
import StatusPill from "../components/StatusPill";

export default function DemoScenariosPage() {
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchDemoScenarios()
      .then(setScenarios)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  async function run(scenario: DemoScenario) {
    setError(null);
    setRunning(scenario.id);
    try {
      const runResult = await runDemoScenario(scenario.id);
      navigate(`/runs/${runResult.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run scenario");
      setRunning(null);
    }
  }

  const categories = Array.from(new Set(scenarios.map((s) => s.category)));

  return (
    <div className="stack-lg">
      <h2 className="section-title">Demo Scenarios</h2>
      <p className="section-subtitle">
        Deterministic scenario variants that run through the exact same workflow engine as a normal
        Dashboard "Run now" click — nothing here is a separate fake demo path.
      </p>
      {error && <div className="form-error">{error}</div>}

      {categories.map((category) => (
        <div key={category} className="scenario-category">
          <h3 className="dept-heading">{category}</h3>
          <div className="scenario-grid">
            {scenarios
              .filter((s) => s.category === category)
              .map((scenario) => (
                <div key={scenario.id} className="scenario-tile">
                  <StatusPill status={scenario.variant} />
                  <div className="scenario-label">{scenario.label}</div>
                  <button className="btn-primary" disabled={running === scenario.id} onClick={() => run(scenario)}>
                    {running === scenario.id ? "Running…" : "Run scenario"}
                  </button>
                </div>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}
