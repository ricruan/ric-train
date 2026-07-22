import { useState, useEffect } from 'react';
import { getUsers, updateUserStatus, resetUserPassword, type User } from '../../api/users';
import { Toast } from '@interview/shared';

export default function UserManager() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    loadUsers();
  }, [keyword, refreshKey]);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await getUsers({ keyword, limit: 100, source_module: 'wolin' });
      setUsers(data.users || []);
    } catch (err) {
      Toast.error('加载用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (user: User) => {
    const newStatus = user.status === 'active' ? 'inactive' : 'active';
    try {
      await updateUserStatus(user.id, newStatus);
      Toast.success('状态更新成功');
      setRefreshKey(k => k + 1);
    } catch (err) {
      Toast.error('状态更新失败');
    }
  };

  const handleResetPassword = async (user: User) => {
    try {
      await resetUserPassword(user.id, '123456');
      Toast.success('密码已重置为 123456');
    } catch (err) {
      Toast.error('密码重置失败');
    }
  };

  return (
    <div className="page manager-page">
      <div className="container">
        <h1 className="title">用户管理</h1>

        <div className="toolbar">
          <input
            type="text"
            placeholder="搜索用户名/邮箱"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            style={{
              padding: '9px 14px',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '14px',
              color: 'var(--text-primary)',
              width: '300px',
            }}
          />
          <span className="record-count">
            共 <strong>{users.length}</strong> 个用户
          </span>
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>用户名</th>
                <th>邮箱</th>
                <th>状态</th>
                <th>角色</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '40px' }}>
                    加载中...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="empty-state">
                    暂无用户数据
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td>{user.username}</td>
                    <td>{user.email || '-'}</td>
                    <td>
                      <span className={`status-badge ${user.status === 'active' ? 'status-completed' : 'status-failed'}`}>
                        {user.status === 'active' ? '活跃' : '禁用'}
                      </span>
                    </td>
                    <td>{user.roles?.join(', ') || '-'}</td>
                    <td>
                      <div className="action-btns">
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => handleToggleStatus(user)}
                        >
                          {user.status === 'active' ? '禁用' : '启用'}
                        </button>
                        <button
                          className="btn btn-sm btn-info"
                          onClick={() => handleResetPassword(user)}
                        >
                          重置密码
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
