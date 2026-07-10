import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, List, Tag, Button, Empty, Spin, message } from 'antd'
import { ClockCircleOutlined } from '@ant-design/icons'
import { paperApi } from '@/api/paper'
import { SUBJECT_MAP } from '@/types'
import type { Paper } from '@/types'

export default function UserExamPage() {
  const [papers, setPapers] = useState<Paper[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const fetchPapers = async () => {
      setLoading(true)
      try {
        const res = await paperApi.list({ status: 'published', page_size: 50 })
        setPapers(res.data.list)
      } catch (error) {
        message.error(error instanceof Error ? error.message : '加载试卷列表失败')
      } finally {
        setLoading(false)
      }
    }
    fetchPapers()
  }, [])

  const handleStartExam = (paper: Paper) => {
    navigate(`/user/exam/${paper.id}`)
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">📝 在线考试</h2>

      <Spin spinning={loading}>
        {papers.length === 0 && !loading ? (
          <Empty description="暂无可用试卷" />
        ) : (
          <List
            grid={{ gutter: 16, xs: 1, sm: 1, md: 2, lg: 2, xl: 3 }}
            dataSource={papers}
            renderItem={(paper) => (
              <List.Item>
                <Card
                  hoverable
                  className="cursor-pointer"
                  onClick={() => handleStartExam(paper)}
                  actions={[
                    <Button type="primary" key="start" onClick={(e) => { e.stopPropagation(); handleStartExam(paper) }}>
                      开始考试
                    </Button>,
                  ]}
                >
                  <Card.Meta
                    title={<span className="text-lg">{paper.paper_name}</span>}
                    description={
                      <div className="space-y-2 mt-2">
                        <p className="text-gray-500 text-sm">{paper.description || '暂无描述'}</p>
                        <div className="flex items-center gap-2 flex-wrap">
                          {paper.subject && (
                            <Tag color="blue">{SUBJECT_MAP[paper.subject] || paper.subject}</Tag>
                          )}
                          <Tag><ClockCircleOutlined /> {paper.duration_minutes} 分钟</Tag>
                          <Tag color="orange">
                            {paper.question_ids ? paper.question_ids.split(',').length : 0} 题
                          </Tag>
                        </div>
                      </div>
                    }
                  />
                </Card>
              </List.Item>
            )}
          />
        )}
      </Spin>
    </div>
  )
}
