import axios from 'axios';

const api = axios.create({
  baseURL: '',
  timeout: 10 * 60 * 1000, // 10 分钟，大文件上传需要更长时间
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('API error:', err);
    return Promise.reject(err);
  }
);

export default api;
