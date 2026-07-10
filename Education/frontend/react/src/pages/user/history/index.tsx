import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Table, Tag, Button, Empty, message } from 'antd'
import { useAuthStore } from '@/store'
import { examApi } from '@/api/exam'
import type { ExamRecord } from '@/types'
import type { ColumnsType } from 'antd/es/table'

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  ongoing: { color: 'processing', label: '进行中' },
  submitted: { color: 'warning', label: '已提交' },
  graded: { color: 'success', label: '已判卷' },
}

export default function HistoryPage() {
  const [records, setRecords] = useState<ExamRecord[]>([])
  const [loading, setLoading] = useState(false)
  const { user } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    const fetchHistory = async () => {
      if (!user) return
      setLoading(true)
      try {
        const res = await examApi.getHistory(user.username, 50)
        setRecords(res.data)
      } catch (error) {
        message.error(error instanceof Error ? error.message : '加载历史失败')
      } finally {
        setLoading(false)
      }
    }
    fetchHistory()
  }, [user])

  const columns: ColumnsType<ExamRecord> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '试卷ID', dataIndex: 'paper_id', width: 80 },
    {
      title: '状态', dataIndex: 'status', width: 100,
      render: (val: string) => {
        const s = STATUS_MAP[val] || { color: 'default', label: val }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    {
      title: '得分', dataIndex: 'total_score', width: 80,
      render: (val: number) => val !== null && val !== undefined ? <span className="font-bold text-blue-500">{val}</span> : '-',
    },
    { title: '考试时间', dataIndex: 'start_time', width: 170, render: (val: string) => val?.substring(0, 19) || '-' },
    {
      title: '操作', width: 120,
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => navigate(`/user/exam/result/${record.id}`)}>
          查看详情
        </Button>
      ),
    },
  ]

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">📊 考试历史</h2>

      <Card>
        {records.length === 0 && !loading ? (
          <Empty description="暂无考试记录">
            <Button type="primary" onClick={() => navigate('/user/exam')}>去考试</Button>
          </Empty>
        ) : (
          <Table
            columns={columns}
            dataSource={records}
            rowKey="id"
            loading={loading}
            pagination={false}
          />
        )}
      </Card>
    </div>
  )
}
