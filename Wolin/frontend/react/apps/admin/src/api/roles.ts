import { apiClient } from '@interview/shared';

export interface Role {
  id: number;
  name: string;
  display_name: string;
  description?: string;
  permissions: string[];
  source_module: string;
  is_builtin: boolean;
}

export async function getRoles(sourceModule: string) {
  const res = await apiClient.get('/api/auth/roles', { params: { source_module: sourceModule } });
  return res.data.data;
}

export async function createRole(data: { name: string; display_name: string; permissions: string[]; description?: string; source_module: string }) {
  const res = await apiClient.post('/api/auth/roles', data);
  return res.data;
}

export async function updateRolePermissions(roleName: string, permissions: string[], sourceModule: string) {
  const res = await apiClient.put('/api/auth/roles/permissions', { role_name: roleName, permissions, source_module: sourceModule });
  return res.data;
}

export async function getPermissions() {
  const res = await apiClient.get('/api/auth/permissions');
  return res.data.data;
}
