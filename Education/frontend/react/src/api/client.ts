import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

const client = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
client.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
client.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data && typeof data === 'object' && 'status_code' in data) {
      if (data.status_code === 200) {
        return data
      }
      return Promise.reject(new Error(data.msg || '请求失败'))
    }
    return data
  },
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const success = await useAuthStore.getState().refreshAccessToken()

      if (success) {
        const token = useAuthStore.getState().accessToken
        originalRequest.headers.Authorization = `Bearer ${token}`
        return client(originalRequest)
      }

      useAuthStore.getState().logout()
      window.location.href = '/login'
    }

    if (error.response) {
      const msg = error.response.data?.msg || `请求失败 (${error.response.status})`
      return Promise.reject(new Error(msg))
    }

    return Promise.reject(error)
  }
)

export default client
