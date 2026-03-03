import request from './request'
import {
  RssFeed,
  Article,
  Idea,
  CreationParams,
  GeneratedArticle,
  ArticleDomain,
  ArticleKeyword,
  GlobalConfig,
} from '@/types'

// API 方法
export const api = {
  // 用户注册：绑定邮箱并订阅每日推送（邀请码由后端校验）
  async register(email: string, inviteCode: string): Promise<{ success: boolean }> {
    const response = await request.post('/subscribe/email', { email, inviteCode })
    return response.data ?? { success: true }
  },

  async logout(): Promise<void> {
    try {
      await request.post('/user/unbind')
    } catch {
      // 无登录态或后端未实现时忽略
    }
  },

  async getCurrentUser(): Promise<{ email: string | null; isEmailBound: boolean }> {
    const response = await request.get('/user/me')
    return response.data
  },

  // RSS 订阅源
  async getFeeds(): Promise<RssFeed[]> {
    const response = await request.get('/feed/list')
    return response.data.feeds
  },

  async createFeed(feed: Omit<RssFeed, 'id' | 'createdAt'>): Promise<RssFeed> {
    const response = await request.post('/feed/create', feed, {
      timeout: 480000, // 添加时会拉取文章，耗时较长，8 分钟
    })
    return response.data
  },

  async updateFeed(id: string, feed: Partial<RssFeed>): Promise<RssFeed> {
    const response = await request.put(`/feed/update/${id}`, feed, {
      timeout: 480000, // 更新可能触发重新拉取，8 分钟
    })
    return response.data
  },

  async deleteFeed(id: string): Promise<{ success: boolean }> {
    const response = await request.delete(`/feed/delete/${id}`)
    return response.data
  },

  async toggleFeedTrust(feedId: string): Promise<{ id: string; isTrusted: boolean }> {
    const response = await request.put(`/feed/trust/${feedId}`)
    return response.data
  },

  async fetchFeeds(): Promise<void> {
    await request.post('/feed/fetch', undefined, {
      timeout: 360000, // 抓取所有源可能较久，6 分钟
    })
  },

  // 文章推送（服务端可能触发 fetch，8 分钟内使用缓存）
  async getTodayArticles(): Promise<Article[]> {
    const CACHE_KEY = 'api_today_articles'
    const EXPIRE_MS = 8 * 60 * 1000
    const cached = sessionStorage.getItem(CACHE_KEY)
    if (cached) {
      try {
        const { data, ts } = JSON.parse(cached)
        if (Date.now() - ts < EXPIRE_MS) return data
      } catch {
        // ignore
      }
    }
    const response = await request.get('/article/today')
    const articles = response.data.articles ?? []
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify({ data: articles, ts: Date.now() }))
    } catch {
      // ignore
    }
    return articles
  },

  async getHistoryArticles(params?: {
    date?: string
    page?: number
    pageSize?: number
  }): Promise<{
    articles: Article[]
    total: number
    page: number
    pageSize: number
  }> {
    const response = await request.get('/article/history', { params })
    return response.data
  },

  async markArticleAsRead(id: number): Promise<{ success: boolean }> {
    const response = await request.post(`/article/mark-read/${id}`)
    return response.data
  },

  // 灵感选题
  async getIdeas(): Promise<Idea[]> {
    const response = await request.get<{ data?: { ideas?: Idea[] }; ideas?: Idea[] }>('/ai/ideas')
    const data = response?.data ?? response
    return data?.ideas ?? (Array.isArray(response) ? response : [])
  },

  // 生成选题（AI 接口较慢，单独延长超时时间）
  async generateIdeas(params?: {
    articleIds?: number[]
    count?: number
  }): Promise<Idea[]> {
    const response = await request.post('/ai/generate-ideas', params, {
      timeout: 120000, // 2 分钟
    })
    return response.data.ideas
  },

  // 文章创作（AI 接口较慢，单独延长超时时间）
  async generateArticle(params: CreationParams): Promise<GeneratedArticle> {
    const response = await request.post(
      '/ai/generate-article',
      {
        ideaId: params.ideaId,
        ideaTitle: params.ideaTitle,
        style: params.style,
        audience: params.audience,
        length: 'medium',
        language: 'zh-CN',
      },
      { timeout: 120000 } // 2 分钟
    )
    return {
      title: response.data.title,
      content: response.data.content,
      generatedAt: response.data.generatedAt,
    }
  },

  // 文章过滤 - 关键领域
  async getDomains(enabled?: boolean): Promise<ArticleDomain[]> {
    const params = enabled !== undefined ? { enabled } : {}
    const response = await request.get('/filter/domains', { params })
    // 拦截器已处理：如果直接返回数组则直接返回，如果是包装格式则返回整个 response.data
    if (Array.isArray(response)) {
      return response
    }
    // 处理包装格式 { code: 0, message: "success", data: [...] }
    if (response && response.data && Array.isArray(response.data)) {
      return response.data
    }
    return []
  },

  async createDomain(data: {
    name: string
    description?: string
    enabled?: boolean
  }): Promise<ArticleDomain> {
    const response = await request.post('/filter/domains', data)
    return response.data
  },

  async updateDomain(
    id: number,
    data: {
      name?: string
      description?: string
      enabled?: boolean
    }
  ): Promise<ArticleDomain> {
    const response = await request.put(`/filter/domains/${id}`, data)
    return response.data
  },

  async deleteDomain(id: number): Promise<{ success: boolean }> {
    const response = await request.delete(`/filter/domains/${id}`)
    return response.data
  },

  // 文章过滤 - 关键词
  async getKeywords(
    domainId?: number,
    keywordType?: 'positive' | 'negative'
  ): Promise<ArticleKeyword[]> {
    const params: Record<string, any> = {}
    if (domainId !== undefined) params.domain_id = domainId
    if (keywordType) params.keyword_type = keywordType
    const response = await request.get('/filter/keywords', { params })
    // 拦截器已处理：如果直接返回数组则直接返回，如果是包装格式则返回整个 response.data
    if (Array.isArray(response)) {
      return response
    }
    // 处理包装格式 { code: 0, message: "success", data: [...] }
    if (response && response.data && Array.isArray(response.data)) {
      return response.data
    }
    return []
  },

  async createKeyword(data: {
    domain_id: number
    keyword_type?: 'positive' | 'negative'
    keyword_text: string
    is_regex?: boolean
    is_required?: boolean
    alias?: string
    priority?: number
    max_results?: number
  }): Promise<ArticleKeyword> {
    const response = await request.post('/filter/keywords', data)
    return response.data
  },

  async deleteKeyword(id: number): Promise<{ success: boolean }> {
    const response = await request.delete(`/filter/keywords/${id}`)
    return response.data
  },

  // 全局配置
  async getGlobalConfig(): Promise<GlobalConfig> {
    const response = await request.get('/config/global')
    return response.data
  },

  async updateGlobalConfig(data: {
    rssSchedule?: string
    translationEnabled?: boolean
  }): Promise<GlobalConfig> {
    const response = await request.put('/config/global', data)
    return response.data
  },
}
