import client from './client'
import type { ApiResponse, Paper, PaperDetail, PaperListResult, PaperListParams } from '@/types'

export const paperApi = {
  /** 获取试卷列表 */
  list(params?: PaperListParams) {
    return client.get<ApiResponse<PaperListResult>>('/education/paper/list', { params })
  },

  /** 获取试卷详情（含题目） */
  getById(paperId: number) {
    return client.get<ApiResponse<PaperDetail>>(`/education/paper/${paperId}`)
  },

  /** 创建试卷 */
  create(data: { paper_name: string; question_ids: string; scores?: string; description?: string; subject?: string; duration_minutes?: number; created_by?: number }) {
    const formData = new FormData()
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        formData.append(key, String(value))
      }
    })
    return client.post<ApiResponse<{ paper_id: number; paper_uuid: string; paper_name: string; total_score: number }>>('/education/paper', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /** 获取试卷版本历史 */
  getVersions(paperId: number) {
    return client.get<ApiResponse<Paper[]>>(`/education/paper/${paperId}/versions`)
  },

  /** 发布试卷 */
  publish(paperId: number) {
    return client.put<ApiResponse<{ message: string }>>(`/education/paper/${paperId}/publish`)
  },

  /** 更新试卷 */
  update(paperId: number, data: { paper_name: string; question_ids: string; scores?: string; description?: string; subject?: string; duration_minutes?: number }) {
    const formData = new FormData()
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        formData.append(key, String(value))
      }
    })
    return client.put<ApiResponse<{ paper_id: number; paper_uuid: string; paper_name: string; total_score: number }>>(`/education/paper/${paperId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /** 删除试卷 */
  delete(paperId: number) {
    return client.delete<ApiResponse<{ message: string }>>(`/education/paper/${paperId}`)
  },

  /** 恢复试卷版本 */
  restore(paperId: number) {
    return client.post<ApiResponse<{ paper_id: number; paper_uuid: string; paper_name: string; total_score: number }>>(`/education/paper/${paperId}/restore`)
  },
}
