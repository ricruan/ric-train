import { apiClient } from '@interview/shared';

export interface Menu {
  id: number;
  parent_id?: number;
  name: string;
  path: string;
  component: string;
  icon?: string;
  permission?: string;
  sort_order: number;
  is_visible: boolean;
  children: Menu[];
}

export async function getMenus(sourceModule: string) {
  const res = await apiClient.get('/api/auth/menus', { params: { source_module: sourceModule } });
  return res.data.data;
}

export async function createMenu(data: Partial<Menu> & { source_module: string }) {
  const res = await apiClient.post('/api/auth/menus', data);
  return res.data;
}

export async function updateMenu(id: number, data: Partial<Menu>) {
  const res = await apiClient.put(`/api/auth/menus/${id}`, data);
  return res.data;
}

export async function deleteMenu(id: number) {
  const res = await apiClient.delete(`/api/auth/menus/${id}`);
  return res.data;
}
