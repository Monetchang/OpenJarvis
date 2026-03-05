import { useEffect, useState } from 'react'
import { Card, Tabs, List, Tag, Badge, Collapse, Empty, Spin, message, Button } from 'antd'
import { ClockCircleOutlined, CheckCircleOutlined, EyeOutlined, SyncOutlined } from '@ant-design/icons'
import { api } from '@/services/api'
import { Article } from '@/types'
import { useArticleStore } from '@/stores/articleStore'
import { useFeedStore } from '@/stores/feedStore'
import dayjs from 'dayjs'

/** 安全格式化日期，避免 Invalid Date；支持 ISO 字符串、毫秒时间戳、秒级时间戳 */
function formatDate(value: string | number | null | undefined, format = 'YYYY-MM-DD HH:mm'): string {
  if (value == null || value === '') return '-'
  const ms = typeof value === 'number' ? (value < 1e12 ? value * 1000 : value) : value
  const d = dayjs(ms)
  return d.isValid() ? d.format(format) : '-'
}

export default function PushPreview() {
  const [activeTab, setActiveTab] = useState('today')
  const [todayArticles, setTodayArticles] = useState<Article[]>([])
  const [historyArticles, setHistoryArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(false)
  const [fetchLoading, setFetchLoading] = useState(false)
  const todayRefreshTrigger = useArticleStore((s) => s.todayRefreshTrigger)
  const triggerTodayRefresh = useArticleStore((s) => s.triggerTodayRefresh)
  const { feeds, setFeeds } = useFeedStore()

  useEffect(() => {
    loadTodayArticles()
  }, [])

  useEffect(() => {
    if (feeds.length === 0) {
      api.getFeeds().then(setFeeds).catch(() => {})
    }
  }, [])

  useEffect(() => {
    if (todayRefreshTrigger > 0) {
      loadTodayArticles()
    }
  }, [todayRefreshTrigger])

  const loadTodayArticles = async () => {
    setLoading(true)
    try {
      const data = await api.getTodayArticles()
      setTodayArticles(data)
      if (data.length === 0) {
        message.info('当日暂无文章，请点击右上角「抓取」按钮获取最新内容')
      }
    } catch (error) {
      message.error('加载推送失败')
    } finally {
      setLoading(false)
    }
  }

  const loadHistoryArticles = async () => {
    setLoading(true)
    try {
      const data = await api.getHistoryArticles()
      setHistoryArticles(data.articles)
    } catch (error) {
      message.error('加载历史数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handleTabChange = (key: string) => {
    setActiveTab(key)
    if (key === 'history' && historyArticles.length === 0) {
      loadHistoryArticles()
    }
  }

  const handleFetch = async () => {
    if (feeds.length === 0) {
      message.info('暂无订阅源，请先在订阅源管理中添加')
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

  const handleMarkAsRead = async (id: number) => {
    try {
      await api.markArticleAsRead(id)
      setTodayArticles((prev) =>
        prev.map((article) =>
          article.id === id ? { ...article, isRead: true } : article
        )
      )
      message.success('已标记为已读')
    } catch (error) {
      message.error('操作失败')
    }
  }

  const renderArticleList = (articles: Article[], showMarkRead = false) => {
    if (articles.length === 0) {
      return <Empty description="暂无推送文章" />
    }

    return (
      <List
        dataSource={articles}
        renderItem={(article) => (
          <List.Item
            className={article.isRead ? 'opacity-60' : ''}
            actions={
              showMarkRead && !article.isRead
                ? [
                    <Button
                      type="link"
                      icon={<CheckCircleOutlined />}
                      onClick={() => handleMarkAsRead(article.id)}
                      key="read"
                    >
                      标记已读
                    </Button>,
                  ]
                : []
            }
          >
            <List.Item.Meta
              title={
                <div className="flex items-center space-x-2">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    {article.title}
                  </a>
                  {article.isRead && (
                    <Tag icon={<CheckCircleOutlined />} color="success">
                      已读
                    </Tag>
                  )}
                </div>
              }
              description={
                <div className="space-y-2">
                  <div className="flex items-center space-x-4 text-sm text-gray-500">
                    <span>
                      <Tag color="blue">{article.feedName}</Tag>
                    </span>
                    <span title="发布时间">
                      <ClockCircleOutlined className="mr-1" />
                      {formatDate(article.publishedAt)}
                    </span>
                    {(() => {
                      const pushedStr = formatDate(article.pushedAt)
                      if (pushedStr === '-') return null
                      return (
                        <span title="推送时间">
                          推送 {pushedStr}
                        </span>
                      )
                    })()}
                  </div>
                  <Collapse
                    ghost
                    items={[
                      {
                        key: '1',
                        label: (
                          <span className="text-blue-600">
                            <EyeOutlined className="mr-1" />
                            查看摘要
                          </span>
                        ),
                        children: <p className="text-gray-600">{article.summary}</p>,
                      },
                    ]}
                  />
                </div>
              }
            />
          </List.Item>
        )}
      />
    )
  }

  const items = [
    {
      key: 'today',
      label: (
        <span>
          今日推送
          <Badge
            count={todayArticles.filter((a) => !a.isRead).length}
            className="ml-2"
          />
        </span>
      ),
      children: (
        <Spin spinning={loading}>
          {renderArticleList(todayArticles, true)}
        </Spin>
      ),
    },
    {
      key: 'history',
      label: '历史存档',
      children: (
        <Spin spinning={loading}>
          {renderArticleList(historyArticles)}
        </Spin>
      ),
    },
  ]

  return (
    <Card
      title="推送预览"
      extra={
        <Button
          icon={<SyncOutlined spin={fetchLoading} />}
          onClick={handleFetch}
          loading={fetchLoading}
          disabled={fetchLoading || feeds.length === 0}
        >
          手动抓取
        </Button>
      }
    >
      <Tabs items={items} activeKey={activeTab} onChange={handleTabChange} />
    </Card>
  )
}

