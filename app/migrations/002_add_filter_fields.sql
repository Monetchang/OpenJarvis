-- 文章过滤功能数据库扩展
-- 添加关键领域和关键词过滤相关表

-- 关键领域表
CREATE TABLE IF NOT EXISTS article_domains (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 关键词规则表
CREATE TABLE IF NOT EXISTS article_keywords (
    id SERIAL PRIMARY KEY,
    domain_id INTEGER NOT NULL REFERENCES article_domains(id) ON DELETE CASCADE,
    keyword_type VARCHAR(20) NOT NULL DEFAULT 'positive', -- positive/negative
    keyword_text TEXT NOT NULL,
    is_regex BOOLEAN DEFAULT FALSE,
    is_required BOOLEAN DEFAULT FALSE, -- 必须词 (+)
    alias VARCHAR(255), -- 别名
    priority INTEGER DEFAULT 0,
    max_results INTEGER, -- 限制数量 (@N)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 为 rss_items 表添加字段（如果不存在）
ALTER TABLE rss_items ADD COLUMN IF NOT EXISTS domain_id INTEGER REFERENCES article_domains(id) ON DELETE SET NULL;
ALTER TABLE rss_items ADD COLUMN IF NOT EXISTS matched_keywords JSONB;

-- 添加索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_article_keywords_domain_id ON article_keywords(domain_id);
CREATE INDEX IF NOT EXISTS idx_article_keywords_type ON article_keywords(keyword_type);
CREATE INDEX IF NOT EXISTS idx_rss_items_domain_id ON rss_items(domain_id);
CREATE INDEX IF NOT EXISTS idx_article_domains_enabled ON article_domains(enabled);

-- 插入初始关键领域数据
INSERT INTO article_domains (name, description, enabled) VALUES
    ('AI模型架构与算法创新', 'AI模型架构与算法创新相关领域', TRUE),
    ('大模型训练与推理技术', '大模型训练与推理技术相关领域', TRUE),
    ('RAG技术与知识库构建', 'RAG技术与知识库构建相关领域', TRUE),
    ('AI Agent开发与评测', 'AI Agent开发与评测相关领域', TRUE),
    ('AI工程实践与落地应用', 'AI工程实践与落地应用相关领域', TRUE),
    ('机器学习前沿研究', '机器学习前沿研究相关领域', TRUE),
    ('AI基础设施与工具链', 'AI基础设施与工具链相关领域', TRUE),
    ('具身智能与自动驾驶', '具身智能与自动驾驶相关领域', TRUE)
ON CONFLICT (name) DO NOTHING;

