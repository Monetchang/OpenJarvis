-- AI RSS 聚合：rss_items 增加 guid 与去重索引，rss_feeds 增加源类型/冷却/条件 GET 等字段

-- rss_items: guid 用于去重，唯一约束 (feed_id, guid)
ALTER TABLE rss_items ADD COLUMN IF NOT EXISTS guid VARCHAR(512);
CREATE UNIQUE INDEX IF NOT EXISTS uq_rss_items_feed_guid ON rss_items (feed_id, guid) WHERE guid IS NOT NULL;

-- rss_feeds: 源类型、代理覆盖、刷新间隔、标签、抓取状态、冷却、条件 GET
ALTER TABLE rss_feeds ADD COLUMN IF NOT EXISTS source_type VARCHAR(32) DEFAULT 'rss';
ALTER TABLE rss_feeds ADD COLUMN IF NOT EXISTS use_proxy_override INTEGER;
ALTER TABLE rss_feeds ADD COLUMN IF NOT EXISTS refresh_interval_minutes INTEGER DEFAULT 30;
ALTER TABLE rss_feeds ADD COLUMN IF NOT EXISTS tags JSONB;
ALTER TABLE rss_feeds ADD COLUMN IF NOT EXISTS fetch_status VARCHAR(32);
ALTER TABLE rss_feeds ADD COLUMN IF NOT EXISTS cooldown_until TIMESTAMP WITH TIME ZONE;
ALTER TABLE rss_feeds ADD COLUMN IF NOT EXISTS last_etag VARCHAR(512);
ALTER TABLE rss_feeds ADD COLUMN IF NOT EXISTS last_modified VARCHAR(512);
