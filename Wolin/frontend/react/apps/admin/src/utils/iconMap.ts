import * as Icons from '@ant-design/icons';
import type { ComponentType } from 'react';

export const iconMap: Record<string, ComponentType> = {
  'UserOutlined': Icons.UserOutlined,
  'TeamOutlined': Icons.TeamOutlined,
  'TableOutlined': Icons.TableOutlined,
  'MenuOutlined': Icons.MenuOutlined,
  'SettingOutlined': Icons.SettingOutlined,
  'DashboardOutlined': Icons.DashboardOutlined,
  'FileTextOutlined': Icons.FileTextOutlined,
  'CheckSquareOutlined': Icons.CheckSquareOutlined,
  'VideoCameraOutlined': Icons.VideoCameraOutlined,
};

export function getIcon(iconName?: string): ComponentType | null {
  if (!iconName) return null;
  return iconMap[iconName] || null;
}
