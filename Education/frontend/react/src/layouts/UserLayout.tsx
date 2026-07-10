import { Outlet, useNavigate } from 'react-router-dom'
import { Dropdown, Avatar } from 'antd'
import { LogoutOutlined, UserOutlined, HistoryOutlined } from '@ant-design/icons'
import { useAuthStore } from '@/store'
import type { MenuProps } from 'antd'

export default function UserLayout() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const userMenuItems: MenuProps['items'] = [
    { key: 'history', icon: <HistoryOutlined />, label: '考试历史', onClick: () => navigate('/user/history') },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/user/exam')}>
            <span className="text-xl">📚</span>
            <span className="text-lg font-semibold text-gray-800">Education</span>
          </div>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div className="flex items-center gap-2 cursor-pointer hover:bg-gray-100 px-3 py-1.5 rounded-lg transition">
              <Avatar size="small" icon={<UserOutlined />} />
              <span className="text-sm text-gray-600">{user?.username}</span>
            </div>
          </Dropdown>
        </div>
      </header>

      {/* 内容区域 */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
