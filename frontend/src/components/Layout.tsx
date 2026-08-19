import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();
  if (!user) return null;

  const canSeeAdmin = user.level === "Senior Manager" || user.level === "Department Head" || user.level === "Admin";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">RPA</span>
          <span className="brand-name">Ops Console</span>
        </div>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            Dashboard
          </NavLink>
          <NavLink to="/exceptions" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            Exception Queue
          </NavLink>
          <NavLink to="/mailroom" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            Mailroom
          </NavLink>
          {canSeeAdmin && (
            <NavLink to="/admin" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
              Access Management
            </NavLink>
          )}
        </nav>
        <div className="sidebar-footer">Oil &amp; Gas RPA/SAP Demo</div>
      </aside>
      <div className="main-col">
        <header className="topbar">
          <div>
            <div className="topbar-dept">{user.department === "Admin" ? "All Departments" : user.department}</div>
          </div>
          <div className="topbar-user">
            <div className="user-meta">
              <span className="user-name">{user.full_name}</span>
              <span className="user-level">{user.level}</span>
            </div>
            <button className="btn-ghost" onClick={logout}>
              Log out
            </button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
