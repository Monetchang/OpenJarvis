export interface User {
  email: string | null
  isEmailBound: boolean
}

export interface RssFeed {
  id: string
  name: string
  url: string
  pushCount: number
  isTrusted?: boolean
  createdAt: string
}

export interface Article {
  id: number
  title: string
  source: string
  feedName: string
  summary: string
  url: string
  publishedAt: string
  pushedAt: string
  isRead: boolean
  isNew?: boolean
}

export interface Idea {
  id: string
  title: string
  relatedArticles: {
    title: string
    source: string
    url: string
  }[]
  reason: string
}

export interface CreationParams {
  ideaId: string
  ideaTitle: string
  style: string
  audience: string
}

export interface GeneratedArticle {
  title: string
  content: string
  generatedAt: string
}

export interface ArticleDomain {
  id: number
  name: string
  description?: string
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface ArticleKeyword {
  id: number
  domain_id: number
  keyword_type: 'positive' | 'negative'
  keyword_text: string
  is_regex: boolean
  is_required: boolean
  alias?: string
  priority: number
  max_results?: number
  created_at: string
}

export interface GlobalConfig {
  rssSchedule: string
  translationEnabled: boolean
}

