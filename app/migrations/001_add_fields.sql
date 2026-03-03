-- RSS AI Service 数据库扩展字段
-- 为 FastAPI 后端添加必要字段

-- 为 rss_feeds 表添加字段（如果不存在）
ALTER TABLE rss_feeds ADD COLUMN IF NOT EXISTS schedule VARCHAR(255) DEFAULT '0 9 * * *';
ALTER TABLE rss_feeds ADD COLUMN IF NOT EXISTS push_count INTEGER DEFAULT 10;
ALTER TABLE rss_feeds ADD COLUMN IF NOT EXISTS enable_translation INTEGER DEFAULT 0;

-- 为 rss_items 表添加字段（如果不存在）
ALTER TABLE rss_items ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE;

-- 添加索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_rss_items_is_read ON rss_items(is_read);
CREATE INDEX IF NOT EXISTS idx_rss_items_first_crawl_time ON rss_items(first_crawl_time);

