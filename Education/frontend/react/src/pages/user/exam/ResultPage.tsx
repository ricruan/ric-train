import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Typography, Spin, Descriptions, Tag, Divider, message } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { examApi } from '@/api/exam'
import type { ExamResultDetail } from '@/types'

const { Title, Text, Paragraph } = Typography

export default function ResultPage() {
  const { examId } = useParams<{ examId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [detail, setDetail] = useState<ExamResultDetail | null>(null)

  useEffect(() => {
    const fetchResult = async () => {
      if (!examId) return
      setLoading(true)
      try {
        const res = await examApi.getResultDetail(Number(examId))
        setDetail(res.data)
      } catch (error) {
        message.error(error instanceof Error ? error.message : '获取结果失败')
      } finally {
        setLoading(false)
      }
    }
    fetchResult()
  }, [examId])

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" tip="加载考试结果..." />
      </div>
    )
  }

  if (!detail) {
    return <div className="text-center py-12">考试结果未找到</div>
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* 成绩总览 */}
      <Card>
        <div className="text-center mb-6">
          <Title level={2}>
            {detail.total_score !== undefined ? (
              <span className="text-blue-500">{detail.total_score}</span>
            ) : '-'}
            <Text type="secondary" className="ml-2">分</Text>
          </Title>
          <Tag color={detail.status === 'graded' ? 'green' : 'orange'}>
            {detail.status === 'graded' ? '已判卷' : '待判卷'}
          </Tag>
        </div>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="试卷">{detail.paper_name}</Descriptions.Item>
          <Descriptions.Item label="考生">{detail.user_id}</Descriptions.Item>
          <Descriptions.Item label="开始时间">{detail.start_time?.substring(0, 19) || '-'}</Descriptions.Item>
          <Descriptions.Item label="交卷时间">{detail.end_time?.substring(0, 19) || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 题目详情 */}
      {detail.questions && detail.questions.length > 0 && (
        <Card title="答题详情">
          <div className="space-y-4">
            {detail.questions.map((q, index) => (
              <div key={q.id} className="border rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <Text strong>{index + 1}. {q.question_text.substring(0, 100)}{q.question_text.length > 100 ? '...' : ''}</Text>
                  <div>
                    {q.score !== undefined && q.max_score !== undefined && (
                      <Tag color={q.score >= q.max_score ? 'green' : q.score > 0 ? 'orange' : 'red'}>
                        {q.score}/{q.max_score}
                      </Tag>
                    )}
                  </div>
                </div>
                <div className="text-sm text-gray-500">
                  <p>你的答案: <Text>{q.user_answer || '未作答'}</Text></p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* AI 总结 */}
      {detail.ai_summary && (
        <Card title="🤖 AI 学习建议">
          <Paragraph className="whitespace-pre-wrap">{detail.ai_summary}</Paragraph>
        </Card>
      )}

      {/* 操作按钮 */}
      <div className="text-center">
        <Space>
          <Button onClick={() => navigate('/user/exam')}>继续考试</Button>
          <Button type="primary" onClick={() => navigate('/user/history')}>查看历史</Button>
        </Space>
      </div>
    </div>
  )
}
