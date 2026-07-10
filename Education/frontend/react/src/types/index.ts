// =========================
// API 通用响应
// =========================

export interface ApiResponse<T = unknown> {
  status_code: number
  data: T
  msg: string
}

// =========================
// 认证相关
// =========================

export interface UserInfo {
  id: number
  username: string
  email?: string
  phone?: string
  source_module: string
  status: string
  roles: Array<{ id: number; name: string; display_name: string }>
  role_names: string[]
  permissions: string[]
  is_admin: boolean
  is_super_admin: boolean
  last_login_at?: string
  created_at?: string
}

export interface LoginResponse {
  id: number
  username: string
  source_module: string
  access_token: string
  refresh_token: string
  roles: string[]
  permissions: string[]
  is_admin: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RefreshResponse {
  access_token: string
}

// =========================
// 题目相关
// =========================

export type Subject = 'chinese' | 'math' | 'english' | 'physics' | 'chemistry' | 'biology' | 'history' | 'geography' | 'politics'

export type QuestionType = 'single_choice' | 'multiple_choice' | 'fill_blank' | 'short_answer' | 'essay' | 'judgement'

export interface Question {
  id: number
  question_uuid: string
  question_text: string
  question_html?: string
  question_markdown?: string
  answer?: string | Record<string, unknown> | unknown[]
  analysis?: string
  hint?: string
  knowledge_points?: string
  grade: number
  subject: string
  question_type: string
  difficulty_level?: number
  difficulty_label?: string
  images?: string
  created_at?: string
  created_by?: number
  status?: number
}

export interface QuestionSearchResult {
  list: Question[]
  total: number
  page: number
  page_size: number
}

export interface QuestionSearchParams {
  keyword?: string
  subject?: string
  question_type?: string
  grade?: number
  difficulty_level?: number
  page?: number
  page_size?: number
}

// =========================
// 试卷相关
// =========================

export interface Paper {
  id: number
  paper_uuid: string
  paper_name: string
  description?: string
  subject?: string
  question_ids: string
  scores?: string
  default_score_type: string
  duration_minutes: number
  status: 'draft' | 'published' | 'archived'
  is_public: number
  created_by: number
  created_at?: string
  parent_id?: number
}

export interface PaperDetail extends Paper {
  questions: Question[]
  total_score: number
  score_list: number[]
}

export interface PaperListResult {
  list: Paper[]
  total: number
  page: number
  page_size: number
}

export interface PaperListParams {
  page?: number
  page_size?: number
  subject?: string
  status?: string
}

// =========================
// 考试相关
// =========================

export interface ExamRecord {
  id: number
  exam_uuid: string
  paper_id: number
  user_id: string
  start_time?: string
  end_time?: string
  user_ip?: string
  answers?: Record<string, string>
  total_score?: number
  score_details?: Record<string, unknown>
  ai_summary?: string
  ai_scoring_basis?: string
  teacher_review?: string
  status: 'ongoing' | 'submitted' | 'graded'
  created_at?: string
}

export interface ExamStartResult {
  exam_id: number
  exam_uuid: string
  paper_id: number
  questions: Question[]
  duration_minutes: number
  total_score: number
}

export interface ExamResultSummary {
  exam_id: number
  exam_uuid: string
  paper_id: number
  paper_name: string
  user_id: string
  total_score: number
  status: string
  start_time?: string
  end_time?: string
}

export interface ExamResultDetail extends ExamResultSummary {
  questions: Array<Question & { user_answer?: string; score?: number; max_score?: number }>
  ai_summary?: string
}

// =========================
// 用户管理 (Admin)
// =========================

export interface AdminUserInfo {
  id: number
  username: string
  email?: string
  phone?: string
  source_module: string
  status: string
  roles?: Array<{ id: number; name: string; display_name: string }>
  permissions?: string[]
  last_login_at?: string
  created_at?: string
}

export interface UserListResult {
  users: AdminUserInfo[]
  total: number
  limit: number
  offset: number
}

export interface RoleInfo {
  id: number
  name: string
  display_name: string
  description?: string
  permissions: string[]
  is_builtin: boolean
}

export interface PermissionOption {
  key: string
  label: string
  group: string
}

// =========================
// 常量
// =========================

export const SUBJECT_MAP: Record<string, string> = {
  chinese: '语文',
  math: '数学',
  english: '英语',
  physics: '物理',
  chemistry: '化学',
  biology: '生物',
  history: '历史',
  geography: '地理',
  politics: '政治',
}

export const QUESTION_TYPE_MAP: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  fill_blank: '填空题',
  short_answer: '简答题',
  essay: '论述题',
  judgement: '判断题',
}

export const DIFFICULTY_MAP: Record<number, string> = {
  1: '简单',
  2: '较易',
  3: '中等',
  4: '较难',
  5: '困难',
}

export const SOURCE_MODULE = 'education'
