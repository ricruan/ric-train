import { useState, useEffect } from 'react';
import { getMenus, createMenu, updateMenu, deleteMenu, type Menu } from '../../api/menus';
import { Toast } from '@interview/shared';

export default function MenuManager() {
  const [menus, setMenus] = useState<Menu[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingMenu, setEditingMenu] = useState<Menu | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    path: '',
    component: '',
    icon: '',
    permission: '',
    sort_order: 0,
  });

  useEffect(() => {
    loadMenus();
  }, [refreshKey]);

  const loadMenus = async () => {
    setLoading(true);
    try {
      const data = await getMenus('wolin');
      setMenus(data.menus || []);
    } catch (err) {
      Toast.error('加载菜单失败');
    } finally {
      setLoading(false);
    }
  };

  const findMenu = (menus: Menu[], id: number): Menu | null => {
    for (const menu of menus) {
      if (menu.id === id) return menu;
      if (menu.children) {
        const found = findMenu(menu.children, id);
        if (found) return found;
      }
    }
    return null;
  };

  const handleCreate = () => {
    setEditingMenu(null);
    setFormData({ name: '', path: '', component: '', icon: '', permission: '', sort_order: 0 });
    setModalVisible(true);
  };

  const handleEdit = (menuId: number) => {
    const menu = findMenu(menus, menuId);
    if (menu) {
      setEditingMenu(menu);
      setFormData({
        name: menu.name,
        path: menu.path,
        component: menu.component,
        icon: menu.icon || '',
        permission: menu.permission || '',
        sort_order: menu.sort_order,
      });
      setModalVisible(true);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteMenu(deleteTarget);
      Toast.success('删除成功');
      setRefreshKey(k => k + 1);
    } catch (err) {
      Toast.error('删除失败');
    } finally {
      setDeleteTarget(null);
    }
  };

  const handleSave = async () => {
    try {
      if (editingMenu) {
        await updateMenu(editingMenu.id, formData);
        Toast.success('更新成功');
      } else {
        await createMenu({ ...formData, source_module: 'wolin' });
        Toast.success('创建成功');
      }
      setModalVisible(false);
      setRefreshKey(k => k + 1);
    } catch (err) {
      Toast.error('保存失败');
    }
  };

  const renderMenuTree = (menuList: Menu[], level = 0) => {
    return menuList.map((menu) => (
      <div key={menu.id}>
        <div
          className="menu-tree-item"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 16px',
            paddingLeft: `${16 + level * 24}px`,
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '8px',
            transition: 'all var(--transition-fast)',
          }}
        >
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontWeight: 600, fontSize: '14px' }}>{menu.name}</span>
              <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>{menu.path}</span>
            </div>
            <div style={{ display: 'flex', gap: '12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
              <span>组件: {menu.component}</span>
              {menu.permission && <span>权限: {menu.permission}</span>}
              {menu.icon && <span>图标: {menu.icon}</span>}
            </div>
          </div>
          <div className="action-btns">
            <button className="btn btn-sm btn-secondary" onClick={() => handleEdit(menu.id)}>
              编辑
            </button>
            <button className="btn btn-sm btn-danger" onClick={() => setDeleteTarget(menu.id)}>
              删除
            </button>
          </div>
        </div>
        {menu.children && menu.children.length > 0 && renderMenuTree(menu.children, level + 1)}
      </div>
    ));
  };

  const countMenus = (menuList: Menu[]): number => {
    let count = menuList.length;
    for (const menu of menuList) {
      if (menu.children) {
        count += countMenus(menu.children);
      }
    }
    return count;
  };

  return (
    <div className="page manager-page">
      <div className="container">
        <h1 className="title">菜单管理</h1>

        <div className="toolbar">
          <span className="record-count">
            共 <strong>{countMenus(menus)}</strong> 个菜单
          </span>
          <button className="btn btn-success" onClick={handleCreate}>
            + 新增菜单
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'auto' }}>
          {loading ? (
            <div className="empty-state">加载中...</div>
          ) : menus.length === 0 ? (
            <div className="empty-state">暂无菜单数据</div>
          ) : (
            renderMenuTree(menus)
          )}
        </div>
      </div>

      {modalVisible && (
        <div className="modal-overlay active" onClick={(e) => { if (e.target === e.currentTarget) setModalVisible(false); }}>
          <div className="modal" style={{ maxWidth: 600 }}>
            <h2 className="modal-title">{editingMenu ? '编辑菜单' : '创建菜单'}</h2>
            <div className="form-grid">
              <div className="form-group">
                <label>菜单名称</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="如 用户管理"
                />
              </div>
              <div className="form-group">
                <label>路由路径</label>
                <input
                  type="text"
                  value={formData.path}
                  onChange={(e) => setFormData({ ...formData, path: e.target.value })}
                  placeholder="如 /users"
                />
              </div>
              <div className="form-group full-width">
                <label>组件 key</label>
                <input
                  type="text"
                  value={formData.component}
                  onChange={(e) => setFormData({ ...formData, component: e.target.value })}
                  placeholder="如 pages/users/UserManager"
                />
              </div>
              <div className="form-group">
                <label>图标</label>
                <input
                  type="text"
                  value={formData.icon}
                  onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                  placeholder="如 UserOutlined"
                />
              </div>
              <div className="form-group">
                <label>权限标识</label>
                <input
                  type="text"
                  value={formData.permission}
                  onChange={(e) => setFormData({ ...formData, permission: e.target.value })}
                  placeholder="如 user:manage"
                />
              </div>
              <div className="form-group">
                <label>排序</label>
                <input
                  type="number"
                  value={formData.sort_order}
                  onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setModalVisible(false)}>取消</button>
              <button className="btn btn-primary" onClick={handleSave}>保存</button>
            </div>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="modal-overlay active" onClick={(e) => { if (e.target === e.currentTarget) setDeleteTarget(null); }}>
          <div className="modal" style={{ maxWidth: 400 }}>
            <h2 className="modal-title">确认删除</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 24, textAlign: 'center' }}>
              确定要删除此菜单吗？此操作将同时删除所有子菜单。
            </p>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setDeleteTarget(null)}>取消</button>
              <button className="btn btn-danger" onClick={handleDelete}>确认删除</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
