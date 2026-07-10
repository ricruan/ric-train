import client from './client'
import type { ApiResponse, Question, QuestionSearchResult, QuestionSearchParams } from '@/types'

export const questionApi = {
  /** 获取科目列表 */
  getSubjects() {
    return client.get<ApiResponse<string[]>>('/education/question/subjects')
  },

  /** 随机获取题目 */
  getRandom(params?: { subject?: string; question_type?: string; difficulty_level?: number; grade?: number; num?: number }) {
    return client.get<ApiResponse<Question | Question[]>>('/education/question/random_one', { params })
  },

  /** 搜索题目 */
  search(params: QuestionSearchParams) {
    return client.get<ApiResponse<QuestionSearchResult>>('/education/question/search', { params })
  },

  /** 获取单个题目 */
  getById(id: number) {
    return client.get<ApiResponse<Question>>(`/education/question/${id}`)
  },

  /** 创建题目 */
  create(data: Partial<Question> & { created_by: number }) {
    return client.post<ApiResponse<Question>>('/education/question', data)
  },

  /** 更新题目 */
  update(id: number, data: Partial<Question>) {
    return client.put<ApiResponse<Question>>(`/education/question/${id}`, data)
  },

  /** 删除题目 */
  delete(id: number) {
    return client.delete<ApiResponse<null>>(`/education/question/${id}`)
  },

  /** AI 判题 */
  aiJudge(params: { user_id?: string; question_id: string; answer: string }) {
    return client.post<ApiResponse<unknown>>('/education/question/ai_judge', params)
  },

  /** 固定逻辑判题 */
  judge(params: { question_id: string; answer: string }) {
    return client.post<ApiResponse<unknown>>('/education/question/judge', params)
  },

  /** 文本导入题目 */
  importText(data: { text: string; subject: string; grade_range?: string; difficulty?: number; created_by?: number }) {
    return client.post<ApiResponse<unknown>>('/education/question/import/text', data)
  },

  /** 文件导入题目 */
  importFile(file: File, subject: string) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('subject', subject)
    return client.post<ApiResponse<unknown>>('/education/question/import/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
