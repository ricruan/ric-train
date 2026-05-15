import api from './client';
import type { InterviewQuestion } from '@/types';

export function getInterviewQuestions(uuid: string) {
  return api.get<{ data: InterviewQuestion[] }>(
    `/interview/interview/questions/${uuid}`
  );
}

export async function submitAnswer(formData: FormData) {
  return api.post('/interview/interview/audio_answer', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export async function audioToText(formData: FormData) {
  return api.post('/interview/audio_to_text', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}
