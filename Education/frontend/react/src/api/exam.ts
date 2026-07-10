import client from './client'
import type { ApiResponse, ExamStartResult, ExamResultSummary, ExamResultDetail, ExamRecord } from '@/types'

export const examApi = {
  /** 开始考试 */
  start(paperId: number, userId: string) {
    return client.post<ApiResponse<ExamStartResult>>('/education/exam/start', null, {
      params: { paper_id: paperId, user_id: userId },
    })
  },

  /** 提交试卷 */
  submit(examId: number, answers: Record<string, string>) {
    return client.post<ApiResponse<ExamResultSummary>>(`/education/exam/${examId}/submit`, answers)
  },

  /** 获取考试结果（简要） */
  getResult(examId?: number, examUuid?: string) {
    return client.get<ApiResponse<ExamResultSummary>>('/education/exam/result', {
      params: { exam_id: examId, exam_uuid: examUuid },
    })
  },

  /** 获取考试结果详情 */
  getResultDetail(examId?: number, examUuid?: string) {
    return client.get<ApiResponse<ExamResultDetail>>('/education/exam/result/detail', {
      params: { exam_id: examId, exam_uuid: examUuid },
    })
  },

  /** 获取考试历史 */
  getHistory(userId: string, limit: number = 10) {
    return client.get<ApiResponse<ExamRecord[]>>('/education/exam/history', {
      params: { user_id: userId, limit },
    })
  },

  /** 手动判卷 */
  grade(examId: number) {
    return client.post<ApiResponse<ExamResultSummary>>(`/education/exam/${examId}/grade`)
  },
}
