import { useState } from 'react'
import { Card, Input, Button, Table, Tag, Space, message, Descriptions } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { examApi } from '@/api/exam'
import type { ExamRecord } from '@/types'
import type { ColumnsType } from 'antd/es/table'

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  ongoing: { color: 'processing', label: '进行中' },
  submitted: { color: 'warning', label: '已提交' },
  graded: { color: 'success', label: '已判卷' },
}

export default function ExamsPage() {
  const [userId, setUserId] = useState('')
  const [records, setRecords] = useState<ExamRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedExam, setSelectedExam] = useState<ExamRecord | null>(null)

  const handleSearch = async () => {
    if (!userId.trim()) return
    setLoading(true)
    try {
      const res = await examApi.getHistory(userId.trim(), 50)
      setRecords(res.data)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '查询失败')
    } finally {
      setLoading(false)
    }
  }

  const handleViewDetail = async (examId: number) => {
    try {
      const res = await examApi.getResultDetail(examId)
      setSelectedExam(res.data as unknown as ExamRecord)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '获取详情失败')
    }
  }

  const columns: ColumnsType<ExamRecord> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '考生', dataIndex: 'user_id', width: 100 },
    { title: '试卷ID', dataIndex: 'paper_id', width: 80 },
    {
      title: '状态', dataIndex: 'status', width: 100,
      render: (val: string) => {
        const s = STATUS_MAP[val] || { color: 'default', label: val }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    { title: '总分', dataIndex: 'total_score', width: 80, render: (val: number) => val ?? '-' },
    { title: '开始时间', dataIndex: 'start_time', width: 170, render: (val: string) => val?.substring(0, 19) || '-' },
    { title: '交卷时间', dataIndex: 'end_time', width: 170, render: (val: string) => val?.substring(0, 19) || '-' },
    {
      title: '操作', width: 100,
      render: (_, record) => (
        <a onClick={() => handleViewDetail(record.id)}>查看详情</a>
      ),
    },
  ]

  return (
    <div>
      <Card title="考试数据管理">
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="输入考生 user_id"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 250 }}
            prefix={<SearchOutlined />}
          />
          <Button type="primary" onClick={handleSearch} loading={loading}>查询</Button>
        </Space>

        <Table
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* 详情弹窗 */}
      {selectedExam && (
        <Card title="考试详情" style={{ marginTop: 16 }}>
          <Descriptions bordered column={2}>
            <Descriptions.Item label="考试ID">{selectedExam.id}</Descriptions.Item>
            <Descriptions.Item label="考生">{selectedExam.user_id}</Descriptions.Item>
            <Descriptions.Item label="试卷ID">{selectedExam.paper_id}</Descriptions.Item>
            <Descriptions.Item label="状态">{STATUS_MAP[selectedExam.status]?.label || selectedExam.status}</Descriptions.Item>
            <Descriptions.Item label="总分">{selectedExam.total_score ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="AI总结" span={2}>
              {selectedExam.ai_summary || '暂无'}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  )
}
