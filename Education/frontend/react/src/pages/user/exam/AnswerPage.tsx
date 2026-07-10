import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Radio, Input, Space, Modal, Typography, Spin, message, Progress, Tag } from 'antd'
import { ClockCircleOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { paperApi } from '@/api/paper'
import { examApi } from '@/api/exam'
import { useAuthStore } from '@/store'
import { QUESTION_TYPE_MAP } from '@/types'
import type { Question } from '@/types'

const { Title, Text } = Typography
const { TextArea } = Input

export default function AnswerPage() {
  const { paperId } = useParams<{ paperId: string }>()
  const navigate = useNavigate()
  const { user } = useAuthStore()

  const [loading, setLoading] = useState(true)
  const [questions, setQuestions] = useState<Question[]>([])
  const [durationMinutes, setDurationMinutes] = useState(30)
  const [totalScore, setTotalScore] = useState(0)
  const [examId, setExamId] = useState<number | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [currentTime, setCurrentTime] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 加载试卷并开始考试
  useEffect(() => {
    const startExam = async () => {
      if (!paperId || !user) return
      setLoading(true)
      try {
        // 获取试卷详情
        const paperRes = await paperApi.getById(Number(paperId))
        const detail = paperRes.data
        setQuestions(detail.questions || [])
        setDurationMinutes(detail.duration_minutes || 30)
        setTotalScore(detail.total_score || 0)

        // 开始考试
        const examRes = await examApi.start(Number(paperId), user.username)
        setExamId(examRes.data.exam_id)

        // 开始倒计时
        setCurrentTime(0)
        timerRef.current = setInterval(() => {
          setCurrentTime((prev) => {
            const next = prev + 1
            // 超时自动交卷
            if (next >= (detail.duration_minutes || 30) * 60) {
              handleAutoSubmit(next, examRes.data.exam_id)
            }
            return next
          })
        }, 1000)
      } catch (error) {
        message.error(error instanceof Error ? error.message : '开始考试失败')
        navigate('/user/exam')
      } finally {
        setLoading(false)
      }
    }
    startExam()

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [paperId, user])

  const handleAutoSubmit = async (_timeSpent: number, currentExamId: number) => {
    if (timerRef.current) clearInterval(timerRef.current)
    try {
      await examApi.submit(currentExamId, answers)
      message.warning('考试时间到，已自动交卷')
      navigate(`/user/exam/result/${currentExamId}`)
    } catch {
      message.error('自动交卷失败')
    }
  }

  const handleSubmit = () => {
    Modal.confirm({
      title: '确认交卷',
      content: `你已回答 ${Object.keys(answers).length}/${questions.length} 题，确定交卷吗？`,
      okText: '确认交卷',
      cancelText: '继续答题',
      onOk: async () => {
        if (!examId) return
        setSubmitting(true)
        if (timerRef.current) clearInterval(timerRef.current)
        try {
          await examApi.submit(examId, answers)
          message.success('交卷成功')
          navigate(`/user/exam/result/${examId}`)
        } catch (error) {
          message.error(error instanceof Error ? error.message : '交卷失败')
        } finally {
          setSubmitting(false)
        }
      },
    })
  }

  const updateAnswer = (questionId: string | number, answer: string) => {
    setAnswers((prev) => ({ ...prev, [String(questionId)]: answer }))
  }

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }

  const remainingTime = durationMinutes * 60 - currentTime
  const progress = (currentTime / (durationMinutes * 60)) * 100
  const isTimeWarning = remainingTime < 300 // 最后5分钟

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" tip="正在加载试卷..." />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* 顶部信息栏 */}
      <Card className="mb-6 sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Title level={4} style={{ margin: 0 }}>答题中</Title>
            <Text type="secondary">共 {questions.length} 题 | 总分 {totalScore}</Text>
          </div>
          <div className="flex items-center gap-4">
            <div className={`text-lg font-mono font-bold ${isTimeWarning ? 'text-red-500' : 'text-gray-700'}`}>
              <ClockCircleOutlined /> {formatTime(remainingTime)}
            </div>
            <Button type="primary" onClick={handleSubmit} loading={submitting}>
              交卷
            </Button>
          </div>
        </div>
        <Progress
          percent={progress}
          size="small"
          status={isTimeWarning ? 'exception' : 'active'}
          showInfo={false}
          className="mt-2"
        />
      </Card>

      {/* 题目列表 */}
      <div className="space-y-6">
        {questions.map((question, index) => (
          <Card key={question.id} title={
            <span>
              <span className="text-blue-500 mr-2">{index + 1}.</span>
              <Tag>{QUESTION_TYPE_MAP[question.question_type] || question.question_type}</Tag>
            </span>
          }>
            <div className="mb-4 whitespace-pre-wrap text-gray-700">
              {question.question_text}
            </div>

            {/* 根据题型渲染不同输入 */}
            {(question.question_type === 'single_choice' || question.question_type === 'judgement') && (
              <Radio.Group
                value={answers[String(question.id)]}
                onChange={(e) => updateAnswer(question.id, e.target.value)}
              >
                <Space direction="vertical" className="w-full">
                  {/* 尝试解析 answer 字段作为选项 */}
                  {(() => {
                    try {
                      const answerObj = typeof question.answer === 'string' ? JSON.parse(question.answer) : question.answer
                      if (Array.isArray(answerObj)) {
                        return answerObj.map((opt: string | { label: string; value: string }, i: number) => {
                          const label = typeof opt === 'string' ? opt : opt.label
                          const value = typeof opt === 'string' ? opt : opt.value
                          return <Radio key={i} value={value}>{label}</Radio>
                        })
                      }
                    } catch { /* 非JSON */ }
                    // 如果没有选项数据，提供 A/B/C/D
                    return ['A', 'B', 'C', 'D'].map((opt) => (
                      <Radio key={opt} value={opt}>{opt}</Radio>
                    ))
                  })()}
                </Space>
              </Radio.Group>
            )}

            {question.question_type === 'multiple_choice' && (
              <div>
                <Text type="secondary" className="mb-2 block">多选题，用逗号分隔选项（如 A,B,C）</Text>
                <Input
                  value={answers[String(question.id)] || ''}
                  onChange={(e) => updateAnswer(question.id, e.target.value)}
                  placeholder="输入答案，如 A,B,C"
                />
              </div>
            )}

            {(question.question_type === 'fill_blank' || question.question_type === 'short_answer' || question.question_type === 'essay') && (
              <TextArea
                value={answers[String(question.id)] || ''}
                onChange={(e) => updateAnswer(question.id, e.target.value)}
                rows={question.question_type === 'essay' ? 6 : 3}
                placeholder="请输入你的答案"
              />
            )}
          </Card>
        ))}
      </div>

      {/* 底部交卷按钮 */}
      <div className="text-center py-8">
        <Button type="primary" size="large" onClick={handleSubmit} loading={submitting}>
          <CheckCircleOutlined /> 交卷
        </Button>
      </div>
    </div>
  )
}
