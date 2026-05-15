export interface InterviewRecord {
  id: number;
  record_uuid: string;
  user_name: string;
  user_email: string;
  company_name: string;
  status: 'processing' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
  audio_duration?: number;
  error_msg?: string;
  audio_text?: string;
  analysis_start?: string;
  resume_analysis?: string;
  interview_evaluation?: string;
  self_evaluation?: string;
  analysis_end?: string;
  qa_pairs?: Record<string, unknown>;
  resume_info?: Record<string, unknown>;
  interview_json?: Record<string, unknown>;
  qa_analysis?: Record<string, unknown>;
}

export interface InterviewQuestion {
  question: string;
  audio_url: string;
}

export interface PaginatedResponse<T> {
  status_code: number;
  data: {
    items: T[];
    total: number;
    page: number;
    page_size: number;
  };
  msg?: string;
}

export interface SingleResponse<T> {
  status_code: number;
  data: T;
  msg?: string;
}

export interface DownloadFileItem {
  url: string;
  label: string;
  file_type: string;
}
