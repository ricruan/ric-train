import { lazy, Suspense } from 'react';
import { HashRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom';
import { AuthProvider, RequireAuth, useAuth, DynamicRouter } from '@interview/shared';
import { componentMap } from './router/componentMap';
import { getIcon } from './utils/iconMap';

const Login = lazy(() => import('./pages/Login'));

const loadingFallback = (
  <div className="loading" style={{ padding: '80px', textAlign: 'center' }}>
    <span className="loading-spinner" />加载中...
  </div>
);

function AdminLayout() {
  const { logout, menus } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="sidebar-logo">🎯</span>
          <span className="sidebar-title">管理后台</span>
        </div>
        <nav className="sidebar-menu">
          {menus.map((menu) => (
            <NavLink
              key={menu.id}
              to={menu.path}
              className={({ isActive }) => `menu-item ${isActive ? 'active' : ''}`}
            >
              {(() => {
                const IconComponent = getIcon(menu.icon);
                return IconComponent ? (
                  <span className="menu-icon"><IconComponent /></span>
                ) : null;
              })()}
              <span className="menu-label">{menu.name}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="collapse-btn" onClick={() => {
            logout();
            navigate('/login', { replace: true });
          }}>
            🚪
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Suspense fallback={loadingFallback}>
          <DynamicRouter menus={menus} componentMap={componentMap} />
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
          <Route path="*" element={
            <RequireAuth requireAdmin>
              <AdminLayout />
            </RequireAuth>
          } />
        </Routes>
      </AuthProvider>
    </HashRouter>
  );
}
