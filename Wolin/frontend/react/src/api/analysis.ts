import api from './client';

export async function submitAnalysis(
  formData: FormData,
  onProgress?: (progress: number) => void
) {
  return api.post('/interview/interview_analysis', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });
}
