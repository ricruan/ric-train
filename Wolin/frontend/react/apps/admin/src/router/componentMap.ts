import { lazy } from 'react';

export const componentMap: Record<string, React.LazyExoticComponent<React.ComponentType>> = {
  'pages/records/RecordManager': lazy(() => import('../pages/records/RecordManager')),
  'pages/users/UserManager': lazy(() => import('../pages/users/UserManager')),
  'pages/roles/RoleManager': lazy(() => import('../pages/roles/RoleManager')),
};
