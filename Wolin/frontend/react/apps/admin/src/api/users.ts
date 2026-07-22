import { apiClient } from '@interview/shared';

export interface User {
  id: number;
  username: string;
  email?: string;
  phone?: string;
  source_module: string;
  status: string;
  roles: string[];
  created_at: string;
}

export async function getUsers(params?: { keyword?: string; limit?: number; offset?: number }) {
  const res = await apiClient.get('/api/auth/users', { params });
  return res.data.data;
}

export async function updateUserStatus(userId: number, status: string) {
  const res = await apiClient.put('/api/auth/users/status', { user_id: userId, status });
  return res.data;
}

export async function resetUserPassword(userId: number, newPassword: string) {
  const res = await apiClient.post('/api/auth/users/reset-password', { user_id: userId, new_password: newPassword });
  return res.data;
}

export async function setUserRoles(userId: number, roleNames: string[], sourceModule: string) {
  const res = await apiClient.post('/api/auth/roles/set', { target_user_id: userId, role_names: roleNames, source_module: sourceModule });
  return res.data;
}
