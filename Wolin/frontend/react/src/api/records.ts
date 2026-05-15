import api from './client';
import type { InterviewRecord, PaginatedResponse, SingleResponse } from '@/types';

interface SearchParams {
  user_name?: string;
  company_name?: string;
  user_email?: string;
  status?: string;
  created_at_start?: string;
  created_at_end?: string;
  page: number;
  page_size: number;
}

export function fetchRecords(params: SearchParams) {
  return api.get<PaginatedResponse<InterviewRecord>>('/interview/records', { params });
}

export function fetchRecord(id: number) {
  return api.get<SingleResponse<InterviewRecord>>(`/interview/record/${id}`);
}

export function createRecord(data: FormData) {
  return api.post('/interview/record', data);
}

export function updateRecord(id: number, data: FormData) {
  return api.put(`/interview/record/${id}`, data);
}

export function deleteRecord(id: number) {
  return api.delete(`/interview/record/${id}`);
}

export function fetchDownloadUrls(id: number) {
  return api.get<{ status_code: number; data: Record<string, { url: string; label: string }> }>(
    `/interview/record/${id}/download-url`
  );
}
