import { useState, useEffect } from 'react';
import { getRoles, createRole, updateRolePermissions, getPermissions, type Role } from '../../api/roles';
import { Toast } from '@interview/shared';

interface Permission {
  key: string;
  label: string;
  group: string;
}

export default function RoleManager() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    permissions: [] as string[],
  });

  useEffect(() => {
    loadRoles();
    loadPermissions();
  }, [refreshKey]);

  const loadRoles = async () => {
    setLoading(true);
    try {
      const data = await getRoles('wolin');
      setRoles(data.roles || []);
    } catch (err) {
      Toast.error('加载角色列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadPermissions = async () => {
    try {
      const data = await getPermissions();
      setPermissions(data.permissions || []);
    } catch (err) {
      console.error('Failed to load permissions');
    }
  };

  const handleCreate = () => {
    setEditingRole(null);
    setFormData({ name: '', display_name: '', description: '', permissions: [] });
    setModalVisible(true);
  };

  const handleEdit = (role: Role) => {
    setEditingRole(role);
    setFormData({
      name: role.name,
      display_name: role.display_name,
      description: role.description || '',
      permissions: role.permissions || [],
    });
    setModalVisible(true);
  };

  const handleSave = async () => {
    try {
      if (editingRole) {
        await updateRolePermissions(editingRole.name, formData.permissions, 'wolin');
        Toast.success('权限更新成功');
      } else {
        await createRole({ ...formData, source_module: 'wolin' });
        Toast.success('角色创建成功');
      }
      setModalVisible(false);
      setRefreshKey(k => k + 1);
    } catch (err) {
      Toast.error('保存失败');
    }
  };

  const togglePermission = (perm: string) => {
    setFormData(prev => ({
      ...prev,
      permissions: prev.permissions.includes(perm)
        ? prev.permissions.filter(p => p !== perm)
        : [...prev.permissions, perm],
    }));
  };

  return (
    <div className="page manager-page">
      <div className="container">
        <h1 className="title">角色管理</h1>

        <div className="toolbar">
          <span className="record-count">
            共 <strong>{roles.length}</strong> 个角色
          </span>
          <button className="btn btn-success" onClick={handleCreate}>
            + 新增角色
          </button>
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>角色名</th>
                <th>显示名</th>
                <th>描述</th>
                <th>权限</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '40px' }}>
                    加载中...
                  </td>
                </tr>
              ) : roles.length === 0 ? (
                <tr>
                  <td colSpan={5} className="empty-state">
                    暂无角色数据
                  </td>
                </tr>
              ) : (
                roles.map((role) => (
                  <tr key={role.id}>
                    <td style={{ fontWeight: 600 }}>{role.name}</td>
                    <td>{role.display_name}</td>
                    <td>{role.description || '-'}</td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {role.permissions?.map((perm) => (
                          <span
                            key={perm}
                            style={{
                              padding: '2px 8px',
                              background: 'rgba(0, 212, 255, 0.08)',
                              border: '1px solid rgba(0, 212, 255, 0.2)',
                              borderRadius: 'var(--radius-full)',
                              fontSize: '11px',
                              color: 'var(--accent-cyan)',
                            }}
                          >
                            {perm}
                          </span>
                        )) || '-'}
                      </div>
                    </td>
                    <td>
                      <button className="btn btn-sm btn-secondary" onClick={() => handleEdit(role)}>
                        编辑权限
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {modalVisible && (
        <div className="modal-overlay active" onClick={(e) => { if (e.target === e.currentTarget) setModalVisible(false); }}>
          <div className="modal">
            <h2 className="modal-title">{editingRole ? '编辑权限' : '创建角色'}</h2>
            <div className="form-grid">
              {!editingRole && (
                <>
                  <div className="form-group">
                    <label>角色标识</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="如 admin"
                    />
                  </div>
                  <div className="form-group">
                    <label>显示名称</label>
                    <input
                      type="text"
                      value={formData.display_name}
                      onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                      placeholder="如 管理员"
                    />
                  </div>
                  <div className="form-group full-width">
                    <label>描述</label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="角色描述（可选）"
                    />
                  </div>
                </>
              )}
              <div className="form-group full-width">
                <label>权限</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', padding: '12px', background: 'var(--bg-input)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  {permissions.map((perm) => (
                    <label
                      key={perm.key}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 12px',
                        background: formData.permissions.includes(perm.key) ? 'rgba(0, 212, 255, 0.12)' : 'rgba(255, 255, 255, 0.04)',
                        border: `1px solid ${formData.permissions.includes(perm.key) ? 'rgba(0, 212, 255, 0.3)' : 'var(--border-color)'}`,
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer',
                        fontSize: '13px',
                        color: formData.permissions.includes(perm.key) ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                        transition: 'all var(--transition-fast)',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={formData.permissions.includes(perm.key)}
                        onChange={() => togglePermission(perm.key)}
                        style={{ margin: 0 }}
                      />
                      {perm.label}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setModalVisible(false)}>取消</button>
              <button className="btn btn-primary" onClick={handleSave}>保存</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
