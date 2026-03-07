-- 文章解读结果缓存
ALTER TABLE rss_items ADD COLUMN IF NOT EXISTS interpret_result JSONB;
