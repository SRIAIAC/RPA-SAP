import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const DEMO_ACCOUNTS = [
  { label: "Procurement — Manager", username: "asha.rao" },
  { label: "Procurement — Dept Head", username: "neha.kapoor" },
  { label: "Maintenance — Manager", username: "rahul.verma" },
  { label: "Finance — Senior Manager", username: "karan.singh" },
  { label: "HSE — Manager", username: "farhan.ali" },
  { label: "Production — Dept Head", username: "arjun.reddy" },
  { label: "System Admin", username: "admin" },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("Demo@123");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-header">
          <span className="brand-mark">RPA</span>
          <h1>Ops Console</h1>
          <p>RPA across SAP &amp; non-SAP systems — Oil &amp; Gas demo</p>
        </div>
        <form onSubmit={handleSubmit} className="login-form">
          <label>
            Username
            <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. asha.rao" required />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          {error && <div className="form-error">{error}</div>}
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="demo-accounts">
          <div className="demo-accounts-title">Demo accounts (password: Demo@123)</div>
          <div className="demo-accounts-grid">
            {DEMO_ACCOUNTS.map((acc) => (
              <button key={acc.username} type="button" className="demo-chip" onClick={() => setUsername(acc.username)}>
                <span>{acc.label}</span>
                <code>{acc.username}</code>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
