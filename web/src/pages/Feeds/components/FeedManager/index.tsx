import { useEffect, useState } from 'react'
import { Card, Button, Table, Space, Modal, Form, Input, message, Popconfirm, InputNumber, Switch, Tag, Upload } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, InboxOutlined } from '@ant-design/icons'
import { useFeedStore } from '@/stores/feedStore'
import { api } from '@/services/api'
import { RssFeed } from '@/types'

export default function FeedManager() {
  const [form] = Form.useForm()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingFeed, setEditingFeed] = useState<RssFeed | null>(null)
  const [loading, setLoading] = useState(false)
  const [batchModalOpen, setBatchModalOpen] = useState(false)
  const [batchFetchNow, setBatchFetchNow] = useState(false)
  const [batchFileList, setBatchFileList] = useState<{ file: File; parsed?: Array<Omit<RssFeed, 'id' | 'createdAt'>> } | null>(null)
  const [batchLoading, setBatchLoading] = useState(false)
  const [batchResult, setBatchResult] = useState<{ created: number; skipped: number; failed: number } | null>(null)
  const { feeds, setFeeds } = useFeedStore()

  useEffect(() => {
    loadFeeds()
  }, [])

  const loadFeeds = async () => {
    setLoading(true)
    try {
      const data = await api.getFeeds()
      setFeeds(data)
    } catch (error) {
      message.error('加载订阅源失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingFeed(null)
    form.resetFields()
    setModalOpen(true)
  }

  const handleEdit = (feed: RssFeed) => {
    setEditingFeed(feed)
    form.setFieldsValue({ ...feed, fetchNow: false })
    setModalOpen(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await api.deleteFeed(id)
      message.success('删除成功')
      await loadFeeds()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleToggleTrust = async (feed: RssFeed) => {
    try {
      const res = await api.toggleFeedTrust(feed.id)
      message.success(res.isTrusted ? '已设为信任源' : '已取消信任源')
      await loadFeeds()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleBatchImport = () => {
    setBatchModalOpen(true)
    setBatchFileList(null)
    setBatchResult(null)
  }

  const normBatchFile = (e: { fileList: { originFileObj?: File }[] }) => {
    const list = e?.fileList ?? []
    if (list.length === 0) {
      setBatchFileList(null)
      return
    }
    const file = list[0].originFileObj
    if (!file) return
    if (!file.name.endsWith('.json')) {
      message.error('请上传 .json 文件')
      setBatchFileList(null)
      return
    }
    setBatchFileList({ file })
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const raw = reader.result as string
        const arr = JSON.parse(raw)
        if (!Array.isArray(arr)) {
          message.error('JSON 应为数组')
          setBatchFileList(null)
          return
        }
        const parsed: Array<Omit<RssFeed, 'id' | 'createdAt'>> = arr.map((item: unknown): Omit<RssFeed, 'id' | 'createdAt'> => {
          const o = item as Record<string, unknown>
          const pushCount = (typeof o.pushCount === 'number' && o.pushCount >= 1 && o.pushCount <= 50) ? o.pushCount : 10
          return {
            name: String(o.name ?? ''),
            url: String(o.url ?? ''),
            pushCount,
            isTrusted: !!o.isTrusted,
          }
        })
        setBatchFileList((prev) => (prev ? { ...prev, parsed } : null))
      } catch {
        message.error('JSON 解析失败')
        setBatchFileList(null)
      }
    }
    reader.readAsText(file)
  }

  const handleBatchSubmit = async () => {
    if (!batchFileList?.parsed?.length) {
      message.error('请先上传有效的 JSON 文件')
      return
    }
    setBatchLoading(true)
    setBatchResult(null)
    try {
      const res = await api.batchCreateFeeds(batchFileList.parsed, batchFetchNow)
      setBatchResult({
        created: res.created.length,
        skipped: res.skipped.length,
        failed: res.failed.length,
      })
      message.success(`导入完成：成功 ${res.created.length}，跳过 ${res.skipped.length}，失败 ${res.failed.length}`)
      await loadFeeds()
      if (res.created.length > 0 || res.skipped.length > 0) {
        setBatchFileList(null)
      }
    } catch {
      message.error('批量导入失败')
    } finally {
      setBatchLoading(false)
    }
  }

  const handleSubmit = async (values: Omit<RssFeed, 'id' | 'createdAt'> & { fetchNow?: boolean }) => {
    setLoading(true)
    try {
      if (editingFeed) {
        await api.updateFeed(editingFeed.id, values)
        message.success('更新成功')
      } else {
        await api.createFeed(values)
        message.success('添加成功')
      }
      setModalOpen(false)
      form.resetFields()
      await loadFeeds()
    } catch (error) {
      message.error('操作失败')
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '订阅源名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'RSS URL',
      dataIndex: 'url',
      key: 'url',
      ellipsis: true,
      render: (url: string) =>
        url ? (
          <a href={url} target="_blank" rel="noopener noreferrer">
            <Tag color="blue">{url}</Tag>
          </a>
        ) : null,
    },
    {
      title: '推送数量',
      dataIndex: 'pushCount',
      key: 'pushCount',
    },
    {
      title: '信任源',
      dataIndex: 'isTrusted',
      key: 'isTrusted',
      render: (isTrusted: boolean, record: RssFeed) => (
        <Space>
          {isTrusted ? <Tag color="green">信任</Tag> : <Tag>普通</Tag>}
          <Switch
            size="small"
            checked={!!isTrusted}
            onChange={() => handleToggleTrust(record)}
          />
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: RssFeed) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
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
        </Space>
      ),
    },
  ]

  return (
    <Card
      title="订阅源管理"
      extra={
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加订阅源
          </Button>
          <Button icon={<InboxOutlined />} onClick={handleBatchImport}>
            批量导入
          </Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={feeds}
        rowKey="id"
        loading={loading}
        pagination={false}
      />

      <Modal
        title={editingFeed ? '编辑订阅源' : '添加订阅源'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            pushCount: 10,
            isTrusted: false,
            fetchNow: false,
          }}
        >
          <Form.Item
            name="name"
            label="订阅源名称"
            rules={[{ required: true, message: '请输入订阅源名称' }]}
          >
            <Input placeholder="例如：TechCrunch" />
          </Form.Item>
          <Form.Item
            name="url"
            label="RSS URL"
            rules={[
              { required: true, message: '请输入 RSS URL' },
              { type: 'url', message: '请输入有效的 URL' },
            ]}
          >
            <Input placeholder="https://example.com/feed" />
          </Form.Item>
          <Form.Item
            name="pushCount"
            label="推送数量"
            rules={[{ required: true, message: '请输入推送数量' }]}
          >
            <InputNumber min={1} max={50} className="w-full" />
          </Form.Item>
          <Form.Item
            name="isTrusted"
            label="信任源"
            valuePropName="checked"
            extra="信任源文章在两阶段过滤中直接保留，不受分类匹配限制"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            name="fetchNow"
            label="添加后立即拉取"
            valuePropName="checked"
            extra={editingFeed ? '更新后是否立即重新拉取该源文章' : '添加后是否立即拉取文章列表'}
          >
            <Switch />
          </Form.Item>
          <Form.Item>
            <Space className="w-full justify-end">
              <Button onClick={() => setModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={loading}>
                {editingFeed ? '更新' : '添加'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="批量导入"
        open={batchModalOpen}
        onCancel={() => { setBatchModalOpen(false); setBatchFileList(null); setBatchResult(null) }}
        footer={[
          <Button key="cancel" onClick={() => setBatchModalOpen(false)}>关闭</Button>,
          <Button key="submit" type="primary" loading={batchLoading} disabled={!batchFileList?.parsed?.length} onClick={handleBatchSubmit}>
            导入
          </Button>,
        ]}
      >
        <div className="mb-3 text-gray-500 text-sm">
          JSON 格式：<code>[{'{ "name": "...", "url": "...", "pushCount": 10, "isTrusted": false }'}, ...]</code>
        </div>
        <Form layout="vertical">
          <Form.Item label="选择文件">
            <Upload.Dragger
              accept=".json"
              maxCount={1}
              beforeUpload={() => false}
              onChange={(e) => normBatchFile(e)}
              fileList={batchFileList ? [{ uid: '1', name: batchFileList.file.name, status: 'done' }] : []}
            >
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">点击或拖拽 .json 文件到此处</p>
            </Upload.Dragger>
          </Form.Item>
          <Form.Item label="导入后立即拉取">
            <Switch checked={batchFetchNow} onChange={setBatchFetchNow} />
          </Form.Item>
        </Form>
        {batchResult && (
          <div className="mt-2 text-sm">
            成功 {batchResult.created}，跳过 {batchResult.skipped}，失败 {batchResult.failed}
          </div>
        )}
      </Modal>
    </Card>
  )
}
