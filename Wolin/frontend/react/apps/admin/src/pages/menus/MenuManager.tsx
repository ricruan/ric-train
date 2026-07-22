import { useState, useEffect } from 'react';
import { Tree, Button, Modal, Form, Input, InputNumber, message, Popconfirm, Space } from 'antd';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { getMenus, createMenu, updateMenu, deleteMenu, type Menu } from '../../api/menus';

export default function MenuManager() {
  const [menus, setMenus] = useState<Menu[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingMenu, setEditingMenu] = useState<Menu | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadMenus();
  }, []);

  const loadMenus = async () => {
    setLoading(true);
    try {
      const data = await getMenus('wolin');
      setMenus(data.menus || []);
    } catch (err) {
      message.error('加载菜单失败');
    } finally {
      setLoading(false);
    }
  };

  const convertToTreeData = (menus: Menu[]): any[] => {
    return menus.map((menu) => ({
      key: menu.id,
      title: `${menu.name} (${menu.path})`,
      children: menu.children ? convertToTreeData(menu.children) : [],
    }));
  };

  const handleCreate = () => {
    setEditingMenu(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (menuId: number) => {
    const findMenu = (menus: Menu[]): Menu | null => {
      for (const menu of menus) {
        if (menu.id === menuId) return menu;
        if (menu.children) {
          const found = findMenu(menu.children);
          if (found) return found;
        }
      }
      return null;
    };

    const menu = findMenu(menus);
    if (menu) {
      setEditingMenu(menu);
      form.setFieldsValue(menu);
      setModalVisible(true);
    }
  };

  const handleDelete = async (menuId: number) => {
    try {
      await deleteMenu(menuId);
      message.success('删除成功');
      loadMenus();
    } catch (err) {
      message.error('删除失败');
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingMenu) {
        await updateMenu(editingMenu.id, values);
        message.success('更新成功');
      } else {
        await createMenu({ ...values, source_module: 'wolin' });
        message.success('创建成功');
      }
      setModalVisible(false);
      loadMenus();
    } catch (err) {
      message.error('保存失败');
    }
  };

  const titleRender = (nodeData: any) => {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
        <span>{nodeData.title}</span>
        <Space style={{ marginLeft: 16 }}>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(nodeData.key)} />
          <Popconfirm title="确认删除此菜单?" onConfirm={() => handleDelete(nodeData.key)} okText="是" cancelText="否">
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      </div>
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <h2>菜单管理</h2>
      <Button type="primary" onClick={handleCreate} style={{ marginBottom: 16 }}>创建菜单</Button>

      <Tree
        treeData={convertToTreeData(menus)}
        defaultExpandAll
        titleRender={titleRender}
        style={{ marginBottom: 16 }}
      />

      <Modal
        title={editingMenu ? '编辑菜单' : '创建菜单'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        confirmLoading={loading}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="菜单名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="path" label="路由路径" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="component" label="组件 key" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="icon" label="图标">
            <Input placeholder="如 UserOutlined" />
          </Form.Item>
          <Form.Item name="permission" label="权限标识">
            <Input placeholder="如 user:manage" />
          </Form.Item>
          <Form.Item name="sort_order" label="排序" initialValue={0}>
            <InputNumber />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
