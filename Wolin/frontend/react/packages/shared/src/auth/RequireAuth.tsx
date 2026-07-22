import type { ReactElement } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider.js';

interface RequireAuthProps {
  children: ReactElement;
  requireAdmin?: boolean;
}

export function RequireAuth({ children, requireAdmin = false }: RequireAuthProps) {
  const { user, ready } = useAuth();
  const location = useLocation();

  if (!ready) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', color: '#94a3b8', fontSize: '16px',
      }}>
        <span style={{ marginRight: 8 }}>⏳</span> 验证身份中...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireAdmin && !user.is_admin) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
