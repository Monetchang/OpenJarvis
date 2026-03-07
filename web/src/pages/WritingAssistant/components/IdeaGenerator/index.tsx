import { useState, useEffect } from 'react'
import { Card, Button, Row, Col, Spin, Empty, message, Tooltip } from 'antd'
import { ReloadOutlined, EditOutlined, BulbOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { Idea } from '@/types'
import { useCreationStore } from '@/stores/creationStore'

export default function IdeaGenerator() {
  const [ideas, setIdeas] = useState<Idea[]>([])
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(true)
  const navigate = useNavigate()
  const { setSelectedIdea, expandCreationArea } = useCreationStore()

  useEffect(() => {
    let cancelled = false
    setFetching(true)
    api
      .getIdeas()
      .then((data) => {
        if (!cancelled) setIdeas(data ?? [])
      })
      .catch(() => {
        if (!cancelled) setIdeas([])
      })
      .finally(() => {
        if (!cancelled) setFetching(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleGenerate = async () => {
    setLoading(true)
    try {
      const data = await api.generateIdeas()
      setIdeas(data)
      message.success('选题生成成功')
    } catch (error) {
      message.error('生成选题失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectIdea = (idea: Idea) => {
    setSelectedIdea(idea)
    expandCreationArea()
    message.success(`已选择选题：${idea.title}`)
    // 滚动到创作区
    setTimeout(() => {
      const creationArea = document.getElementById('creation-area')
      if (creationArea) {
        creationArea.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }, 100)
  }

  return (
    <Card
      title={
        <span>
          <BulbOutlined className="mr-2" />
          灵感选题
        </span>
      }
      extra={
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          onClick={handleGenerate}
          loading={loading}
        >
          生成选题
        </Button>
      }
    >
      <Spin spinning={loading || fetching}>
        {ideas.length === 0 && !loading ? (
          <Empty description={fetching ? '加载选题中…' : '暂无当日选题，点击「生成选题」获取写作灵感'}>
            {!fetching && (
              <Button type="primary" onClick={handleGenerate} loading={loading}>
                生成选题
              </Button>
            )}
          </Empty>
        ) : (
          <Row gutter={[16, 16]}>
            {ideas.map((idea) => (
              <Col xs={24} md={12} lg={8} key={idea.id}>
                <Card
                  hoverable
                  className="h-full"
                  actions={[
                    <Tooltip title={idea.reason} key="reason">
                      <Button type="link" icon={<BulbOutlined />}>
                        查看理由
                      </Button>
                    </Tooltip>,
                    <Button
                      type="primary"
                      icon={<EditOutlined />}
                      onClick={() => {
                        handleSelectIdea(idea)
                        navigate('/create/chat', { state: { idea } })
                      }}
                      key="select"
                    >
                      选择创作
                    </Button>,
                  ]}
                >
                  <Card.Meta
                    title={
                      <div className="text-base font-medium line-clamp-2">
                        {idea.title}
                      </div>
                    }
                    description={
                      <div className="mt-3">
                        <div className="text-xs text-gray-500 mb-2">
                          相关文章来源：
                        </div>
                        <div className="space-y-1">
                          {idea.relatedArticles.map((article, index) => (
                            <div
                              key={index}
                              className="text-xs text-gray-600 truncate"
                            >
                              •{' '}
                              <a
                                href={article.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-800 hover:underline"
                              >
                                {article.titleZh && article.title && article.titleZh !== article.title
                                  ? `${article.titleZh}（${article.title}）`
                                  : (article.titleZh ?? article.title)}
                              </a>{' '}
                              ({article.source})
                            </div>
                          ))}
                        </div>
                      </div>
                    }
                  />
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>
    </Card>
  )
}

