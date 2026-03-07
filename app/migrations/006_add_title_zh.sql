-- 双语言标题：rss_items 增加 title_zh（翻译中文）
ALTER TABLE rss_items ADD COLUMN IF NOT EXISTS title_zh TEXT;
