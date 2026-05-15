import { lazy, Suspense } from 'react';
import { HashRouter, Routes, Route, NavLink } from 'react-router-dom';

const InterviewAnalysis = lazy(() => import('./pages/InterviewAnalysis'));
const CameraTest = lazy(() => import('./pages/CameraTest'));
const InterviewChat = lazy(() => import('./pages/InterviewChat'));
const InterviewRecordManager = lazy(() => import('./pages/InterviewRecordManager'));

const navItems = [
  { path: '/', label: '面试分析' },
  { path: '/camera-test', label: '摄像头测试' },
  { path: '/interview-chat', label: '模拟面试' },
  { path: '/record-manager', label: '记录管理' },
];

const NavLogo = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="url(#navGrad)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 8, verticalAlign: 'middle' }}>
    <defs><linearGradient id="navGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#00d4ff" /><stop offset="100%" stopColor="#7c3aed" /></linearGradient></defs>
    <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
  </svg>
);

const loadingFallback = (
  <div className="loading" style={{ padding: '80px', textAlign: 'center' }}>
    <span className="loading-spinner" />加载中...
  </div>
);

function Layout() {
  return (
    <div className="app">
      <nav className="app-nav">
        <div className="nav-brand">
          <NavLogo />
          AI 面试系统
        </div>
        <div className="nav-links">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>
      <main className="app-content">
        <Routes>
          <Route path="/" element={<Suspense fallback={loadingFallback}><InterviewAnalysis /></Suspense>} />
          <Route path="/camera-test" element={<Suspense fallback={loadingFallback}><CameraTest /></Suspense>} />
          <Route path="/interview-chat" element={<Suspense fallback={loadingFallback}><InterviewChat /></Suspense>} />
          <Route path="/record-manager" element={<Suspense fallback={loadingFallback}><InterviewRecordManager /></Suspense>} />
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
