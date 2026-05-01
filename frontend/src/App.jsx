/**
 * App.jsx
 * ───────
 * Root router for LexFlow.
 * Protected routes check auth from Zustand store before rendering.
 * Role-based guards prevent wrong-role access.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import useAuthStore from './store/authStore';
import Login from './pages/Login';
import StudentPortal from './pages/StudentPortal';
import GovDashboard from './pages/GovDashboard';
import CaseDetail from './pages/CaseDetail';
import AdminPanel from './pages/AdminPanel';

/** Requires authentication; redirects to /login if no token */
function RequireAuth({ children }) {
  const { token } = useAuthStore();
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

/** Requires a specific role; redirects to /login if role doesn't match */
function RequireRole({ role, children }) {
  const { user } = useAuthStore();
  if (!user || user.role !== role) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const { user } = useAuthStore();

  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login />} />

        {/* Role-based home redirect */}
        <Route
          path="/"
          element={
            user
              ? <Navigate to={user.role === 'admin' ? '/admin' : user.role === 'student' ? '/student' : '/dashboard'} replace />
              : <Navigate to="/login" replace />
          }
        />

        {/* Student */}
        <Route
          path="/student"
          element={
            <RequireAuth>
              <RequireRole role="student">
                <StudentPortal />
              </RequireRole>
            </RequireAuth>
          }
        />

        {/* Government Official */}
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <RequireRole role="official">
                <GovDashboard />
              </RequireRole>
            </RequireAuth>
          }
        />
        <Route
          path="/dashboard/case/:id"
          element={
            <RequireAuth>
              <RequireRole role="official">
                <CaseDetail />
              </RequireRole>
            </RequireAuth>
          }
        />

        {/* Admin */}
        <Route
          path="/admin"
          element={
            <RequireAuth>
              <RequireRole role="admin">
                <AdminPanel />
              </RequireRole>
            </RequireAuth>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
