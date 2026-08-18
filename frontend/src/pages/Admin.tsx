import { FormEvent, useEffect, useState } from "react";
import {
  createAdminUser,
  fetchAdminUsers,
  fetchAdminWorkflows,
  fetchUserAccess,
  setUserAccess,
  updateAdminUser,
} from "../api";
import { useAuth } from "../auth/AuthContext";
import type { Department, Level, User, Workflow } from "../types";

const ALL_DEPARTMENTS: Department[] = ["Procurement", "Maintenance", "Finance", "HSE", "Production"];
const MANAGEABLE_LEVELS: Level[] = ["Manager", "Senior Manager", "Department Head", "Admin"];

export default function AdminPage() {
  const { user: actor } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    username: "",
    password: "Demo@123",
    full_name: "",
    department: actor?.level === "Admin" ? ALL_DEPARTMENTS[0] : (actor?.department as Department),
    level: "Manager" as Level,
  });
  const [accessPanelUserId, setAccessPanelUserId] = useState<number | null>(null);
  const [accessSelection, setAccessSelection] = useState<Set<number>>(new Set());
  const [accessSaving, setAccessSaving] = useState(false);

  const departmentOptions = actor?.level === "Admin" ? ALL_DEPARTMENTS : [actor?.department as Department];
  const levelOptions = actor?.level === "Admin" ? MANAGEABLE_LEVELS : (["Manager", "Senior Manager"] as Level[]);

  async function refresh() {
    const [u, w] = await Promise.all([fetchAdminUsers(), fetchAdminWorkflows()]);
    setUsers(u);
    setWorkflows(w);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCreating(true);
    try {
      await createAdminUser(form);
      setForm((f) => ({ ...f, username: "", full_name: "" }));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(u: User) {
    setError(null);
    try {
      await updateAdminUser(u.id, { active: !u.active });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update user");
    }
  }

  async function openAccessPanel(u: User) {
    setAccessPanelUserId(u.id);
    const granted = await fetchUserAccess(u.id);
    setAccessSelection(new Set(granted));
  }

  async function saveAccess(userId: number) {
    setAccessSaving(true);
    setError(null);
    try {
      await setUserAccess(userId, Array.from(accessSelection));
      setAccessPanelUserId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save access");
    } finally {
      setAccessSaving(false);
    }
  }

  const panelUser = users.find((u) => u.id === accessPanelUserId);
  const panelWorkflows = panelUser ? workflows.filter((w) => w.department === panelUser.department) : [];

  return (
    <div className="stack-lg">
      <h2 className="section-title">Access management</h2>
      <p className="section-subtitle">
        {actor?.level === "Admin"
          ? "Create and manage users across every department, and control exactly which workflows each Manager can run."
          : `Manage Managers and Senior Managers within ${actor?.department}, and control which workflows your Managers can run.`}
      </p>
      {error && <div className="form-error">{error}</div>}

      <div className="admin-grid">
        <div className="admin-panel">
          <h3 className="dept-heading">Create user</h3>
          <form onSubmit={handleCreate} className="stack-md">
            <label>
              Username
              <input
                value={form.username}
                onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                placeholder="e.g. sunita.rao"
                required
              />
            </label>
            <label>
              Full name
              <input
                value={form.full_name}
                onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                required
              />
            </label>
            <label>
              Temporary password
              <input value={form.password} onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} required />
            </label>
            <label>
              Department
              <select
                value={form.department}
                onChange={(e) => setForm((f) => ({ ...f, department: e.target.value as Department }))}
                disabled={departmentOptions.length === 1}
              >
                {departmentOptions.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Level
              <select value={form.level} onChange={(e) => setForm((f) => ({ ...f, level: e.target.value as Level }))}>
                {levelOptions.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
            <button className="btn-primary" type="submit" disabled={creating}>
              {creating ? "Creating…" : "Create user"}
            </button>
          </form>
        </div>

        <div className="admin-panel admin-panel-wide">
          <h3 className="dept-heading">Users</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Username</th>
                  <th>Department</th>
                  <th>Level</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.full_name}</td>
                    <td>
                      <code>{u.username}</code>
                    </td>
                    <td>{u.department}</td>
                    <td>{u.level}</td>
                    <td>
                      <span className={u.active ? "badge badge-completed" : "badge badge-exception"}>
                        {u.active ? "Active" : "Disabled"}
                      </span>
                    </td>
                    <td className="row-actions">
                      {u.level === "Manager" && (
                        <button className="btn-ghost" onClick={() => openAccessPanel(u)}>
                          Manage access
                        </button>
                      )}
                      {u.id !== actor?.id && (
                        <button className="btn-ghost" onClick={() => toggleActive(u)}>
                          {u.active ? "Disable" : "Enable"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {panelUser && (
        <div className="modal-backdrop" onClick={() => setAccessPanelUserId(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3 className="dept-heading">Workflow access — {panelUser.full_name}</h3>
            <p className="modal-subtitle">Choose which {panelUser.department} workflows this Manager can trigger.</p>
            <div className="checkbox-list">
              {panelWorkflows.map((wf) => (
                <label key={wf.id} className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={accessSelection.has(wf.id)}
                    onChange={(e) => {
                      const next = new Set(accessSelection);
                      if (e.target.checked) next.add(wf.id);
                      else next.delete(wf.id);
                      setAccessSelection(next);
                    }}
                  />
                  {wf.name}
                </label>
              ))}
            </div>
            <div className="modal-actions">
              <button className="btn-ghost" onClick={() => setAccessPanelUserId(null)}>
                Cancel
              </button>
              <button className="btn-primary" disabled={accessSaving} onClick={() => saveAccess(panelUser.id)}>
                {accessSaving ? "Saving…" : "Save access"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
