import axios from 'axios'

const client = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器: 自动附加 Authorization header
client.interceptors.request.use(
  (config) => {
    // 延迟导入避免循环依赖
    const { useAuthStore } = require('@/store/authStore')
    const token = useAuthStore.getState().accessToken
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器: 统一处理响应
client.interceptors.response.use(
  (response) => {
    const data = response.data
    // 后端统一响应格式: { status_code, data, msg }
    if (data && typeof data === 'object' && 'status_code' in data) {
      if (data.status_code === 200) {
        return data
      }
      // 业务错误
      return Promise.reject(new Error(data.msg || '请求失败'))
    }
    return data
  },
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const { useAuthStore } = require('@/store/authStore')
      const success = await useAuthStore.getState().refreshAccessToken()

      if (success) {
        const token = useAuthStore.getState().accessToken
        originalRequest.headers.Authorization = `Bearer ${token}`
        return client(originalRequest)
      }

      useAuthStore.getState().logout()
      window.location.href = '/login'
    }

    // HTTP 错误但非 401
    if (error.response) {
      const msg = error.response.data?.msg || `请求失败 (${error.response.status})`
      return Promise.reject(new Error(msg))
    }

    return Promise.reject(error)
  }
)

export default client
