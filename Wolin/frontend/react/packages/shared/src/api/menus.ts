import { apiClient } from './client.js';

export interface MenuItem {
  id: number;
  parent_id: number | null;
  name: string;
  path: string;
  component: string;
  icon?: string;
  permission?: string;
  sort_order: number;
  is_visible: boolean;
  children: MenuItem[];
}

export async function fetchUserMenus(): Promise<MenuItem[]> {
  const res = await apiClient.get('/api/auth/me/menus');
  return res.data.data.menus;
}
