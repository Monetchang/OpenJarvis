-- 飞书 Webhook 订阅者表
CREATE TABLE IF NOT EXISTS feishu_subscribers (
    id SERIAL PRIMARY KEY,
    webhook_url VARCHAR(512) NOT NULL UNIQUE,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_feishu_subscribers_active ON feishu_subscribers(is_active);
