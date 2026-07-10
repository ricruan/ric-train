import axios, { AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { useAuthStore } from '@/store/authStore'

/**
 * Custom client interface where the interceptor has already unwrapped
 * the HTTP response, so get<T>() returns Promise<T> (the response body).
 *
 * At runtime the interceptor returns response.data (the ApiResponse<T> object),
 * so client.get<ApiResponse<SomeType>>().data gives SomeType.
 */
interface ApiClient extends AxiosInstance {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
}

const axiosInstance = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
axiosInstance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// 响应拦截器 — 返回 response.data，即后端的 { status_code, data, msg }
axiosInstance.interceptors.response.use(
  (response: AxiosResponse) => {
    const data = response.data
    if (data && typeof data === 'object' && 'status_code' in data) {
      if (data.status_code === 200) {
        return data
      }
      return Promise.reject(new Error(data.msg || '请求失败'))
    }
    return data
  },
  async (error: AxiosError) => {
    const originalRequest = (error.config as any) || {}

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const success = await useAuthStore.getState().refreshAccessToken()

      if (success) {
        const token = useAuthStore.getState().accessToken
        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers.Authorization = `Bearer ${token}`
        return axiosInstance(originalRequest)
      }

      useAuthStore.getState().logout()
      window.location.href = '/login'
    }

    if (error.response) {
      const msg = (error.response.data as any)?.msg || `请求失败 (${error.response.status})`
      return Promise.reject(new Error(msg))
    }

    return Promise.reject(error)
  }
)

const client = axiosInstance as ApiClient

export default client
