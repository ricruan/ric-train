import { useEffect, useState, useCallback } from 'react'
import { Table, Button, Space, Tag, Input, Select, Modal, Form, message, Popconfirm, Card, InputNumber } from 'antd'
import { PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { questionApi } from '@/api/question'
import { useAuthStore } from '@/store'
import { SUBJECT_MAP, QUESTION_TYPE_MAP, DIFFICULTY_MAP } from '@/types'
import type { Question } from '@/types'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'

const { TextArea } = Input

export default function QuestionsPage() {
  const [questions, setQuestions] = useState<Question[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null)
  const [form] = Form.useForm()
  const { user } = useAuthStore()

  const [filters, setFilters] = useState({
    keyword: '',
    subject: undefined as string | undefined,
    question_type: undefined as string | undefined,
    page: 1,
    page_size: 10,
  })

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await questionApi.search(filters)
      setQuestions(res.data.list)
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
      await questionApi.delete(id)
      message.success('删除成功')
      fetchData()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '删除失败')
    }
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (editingQuestion) {
        await questionApi.update(editingQuestion.id, values)
        message.success('更新成功')
      } else {
        await questionApi.create({ ...values, created_by: user!.id })
        message.success('创建成功')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingQuestion(null)
      fetchData()
    } catch (error) {
      if (error instanceof Error) message.error(error.message)
    }
  }

  const openEdit = (record: Question) => {
    setEditingQuestion(record)
    form.setFieldsValue(record)
    setModalOpen(true)
  }

  const openCreate = () => {
    setEditingQuestion(null)
    form.resetFields()
    setModalOpen(true)
  }

  const columns: ColumnsType<Question> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '题干', dataIndex: 'question_text', ellipsis: true },
    {
      title: '科目', dataIndex: 'subject', width: 80,
      render: (val: string) => SUBJECT_MAP[val] || val,
    },
    {
      title: '题型', dataIndex: 'question_type', width: 100,
      render: (val: string) => QUESTION_TYPE_MAP[val] || val,
    },
    {
      title: '难度', dataIndex: 'difficulty_level', width: 80,
      render: (val: number) => {
        const colors: Record<number, string> = { 1: 'green', 2: 'lime', 3: 'gold', 4: 'orange', 5: 'red' }
        return <Tag color={colors[val]}>{DIFFICULTY_MAP[val] || val}</Tag>
      },
    },
    {
      title: '操作', width: 150,
      render: (_, record) => (
        <Space>
          <a onClick={() => openEdit(record)}>编辑</a>
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
      title="题目管理"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增题目</Button>}
    >
      {/* 搜索栏 */}
      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="搜索题干"
          prefix={<SearchOutlined />}
          value={filters.keyword}
          onChange={(e) => setFilters((p) => ({ ...p, keyword: e.target.value, page: 1 }))}
          style={{ width: 200 }}
          allowClear
        />
        <Select
          placeholder="科目"
          allowClear
          style={{ width: 120 }}
          value={filters.subject}
          onChange={(val) => setFilters((p) => ({ ...p, subject: val, page: 1 }))}
          options={Object.entries(SUBJECT_MAP).map(([k, v]) => ({ value: k, label: v }))}
        />
        <Select
          placeholder="题型"
          allowClear
          style={{ width: 120 }}
          value={filters.question_type}
          onChange={(val) => setFilters((p) => ({ ...p, question_type: val, page: 1 }))}
          options={Object.entries(QUESTION_TYPE_MAP).map(([k, v]) => ({ value: k, label: v }))}
        />
      </Space>

      {/* 题目列表 */}
      <Table
        columns={columns}
        dataSource={questions}
        rowKey="id"
        loading={loading}
        pagination={{ current: filters.page, pageSize: filters.page_size, total, showSizeChanger: true }}
        onChange={handleTableChange}
      />

      {/* 新增/编辑弹窗 */}
      <Modal
        title={editingQuestion ? '编辑题目' : '新增题目'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => { setModalOpen(false); setEditingQuestion(null) }}
        width={700}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="question_text" label="题干" rules={[{ required: true, message: '请输入题干' }]}>
            <TextArea rows={4} placeholder="请输入题干内容" />
          </Form.Item>
          <Form.Item name="answer" label="标准答案">
            <TextArea rows={2} placeholder="请输入标准答案" />
          </Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item name="subject" label="科目" rules={[{ required: true }]}>
              <Select style={{ width: 140 }} options={Object.entries(SUBJECT_MAP).map(([k, v]) => ({ value: k, label: v }))} />
            </Form.Item>
            <Form.Item name="question_type" label="题型" rules={[{ required: true }]}>
              <Select style={{ width: 140 }} options={Object.entries(QUESTION_TYPE_MAP).map(([k, v]) => ({ value: k, label: v }))} />
            </Form.Item>
            <Form.Item name="grade" label="年级" rules={[{ required: true }]}>
              <InputNumber min={1} max={12} style={{ width: 100 }} />
            </Form.Item>
            <Form.Item name="difficulty_level" label="难度" initialValue={3}>
              <Select style={{ width: 100 }} options={Object.entries(DIFFICULTY_MAP).map(([k, v]) => ({ value: Number(k), label: v }))} />
            </Form.Item>
          </Space>
          <Form.Item name="knowledge_points" label="知识点">
            <Input placeholder="知识点，逗号分隔" />
          </Form.Item>
          <Form.Item name="analysis" label="解析">
            <TextArea rows={2} placeholder="题目解析" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
