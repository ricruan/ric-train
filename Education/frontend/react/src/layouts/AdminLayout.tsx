import { Outlet } from 'react-router-dom'

export default function AdminLayout() {
  return (
    <div>
      <div>Admin Header</div>
      <Outlet />
    </div>
  )
}
