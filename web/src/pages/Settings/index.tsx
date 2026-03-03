import { useState, useEffect } from 'react'
import { Tabs, Card, Button, Table, Space, Modal, Form, Input, Switch, message, Popconfirm, Select, InputNumber } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { api } from '@/services/api'
import { ArticleDomain, ArticleKeyword, GlobalConfig } from '@/types'

export default function Settings() {
  const tabItems = [
    {
      key: 'global',
      label: '全局配置',
      children: <GlobalConfigManager />,
    },
    {
      key: 'domains',
      label: '关键领域管理',
      children: <DomainManager />,
    },
    {
      key: 'keywords',
      label: '关键词规则管理',
      children: <KeywordManager />,
    },
  ]

  return (
    <Card title="设置">
      <Tabs defaultActiveKey="global" items={tabItems} />
    </Card>
  )
}

function GlobalConfigManager() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [, setConfig] = useState<GlobalConfig | null>(null)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const data = await api.getGlobalConfig()
      setConfig(data)
      form.setFieldsValue(data)
    } catch (error) {
      message.error('加载配置失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (values: GlobalConfig) => {
    setLoading(true)
    try {
      const updated = await api.updateGlobalConfig(values)
      setConfig(updated)
      message.success('更新成功')
    } catch (error: any) {
      message.error(error?.response?.data?.message || '更新失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
      style={{ maxWidth: 600 }}
    >
      <Form.Item
        name="rssSchedule"
        label="RSS 定时规则"
        rules={[{ required: true, message: '请输入定时规则' }]}
        extra="cron 表达式，例如：0 9 * * * 表示每天上午 9:00"
      >
        <Input placeholder="0 9 * * *" />
      </Form.Item>
      <Form.Item
        name="translationEnabled"
        label="AI 翻译"
        valuePropName="checked"
        extra="是否启用 AI 翻译功能"
      >
        <Switch />
      </Form.Item>
      <Form.Item>
        <Button type="primary" htmlType="submit" loading={loading}>
          保存配置
        </Button>
      </Form.Item>
    </Form>
  )
}

function DomainManager() {
  const [form] = Form.useForm()
  const [domains, setDomains] = useState<ArticleDomain[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingDomain, setEditingDomain] = useState<ArticleDomain | null>(null)

  useEffect(() => {
    loadDomains()
  }, [])

  const loadDomains = async () => {
    setLoading(true)
    try {
      const data = await api.getDomains()
      setDomains(data)
    } catch (error) {
      message.error('加载领域列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingDomain(null)
    form.resetFields()
    form.setFieldsValue({ enabled: true })
    setModalOpen(true)
  }

  const handleEdit = (domain: ArticleDomain) => {
    setEditingDomain(domain)
    form.setFieldsValue(domain)
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.deleteDomain(id)
      message.success('删除成功')
      loadDomains()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleToggleEnabled = async (domain: ArticleDomain) => {
    try {
      await api.updateDomain(domain.id, { enabled: !domain.enabled })
      message.success('更新成功')
      loadDomains()
    } catch (error) {
      message.error('更新失败')
    }
  }

  const handleSubmit = async (values: {
    name: string
    description?: string
    enabled?: boolean
  }) => {
    setLoading(true)
    try {
      if (editingDomain) {
        await api.updateDomain(editingDomain.id, values)
        message.success('更新成功')
      } else {
        await api.createDomain(values)
        message.success('添加成功')
      }
      setModalOpen(false)
      form.resetFields()
      loadDomains()
    } catch (error: any) {
      message.error(error?.response?.data?.message || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '领域名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean, record: ArticleDomain) => (
        <Switch checked={enabled} onChange={() => handleToggleEnabled(record)} />
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: ArticleDomain) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除？删除后该领域下的所有关键词也会被删除"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <>
      <div className="mb-4">
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加领域
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={domains}
        rowKey="id"
        loading={loading}
        pagination={false}
      />

      <Modal
        title={editingDomain ? '编辑领域' : '添加领域'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="name"
            label="领域名称"
            rules={[{ required: true, message: '请输入领域名称' }]}
          >
            <Input placeholder="例如：AI模型架构与算法创新" />
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea rows={3} placeholder="领域描述（可选）" />
          </Form.Item>
          <Form.Item
            name="enabled"
            label="启用状态"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item>
            <Space className="w-full justify-end">
              <Button onClick={() => setModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={loading}>
                {editingDomain ? '更新' : '添加'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

function KeywordManager() {
  const [form] = Form.useForm()
  const [domains, setDomains] = useState<ArticleDomain[]>([])
  const [keywords, setKeywords] = useState<ArticleKeyword[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedDomainId, setSelectedDomainId] = useState<number | undefined>()
  const [, setEditingKeyword] = useState<ArticleKeyword | null>(null)

  useEffect(() => {
    loadDomains()
  }, [])

  useEffect(() => {
    if (selectedDomainId) {
      loadKeywords()
    } else {
      setKeywords([])
    }
  }, [selectedDomainId])

  const loadDomains = async () => {
    try {
      const data = await api.getDomains()
      setDomains(data)
    } catch (error) {
      message.error('加载领域列表失败')
    }
  }

  const loadKeywords = async () => {
    if (!selectedDomainId) return
    setLoading(true)
    try {
      const data = await api.getKeywords(selectedDomainId)
      setKeywords(data || [])
    } catch (error: any) {
      message.error(error?.message || '加载关键词列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    if (!selectedDomainId) {
      message.warning('请先选择领域')
      return
    }
    setEditingKeyword(null)
    form.resetFields()
    form.setFieldsValue({
      domain_id: selectedDomainId,
      keyword_type: 'positive',
      is_regex: false,
      is_required: false,
      priority: 0,
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.deleteKeyword(id)
      message.success('删除成功')
      loadKeywords()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values: {
    domain_id: number
    keyword_type: 'positive' | 'negative'
    keyword_text: string
    is_regex?: boolean
    is_required?: boolean
    alias?: string
    priority?: number
    max_results?: number
  }) => {
    setLoading(true)
    try {
      await api.createKeyword(values)
      message.success('添加成功')
      setModalOpen(false)
      form.resetFields()
      loadKeywords()
    } catch (error: any) {
      message.error(error?.response?.data?.message || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  const positiveKeywords = keywords.filter(k => k.keyword_type === 'positive')
  const negativeKeywords = keywords.filter(k => k.keyword_type === 'negative')

  const keywordColumns = [
    {
      title: '关键词',
      dataIndex: 'keyword_text',
      key: 'keyword_text',
    },
    {
      title: '类型',
      key: 'type',
      render: (_: unknown, record: ArticleKeyword) => (
        <Space>
          {record.is_regex && <span className="text-blue-500">正则</span>}
          {record.is_required && <span className="text-green-500">必须</span>}
          {record.keyword_type === 'negative' && <span className="text-red-500">过滤</span>}
        </Space>
      ),
    },
    {
      title: '别名',
      dataIndex: 'alias',
      key: 'alias',
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
    },
    {
      title: '限制数量',
      dataIndex: 'max_results',
      key: 'max_results',
      render: (val: number | null) => val ?? '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: ArticleKeyword) => (
        <Popconfirm
          title="确认删除？"
          onConfirm={() => handleDelete(record.id)}
          okText="确认"
          cancelText="取消"
        >
          <Button type="link" danger icon={<DeleteOutlined />}>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <>
      <div className="mb-4">
        <Space>
          <span>选择领域：</span>
          <Select
            style={{ width: 300 }}
            placeholder="请选择领域"
            value={selectedDomainId}
            onChange={setSelectedDomainId}
            options={domains.map(d => ({ label: d.name, value: d.id }))}
          />
        </Space>
      </div>

      {selectedDomainId && (
        <>
          <div className="mb-4">
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
              添加关键词
            </Button>
          </div>

          <Tabs
            items={[
              {
                key: 'positive',
                label: `正向关键词 (${positiveKeywords.length})`,
                children: (
                  <Table
                    columns={keywordColumns}
                    dataSource={positiveKeywords}
                    rowKey="id"
                    loading={loading}
                    pagination={false}
                  />
                ),
              },
              {
                key: 'negative',
                label: `负向关键词 (${negativeKeywords.length})`,
                children: (
                  <Table
                    columns={keywordColumns}
                    dataSource={negativeKeywords}
                    rowKey="id"
                    loading={loading}
                    pagination={false}
                  />
                ),
              },
            ]}
          />
        </>
      )}

      <Modal
        title="添加关键词"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="domain_id"
            label="所属领域"
            hidden
          >
            <InputNumber />
          </Form.Item>
          <Form.Item
            name="keyword_type"
            label="关键词类型"
            rules={[{ required: true }]}
          >
            <Select>
              <Select.Option value="positive">正向关键词</Select.Option>
              <Select.Option value="negative">负向关键词（过滤词）</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="keyword_text"
            label="关键词文本"
            rules={[{ required: true, message: '请输入关键词' }]}
            extra="正则表达式需用 /.../ 包裹，如：/AI|人工智能|机器学习/"
          >
            <Input placeholder="例如：AI 或 /AI|人工智能/" />
          </Form.Item>
          <Form.Item
            name="is_regex"
            label="是否为正则表达式"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            name="is_required"
            label="是否为必须词"
            valuePropName="checked"
            extra="必须词：所有必须词都要匹配才算匹配"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            name="alias"
            label="别名"
          >
            <Input placeholder="可选，用于标识该关键词" />
          </Form.Item>
          <Form.Item
            name="priority"
            label="优先级"
          >
            <InputNumber min={0} defaultValue={0} />
          </Form.Item>
          <Form.Item
            name="max_results"
            label="限制数量"
            extra="限制该关键词组最多显示多少条，留空表示不限制"
          >
            <InputNumber min={1} placeholder="留空不限制" />
          </Form.Item>
          <Form.Item>
            <Space className="w-full justify-end">
              <Button onClick={() => setModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={loading}>
                添加
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

