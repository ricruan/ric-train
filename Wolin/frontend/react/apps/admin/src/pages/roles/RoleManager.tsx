import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Checkbox, message } from 'antd';
import { getRoles, createRole, updateRolePermissions, getPermissions, type Role } from '../../api/roles';

export default function RoleManager() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadRoles();
    loadPermissions();
  }, []);

  const loadRoles = async () => {
    setLoading(true);
    try {
      const data = await getRoles('wolin');
      setRoles(data.roles || []);
    } catch (err) {
      message.error('加载角色列表失败');
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
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (role: Role) => {
    setEditingRole(role);
    form.setFieldsValue(role);
    setModalVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingRole) {
        await updateRolePermissions(editingRole.name, values.permissions, 'wolin');
        message.success('权限更新成功');
      } else {
        await createRole({ ...values, source_module: 'wolin' });
        message.success('角色创建成功');
      }
      setModalVisible(false);
      loadRoles();
    } catch (err) {
      message.error('保存失败');
    }
  };

  const columns = [
    { title: '角色名', dataIndex: 'name', key: 'name' },
    { title: '显示名', dataIndex: 'display_name', key: 'display_name' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    { title: '权限', dataIndex: 'permissions', key: 'permissions', render: (perms: string[]) => perms?.join(', ') },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, role: Role) => (
        <Button size="small" onClick={() => handleEdit(role)}>编辑权限</Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2>角色管理</h2>
      <Button type="primary" onClick={handleCreate} style={{ marginBottom: 16 }}>创建角色</Button>
      <Table columns={columns} dataSource={roles} loading={loading} rowKey="id" />

      <Modal
        title={editingRole ? '编辑权限' : '创建角色'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
      >
        <Form form={form} layout="vertical">
          {!editingRole && (
            <>
              <Form.Item name="name" label="角色标识" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="display_name" label="显示名称" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="description" label="描述">
                <Input.TextArea />
              </Form.Item>
            </>
          )}
          <Form.Item name="permissions" label="权限" rules={[{ required: true }]}>
            <Checkbox.Group>
              {permissions.map((perm) => (
                <Checkbox key={perm} value={perm}>{perm}</Checkbox>
              ))}
            </Checkbox.Group>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
