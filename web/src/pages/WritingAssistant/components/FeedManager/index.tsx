import { useEffect, useState } from 'react'
import { Card, Button, Table, Space, Modal, Form, Input, message, Popconfirm, InputNumber, Switch, Tag } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, SyncOutlined } from '@ant-design/icons'
import { useFeedStore } from '@/stores/feedStore'
import { useArticleStore } from '@/stores/articleStore'
import { api } from '@/services/api'
import { RssFeed } from '@/types'

export default function FeedManager() {
  const [form] = Form.useForm()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingFeed, setEditingFeed] = useState<RssFeed | null>(null)
  const [loading, setLoading] = useState(false)
  const [fetchLoading, setFetchLoading] = useState(false)
  const { feeds, setFeeds } = useFeedStore()
  const triggerTodayRefresh = useArticleStore((s) => s.triggerTodayRefresh)

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
    form.setFieldsValue(feed)
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

  const handleFetch = async () => {
    if (feeds.length === 0) {
      message.info('暂无订阅源，请先添加')
      return
    }
    setFetchLoading(true)
    try {
      await api.fetchFeeds()
      message.success('抓取完成')
      triggerTodayRefresh()
    } catch (error) {
      message.error('抓取失败')
    } finally {
      setFetchLoading(false)
    }
  }

  const handleSubmit = async (values: Omit<RssFeed, 'id' | 'createdAt'>) => {
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
          <Button
            icon={<SyncOutlined spin={fetchLoading} />}
            onClick={handleFetch}
            loading={fetchLoading}
            disabled={fetchLoading || feeds.length === 0}
          >
            手动抓取
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加订阅源
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
    </Card>
  )
}

