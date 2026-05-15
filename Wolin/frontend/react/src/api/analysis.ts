import api from './client';

export async function submitAnalysis(formData: FormData) {
  return api.post('/interview/interview_analysis', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}
