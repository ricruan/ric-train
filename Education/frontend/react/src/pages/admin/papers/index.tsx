import { useEffect, useState, useCallback } from 'react'
import { Table, Button, Space, Tag, Modal, Form, Input, InputNumber, Select, message, Popconfirm, Card } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { paperApi } from '@/api/paper'
import { useAuthStore } from '@/store'
import { SUBJECT_MAP } from '@/types'
import type { Paper } from '@/types'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  published: { color: 'green', label: '已发布' },
  archived: { color: 'red', label: '已归档' },
}

export default function PapersPage() {
  const [papers, setPapers] = useState<Paper[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingPaper, setEditingPaper] = useState<Paper | null>(null)
  const [form] = Form.useForm()
  const { user } = useAuthStore()

  const [filters, setFilters] = useState({
    page: 1,
    page_size: 10,
    subject: undefined as string | undefined,
    status: undefined as string | undefined,
  })

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await paperApi.list(filters)
      setPapers(res.data.list)
      setTotal(res.data.total)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { fetchData() }, [fetchData])

  const handleDelete = async (id: number) => {
    try {
      await paperApi.delete(id)
      message.success('删除成功')
      fetchData()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '删除失败')
    }
  }

  const handlePublish = async (id: number) => {
    try {
      await paperApi.publish(id)
      message.success('发布成功')
      fetchData()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '发布失败')
    }
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (editingPaper) {
        await paperApi.update(editingPaper.id, values)
        message.success('更新成功')
      } else {
        await paperApi.create({ ...values, created_by: user!.id })
        message.success('创建成功')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingPaper(null)
      fetchData()
    } catch (error) {
      if (error instanceof Error) message.error(error.message)
    }
  }

  const openEdit = (record: Paper) => {
    setEditingPaper(record)
    form.setFieldsValue(record)
    setModalOpen(true)
  }

  const openCreate = () => {
    setEditingPaper(null)
    form.resetFields()
    form.setFieldsValue({ duration_minutes: 30 })
    setModalOpen(true)
  }

  const columns: ColumnsType<Paper> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '试卷名称', dataIndex: 'paper_name', ellipsis: true },
    { title: '科目', dataIndex: 'subject', width: 80, render: (val: string) => SUBJECT_MAP[val] || val || '-' },
    { title: '题目数', dataIndex: 'question_ids', width: 80, render: (val: string) => val ? val.split(',').length : 0 },
    {
      title: '状态', dataIndex: 'status', width: 100,
      render: (val: string) => {
        const s = STATUS_MAP[val] || { color: 'default', label: val }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    { title: '时长(分)', dataIndex: 'duration_minutes', width: 80 },
    { title: '创建时间', dataIndex: 'created_at', width: 170, render: (val: string) => val ? val.substring(0, 19) : '-' },
    {
      title: '操作', width: 200,
      render: (_, record) => (
        <Space>
          <a onClick={() => openEdit(record)}>编辑</a>
          {record.status === 'draft' && <a onClick={() => handlePublish(record.id)}>发布</a>}
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: 'red' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const handleTableChange = (pagination: TablePaginationConfig) => {
    setFilters((prev) => ({ ...prev, page: pagination.current || 1, page_size: pagination.pageSize || 10 }))
  }

  return (
    <Card
      title="试卷管理"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增试卷</Button>}
    >
      <Space style={{ marginBottom: 16 }}>
        <Select placeholder="科目" allowClear style={{ width: 120 }} value={filters.subject}
          onChange={(val) => setFilters((p) => ({ ...p, subject: val, page: 1 }))}
          options={Object.entries(SUBJECT_MAP).map(([k, v]) => ({ value: k, label: v }))}
        />
        <Select placeholder="状态" allowClear style={{ width: 120 }} value={filters.status}
          onChange={(val) => setFilters((p) => ({ ...p, status: val, page: 1 }))}
          options={Object.entries(STATUS_MAP).map(([k, v]) => ({ value: k, label: v.label }))}
        />
      </Space>

      <Table
        columns={columns}
        dataSource={papers}
        rowKey="id"
        loading={loading}
        pagination={{ current: filters.page, pageSize: filters.page_size, total }}
        onChange={handleTableChange}
      />

      <Modal
        title={editingPaper ? '编辑试卷' : '新增试卷'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => { setModalOpen(false); setEditingPaper(null) }}
        width={600}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="paper_name" label="试卷名称" rules={[{ required: true }]}>
            <Input placeholder="请输入试卷名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="试卷描述" />
          </Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item name="subject" label="科目">
              <Select style={{ width: 140 }} allowClear options={Object.entries(SUBJECT_MAP).map(([k, v]) => ({ value: k, label: v }))} />
            </Form.Item>
            <Form.Item name="duration_minutes" label="考试时长(分钟)">
              <InputNumber min={1} max={180} style={{ width: 120 }} />
            </Form.Item>
          </Space>
          <Form.Item name="question_ids" label="题目ID列表" rules={[{ required: true, message: '请输入题目ID，逗号分隔' }]}
            extra="多个题目ID用逗号分隔，例如: 1,2,3,4,5">
            <Input placeholder="1,2,3,4,5" />
          </Form.Item>
          <Form.Item name="scores" label="每题分值" extra="逗号分隔，留空则每题1分。例如: 2,3,2,5,3">
            <Input placeholder="2,3,2,5,3" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
