import axios, { type AxiosError, type AxiosInstance } from 'axios';
import { getToken, clearToken } from '../auth/token.js';

export function createApiClient(onUnauthorized: () => void): AxiosInstance {
  const client = axios.create({
    baseURL: '',
    timeout: 10 * 60 * 1000,
    headers: { 'Content-Type': 'application/json' },
  });

  client.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (res) => res,
    (error: AxiosError) => {
      if (error.response?.status === 401) {
        clearToken();
        onUnauthorized();
      }
      return Promise.reject(error);
    },
  );

  return client;
}

/** Shared apiClient singleton with auth interceptors (no redirect on 401). */
export const apiClient = createApiClient(() => {});
