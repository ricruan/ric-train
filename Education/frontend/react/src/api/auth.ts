import client from './client'
import type { ApiResponse, LoginResponse, RefreshResponse, UserInfo, UserListResult, RoleInfo, PermissionOption } from '@/types'

export const authApi = {
  /** 登录 */
  login(username: string, password: string) {
    return client.post<ApiResponse<LoginResponse>>('/api/auth/login', { username, password })
  },

  /** 刷新 Token */
  refresh(refreshToken: string) {
    return client.post<ApiResponse<RefreshResponse>>('/api/auth/refresh', { refresh_token: refreshToken })
  },

  /** 获取当前用户信息 */
  getMe() {
    return client.get<ApiResponse<UserInfo>>('/api/auth/me')
  },

  /** 修改密码 */
  changePassword(oldPassword: string, newPassword: string) {
    return client.post<ApiResponse<null>>('/api/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
  },

  /** 获取用户列表 (管理员) */
  listUsers(params?: { source_module?: string; status?: string; keyword?: string; limit?: number; offset?: number }) {
    return client.get<ApiResponse<UserListResult>>('/api/auth/users', { params })
  },

  /** 更新用户状态 */
  updateStatus(userId: number, status: string) {
    return client.put<ApiResponse<null>>('/api/auth/users/status', { user_id: userId, status })
  },

  /** 重置密码 */
  resetPassword(userId: number, newPassword: string = '123456') {
    return client.post<ApiResponse<null>>('/api/auth/users/reset-password', { user_id: userId, new_password: newPassword })
  },

  /** 获取角色列表 */
  listRoles(sourceModule: string = 'education') {
    return client.get<ApiResponse<{ roles: RoleInfo[] }>>('/api/auth/roles', { params: { source_module: sourceModule } })
  },

  /** 创建角色 */
  createRole(data: { name: string; display_name: string; permissions: string[]; description?: string; source_module?: string }) {
    return client.post<ApiResponse<null>>('/api/auth/roles', data)
  },

  /** 更新角色权限 */
  updateRolePermissions(roleName: string, permissions: string[], sourceModule: string = 'education') {
    return client.put<ApiResponse<null>>('/api/auth/roles/permissions', {
      role_name: roleName,
      permissions,
      source_module: sourceModule,
    })
  },

  /** 获取可用权限列表 */
  listPermissions() {
    return client.get<ApiResponse<{ permissions: PermissionOption[] }>>('/api/auth/permissions')
  },

  /** 授予用户角色 */
  grantRole(targetUserId: number, roleName: string, sourceModule?: string) {
    return client.post<ApiResponse<null>>('/api/auth/roles/grant', {
      target_user_id: targetUserId,
      role_name: roleName,
      source_module: sourceModule,
    })
  },

  /** 撤销用户角色 */
  revokeRole(targetUserId: number, roleName: string, sourceModule?: string) {
    return client.post<ApiResponse<null>>('/api/auth/roles/revoke', {
      target_user_id: targetUserId,
      role_name: roleName,
      source_module: sourceModule,
    })
  },

  /** 设置用户角色（替换全部） */
  setUserRoles(targetUserId: number, roleNames: string[], sourceModule?: string) {
    return client.post<ApiResponse<null>>('/api/auth/roles/set', {
      target_user_id: targetUserId,
      role_names: roleNames,
      source_module: sourceModule,
    })
  },

  /** 获取用户角色信息 */
  getUserRoles(userId: number) {
    return client.get<ApiResponse<{ user_id: number; username: string; roles: RoleInfo[]; permissions: string[] }>>(`/api/auth/users/${userId}/roles`)
  },
}
