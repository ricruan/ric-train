import { lazy, Suspense, useState } from 'react';
import { HashRouter, Routes, Route, NavLink } from 'react-router-dom';

const InterviewAnalysis = lazy(() => import('./pages/InterviewAnalysis'));
const CameraTest = lazy(() => import('./pages/CameraTest'));
const InterviewChat = lazy(() => import('./pages/InterviewChat'));

const navItems = [
  { path: '/', label: '面试分析', icon: '📊' },
  { path: '/interview-chat', label: '模拟面试', icon: '🎤' },
  { path: '/camera-test', label: '摄像头测试', icon: '📷' },
];

const loadingFallback = (
  <div className="loading" style={{ padding: '80px', textAlign: 'center' }}>
    <span className="loading-spinner" />加载中...
  </div>
);

function Layout() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="app-layout">
      <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <span className="sidebar-logo">🎯</span>
          {!collapsed && <span className="sidebar-title">AI 面试系统</span>}
        </div>
        <nav className="sidebar-menu">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `menu-item ${isActive ? 'active' : ''}`}
              end={item.path === '/'}
            >
              <span className="menu-icon">{item.icon}</span>
              {!collapsed && <span className="menu-label">{item.label}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="collapse-btn" onClick={() => setCollapsed(!collapsed)}>
            {collapsed ? '▶' : '◀'}
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Suspense fallback={loadingFallback}><InterviewAnalysis /></Suspense>} />
          <Route path="/camera-test" element={<Suspense fallback={loadingFallback}><CameraTest /></Suspense>} />
          <Route path="/interview-chat" element={<Suspense fallback={loadingFallback}><InterviewChat /></Suspense>} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <HashRouter>
      <Layout />
    </HashRouter>
  );
}
