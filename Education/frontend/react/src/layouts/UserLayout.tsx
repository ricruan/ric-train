import { Outlet } from 'react-router-dom'

export default function UserLayout() {
  return (
    <div>
      <div>User Header</div>
      <Outlet />
    </div>
  )
}
