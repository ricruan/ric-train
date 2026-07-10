import { useEffect, useState, useCallback } from 'react'
import { Table, Tag, Space, Modal, Select, Button, message, Popconfirm, Card, Input } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { authApi } from '@/api/auth'
import { SOURCE_MODULE } from '@/types'
import type { AdminUserInfo, RoleInfo } from '@/types'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'

export default function UsersPage() {
  const [users, setUsers] = useState<AdminUserInfo[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [offset, setOffset] = useState(0)
  const [limit] = useState(20)

  const [roles, setRoles] = useState<RoleInfo[]>([])

  // 角色管理弹窗
  const [roleModalOpen, setRoleModalOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<AdminUserInfo | null>(null)
  const [selectedRoles, setSelectedRoles] = useState<string[]>([])

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const res = await authApi.listUsers({ source_module: SOURCE_MODULE, keyword: keyword || undefined, limit, offset })
      setUsers(res.data.users)
      setTotal(res.data.total)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [keyword, limit, offset])

  useEffect(() => { fetchUsers() }, [fetchUsers])

  const fetchRoles = async () => {
    try {
      const res = await authApi.listRoles()
      setRoles(res.data.roles)
    } catch { /* ignore */ }
  }

  useEffect(() => { fetchRoles() }, [])

  const handleToggleStatus = async (userId: number, currentStatus: string) => {
    const newStatus = currentStatus === 'active' ? 'inactive' : 'active'
    try {
      await authApi.updateStatus(userId, newStatus)
      message.success('状态已更新')
      fetchUsers()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '操作失败')
    }
  }

  const handleResetPassword = async (userId: number) => {
    try {
      await authApi.resetPassword(userId, '123456')
      message.success('密码已重置为 123456')
    } catch (error) {
      message.error(error instanceof Error ? error.message : '操作失败')
    }
  }

  const handleOpenRoleModal = async (user: AdminUserInfo) => {
    setSelectedUser(user)
    try {
      const res = await authApi.getUserRoles(user.id)
      setSelectedRoles(res.data.roles.map((r: RoleInfo) => r.name))
    } catch {
      setSelectedRoles([])
    }
    setRoleModalOpen(true)
  }

  const handleSetRoles = async () => {
    if (!selectedUser) return
    try {
      await authApi.setUserRoles(selectedUser.id, selectedRoles, SOURCE_MODULE)
      message.success('角色已更新')
      setRoleModalOpen(false)
      fetchUsers()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '操作失败')
    }
  }

  const columns: ColumnsType<AdminUserInfo> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '用户名', dataIndex: 'username', width: 120 },
    { title: '邮箱', dataIndex: 'email', width: 180, render: (v: string) => v || '-' },
    { title: '手机', dataIndex: 'phone', width: 130, render: (v: string) => v || '-' },
    {
      title: '角色', dataIndex: 'roles', width: 200,
      render: (val: Array<{ display_name: string }>) => val?.map((r) => <Tag key={r.display_name}>{r.display_name}</Tag>) || '-',
    },
    {
      title: '状态', dataIndex: 'status', width: 80,
      render: (val: string) => <Tag color={val === 'active' ? 'green' : 'red'}>{val === 'active' ? '正常' : '禁用'}</Tag>,
    },
    { title: '注册时间', dataIndex: 'created_at', width: 170, render: (v: string) => v?.substring(0, 19) || '-' },
    {
      title: '操作', width: 240,
      render: (_, record) => (
        <Space>
          <a onClick={() => handleOpenRoleModal(record)}>角色</a>
          <Popconfirm title={`确定${record.status === 'active' ? '禁用' : '启用'}此用户？`} onConfirm={() => handleToggleStatus(record.id, record.status)}>
            <a>{record.status === 'active' ? '禁用' : '启用'}</a>
          </Popconfirm>
          <Popconfirm title="确定重置密码为 123456？" onConfirm={() => handleResetPassword(record.id)}>
            <a style={{ color: 'orange' }}>重置密码</a>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const handleTableChange = (pagination: TablePaginationConfig) => {
    setOffset(((pagination.current || 1) - 1) * limit)
  }

  return (
    <Card title="用户管理">
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索用户名/邮箱/手机"
          prefix={<SearchOutlined />}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={() => setOffset(0)}
          style={{ width: 250 }}
          allowClear
        />
        <Button type="primary" onClick={() => setOffset(0)}>搜索</Button>
      </Space>

      <Table
        columns={columns}
        dataSource={users}
        rowKey="id"
        loading={loading}
        pagination={{ current: Math.floor(offset / limit) + 1, pageSize: limit, total }}
        onChange={handleTableChange}
      />

      {/* 角色分配弹窗 */}
      <Modal
        title={`分配角色 - ${selectedUser?.username}`}
        open={roleModalOpen}
        onOk={handleSetRoles}
        onCancel={() => setRoleModalOpen(false)}
        okText="保存"
        cancelText="取消"
      >
        <Select
          mode="multiple"
          style={{ width: '100%' }}
          placeholder="选择角色"
          value={selectedRoles}
          onChange={setSelectedRoles}
          options={roles.map((r) => ({ value: r.name, label: `${r.display_name} (${r.name})` }))}
        />
      </Modal>
    </Card>
  )
}
