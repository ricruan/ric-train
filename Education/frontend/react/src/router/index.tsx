import { useEffect, useState } from 'react'
import { createBrowserRouter, RouterProvider, Navigate, useLocation, RouteObject } from 'react-router-dom'
import { useAuthStore } from '@/store'
import { routes } from './routes'
import { Spin } from 'antd'

/** 需要登录才能访问的路由守卫 */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to={`/login?redirect=${encodeURIComponent(location.pathname)}`} replace />
  }

  return <>{children}</>
}

/** 需要管理员权限的路由守卫 */
function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isAdmin } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to={`/login?redirect=${encodeURIComponent(location.pathname)}`} replace />
  }

  if (!isAdmin()) {
    return <Navigate to="/user/exam" replace />
  }

  return <>{children}</>
}

/** 包装路由，添加守卫 */
function wrapRoutesWithGuards(routeList: RouteObject[]): RouteObject[] {
  return routeList.map((route) => {
    if (route.path === '/admin' || route.path?.startsWith('/admin')) {
      return {
        ...route,
        element: <RequireAdmin>{route.element}</RequireAdmin>,
        children: route.children ? wrapRoutesWithGuards(route.children as RouteObject[]) : undefined,
      } as RouteObject
    }
    if (route.path === '/user' || route.path?.startsWith('/user')) {
      return {
        ...route,
        element: <RequireAuth>{route.element}</RequireAuth>,
        children: route.children ? wrapRoutesWithGuards(route.children as RouteObject[]) : undefined,
      } as RouteObject
    }
    return route
  })
}

const guardedRoutes = wrapRoutesWithGuards(routes)
const router = createBrowserRouter(guardedRoutes)

export default function AppRouter() {
  const { initAuth, isLoading } = useAuthStore()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    initAuth().finally(() => setReady(true))
  }, [initAuth])

  if (!ready || isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  return <RouterProvider router={router} />
}
