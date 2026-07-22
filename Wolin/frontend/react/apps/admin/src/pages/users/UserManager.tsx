import { useState, useEffect } from 'react';
import { Table, Button, Input, message, Popconfirm } from 'antd';
import { getUsers, updateUserStatus, resetUserPassword, type User } from '../../api/users';

export default function UserManager() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState('');

  useEffect(() => {
    loadUsers();
  }, [keyword]);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await getUsers({ keyword, limit: 100 });
      setUsers(data.users || []);
    } catch (err) {
      message.error('加载用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (user: User) => {
    const newStatus = user.status === 'active' ? 'inactive' : 'active';
    try {
      await updateUserStatus(user.id, newStatus);
      message.success('状态更新成功');
      loadUsers();
    } catch (err) {
      message.error('状态更新失败');
    }
  };

  const handleResetPassword = async (user: User) => {
    try {
      await resetUserPassword(user.id, '123456');
      message.success('密码已重置为 123456');
    } catch (err) {
      message.error('密码重置失败');
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id' },
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '状态', dataIndex: 'status', key: 'status' },
    { title: '角色', dataIndex: 'roles', key: 'roles', render: (roles: string[]) => roles?.join(', ') },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, user: User) => (
        <>
          <Button size="small" onClick={() => handleToggleStatus(user)}>
            {user.status === 'active' ? '禁用' : '启用'}
          </Button>
          <Popconfirm title="确定重置密码？" onConfirm={() => handleResetPassword(user)}>
            <Button size="small">重置密码</Button>
          </Popconfirm>
        </>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2>用户管理</h2>
      <Input.Search
        placeholder="搜索用户名/邮箱"
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        style={{ marginBottom: 16, width: 300 }}
      />
      <Table columns={columns} dataSource={users} loading={loading} rowKey="id" />
    </div>
  );
}
