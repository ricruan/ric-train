import { lazy, Suspense } from 'react';
import { HashRouter, Routes, Route, Navigate, NavLink, Outlet } from 'react-router-dom';
import { AuthProvider, RequireAuth } from '@interview/shared';

const Login = lazy(() => import('./pages/Login'));
const RecordManager = lazy(() => import('./pages/records/RecordManager'));

const loadingFallback = (
  <div className="loading" style={{ padding: '80px', textAlign: 'center' }}>
    <span className="loading-spinner" />加载中...
  </div>
);

function AdminLayout() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="sidebar-logo">🎯</span>
          <span className="sidebar-title">管理后台</span>
        </div>
        <nav className="sidebar-menu">
          <NavLink
            to="/records"
            className={({ isActive }) => `menu-item ${isActive ? 'active' : ''}`}
          >
            <span className="menu-icon">📋</span>
            <span className="menu-label">记录管理</span>
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          <button className="collapse-btn" onClick={() => {
            localStorage.removeItem('interview_access_token');
            localStorage.removeItem('interview_refresh_token');
            window.location.hash = '#/login';
          }}>
            🚪
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Suspense fallback={loadingFallback}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <HashRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Suspense fallback={loadingFallback}><Login /></Suspense>} />
          <Route element={
            <RequireAuth requireAdmin>
              <AdminLayout />
            </RequireAuth>
          }>
            <Route index element={<Navigate to="/records" replace />} />
            <Route path="/records" element={<RecordManager />} />
          </Route>
          <Route path="*" element={<Navigate to="/records" replace />} />
        </Routes>
      </AuthProvider>
    </HashRouter>
  );
}
