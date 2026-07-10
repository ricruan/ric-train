import { create } from 'zustand'
import { authApi } from '@/api/auth'
import { SOURCE_MODULE } from '@/types'
import type { UserInfo } from '@/types'

const TOKEN_KEY = 'edu_access_token'
const REFRESH_KEY = 'edu_refresh_token'

interface AuthState {
  user: UserInfo | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean

  login: (username: string, password: string) => Promise<void>
  logout: () => void
  refreshAccessToken: () => Promise<boolean>
  initAuth: () => Promise<void>
  hasPermission: (permission: string) => boolean
  isAdmin: () => boolean
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: localStorage.getItem(TOKEN_KEY),
  refreshToken: localStorage.getItem(REFRESH_KEY),
  isAuthenticated: !!localStorage.getItem(TOKEN_KEY),
  isLoading: false,

  login: async (username: string, password: string) => {
    set({ isLoading: true })
    try {
      const res = await authApi.login(username, password)
      const data = res.data
      localStorage.setItem(TOKEN_KEY, data.access_token)
      localStorage.setItem(REFRESH_KEY, data.refresh_token)

      // 获取完整用户信息
      const meRes = await authApi.getMe()
      set({
        user: meRes.data,
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        isAuthenticated: true,
        isLoading: false,
      })
    } catch (error) {
      set({ isLoading: false })
      throw error
    }
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    })
  },

  refreshAccessToken: async () => {
    const { refreshToken } = get()
    if (!refreshToken) return false

    try {
      const res = await authApi.refresh(refreshToken)
      const newToken = res.data.access_token
      localStorage.setItem(TOKEN_KEY, newToken)
      set({ accessToken: newToken })
      return true
    } catch {
      get().logout()
      return false
    }
  },

  initAuth: async () => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      set({ isLoading: false })
      return
    }

    set({ isLoading: true })
    try {
      const res = await authApi.getMe()
      set({
        user: res.data,
        accessToken: token,
        refreshToken: localStorage.getItem(REFRESH_KEY),
        isAuthenticated: true,
        isLoading: false,
      })
    } catch {
      get().logout()
    }
  },

  hasPermission: (permission: string) => {
    const { user } = get()
    if (!user) return false
    return user.permissions.includes(permission)
  },

  isAdmin: () => {
    const { user } = get()
    return user?.is_admin ?? false
  },
}))
