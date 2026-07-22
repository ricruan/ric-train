import { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import type { MenuItem } from '../api/menus.js';

interface DynamicRouterProps {
  menus: MenuItem[];
  componentMap: Record<string, React.LazyExoticComponent<React.ComponentType>>;
}

function renderRoutes(
  menus: MenuItem[],
  componentMap: Record<string, React.LazyExoticComponent<React.ComponentType>>,
): React.ReactNode[] {
  const routes: React.ReactNode[] = [];

  for (const menu of menus) {
    const Component = componentMap[menu.component];

    if (Component) {
      routes.push(
        <Route
          key={menu.id}
          path={menu.path}
          element={
            <Suspense fallback={<div>加载中...</div>}>
              <Component />
            </Suspense>
          }
        />,
      );
    }

    if (menu.children && menu.children.length > 0) {
      routes.push(...renderRoutes(menu.children, componentMap));
    }
  }

  return routes;
}

export function DynamicRouter({ menus, componentMap }: DynamicRouterProps) {
  if (menus.length === 0) {
    return <div>暂无菜单权限</div>;
  }

  const firstMenu = menus[0];

  return (
    <Routes>
      <Route index element={<Navigate to={firstMenu.path} replace />} />
      {renderRoutes(menus, componentMap)}
      <Route path="*" element={<Navigate to={firstMenu.path} replace />} />
    </Routes>
  );
}
