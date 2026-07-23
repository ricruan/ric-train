import api from './client';
import { frontendLogger } from '@interview/shared';

export async function submitAnalysis(
  formData: FormData,
  onProgress?: (progress: number) => void
) {
  frontendLogger.debug(`submitAnalysis 开始请求，formData 字段: ${[...formData.keys()].join(', ')}`);
  return api.post('/interview/interview_analysis', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 10 * 60 * 1000, // 10 分钟超时
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  }).then(res => {
    frontendLogger.info(`submitAnalysis 请求成功，状态码: ${res.status}`);
    return res;
  }).catch(err => {
    frontendLogger.error(`submitAnalysis 请求失败: ${err.code || err.message}`, err);
    throw err;
  });
}
