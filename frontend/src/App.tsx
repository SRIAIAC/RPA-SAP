import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import AdminPage from "./pages/Admin";
import AIDecisionsPage from "./pages/AIDecisions";
import AnalyticsPage from "./pages/Analytics";
import AuditLogPage from "./pages/AuditLog";
import Dashboard from "./pages/Dashboard";
import DemoScenariosPage from "./pages/DemoScenarios";
import ExceptionDetailPage from "./pages/ExceptionDetail";
import ExceptionsPage from "./pages/Exceptions";
import IntegrationMonitorPage from "./pages/IntegrationMonitor";
import Login from "./pages/Login";
import MailroomPage from "./pages/Mailroom";
import RunDetail from "./pages/RunDetail";
import SystemHealthPage from "./pages/SystemHealth";
import WorkflowDetailPage from "./pages/WorkflowDetail";

function RequireAuth({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loading">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="runs/:runId" element={<RunDetail />} />
        <Route path="workflows/:workflowId" element={<WorkflowDetailPage />} />
        <Route path="exceptions" element={<ExceptionsPage />} />
        <Route path="exceptions/:exceptionId" element={<ExceptionDetailPage />} />
        <Route path="mailroom" element={<MailroomPage />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="integrations" element={<IntegrationMonitorPage />} />
        <Route path="ai-decisions" element={<AIDecisionsPage />} />
        <Route path="audit-log" element={<AuditLogPage />} />
        <Route path="demo-scenarios" element={<DemoScenariosPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="system-health" element={<SystemHealthPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
