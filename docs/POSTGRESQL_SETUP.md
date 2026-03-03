# PostgreSQL 存储集成使用指南

## 概述

TrendRadar 已支持 PostgreSQL 作为存储后端，可以将爬取的热榜数据、RSS订阅数据以及AI生成的博客选题存储到PostgreSQL数据库中。

## 功能特性

- ✅ 热榜新闻数据存储（包含排名历史、标题变更记录）
- ✅ RSS订阅数据存储
- ✅ AI博客选题及参考资料存储
- ✅ 支持与SQLite并存（可配置切换）
- ✅ 数据迁移工具（SQLite → PostgreSQL）

## 部署步骤

### 1. 安装 PostgreSQL

确保 PostgreSQL 已安装并运行（同一台机器或远程）。

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS (使用 Homebrew)
brew install postgresql
brew services start postgresql

# 验证安装
psql --version
```

### 2. 创建数据库

```bash
# 切换到 postgres 用户
sudo -u postgres psql

# 在 psql 命令行中执行
CREATE DATABASE trendradar;
CREATE USER trendradar_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE trendradar TO trendradar_user;

# PostgreSQL 15+ 需要额外授权
\c trendradar
GRANT ALL ON SCHEMA public TO trendradar_user;

# 退出
\q
```

### 3. 安装依赖

```bash
pip install psycopg2-binary
```

### 4. 配置 TrendRadar

编辑 `config/config.yaml`：

```yaml
storage:
  backend: "postgresql"  # 或 "auto" 自动选择
  
  postgresql:
    enabled: true
    host: "localhost"
    port: 5432
    database: "trendradar"
    user: "t_admin"
    password: "12345678"
```

**推荐使用环境变量（更安全）：**

```bash
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_DB="trendradar"
export POSTGRES_USER="trendradar_user"
export POSTGRES_PASSWORD="your_password"
```

### 5. 运行测试

```bash
# 运行爬虫，数据会自动存储到 PostgreSQL
python -m trendradar
```

## 数据迁移

如果你已有 SQLite 数据，可使用迁移工具将数据转移到 PostgreSQL：

### 迁移所有数据

```bash
python -m tools.migrate_to_postgresql --all
```

### 迁移指定日期范围

```bash
python -m tools.migrate_to_postgresql \
  --start-date 2026-02-05 \
  --end-date 2026-02-12
```

### 迁移单日数据

```bash
python -m tools.migrate_to_postgresql --date 2026-02-12
```

### 强制覆盖已存在的数据

```bash
python -m tools.migrate_to_postgresql --all --force
```

## 数据查询

### 使用 psql 查询

```bash
# 连接数据库
psql -h localhost -U trendradar_user -d trendradar

# 查看表结构
\dt

# 查询热榜数据
SELECT date, crawl_time, title, platform_id, rank 
FROM news_items 
WHERE DATE(created_at) = '2026-02-12' 
ORDER BY created_at DESC 
LIMIT 10;

# 查询 RSS 数据
SELECT date, crawl_time, title, feed_id 
FROM rss_items 
WHERE DATE(created_at) = '2026-02-12' 
ORDER BY created_at DESC 
LIMIT 10;

# 查询 AI 博客选题
SELECT id, title, description, news_count, generated_at 
FROM blog_topics 
ORDER BY generated_at DESC 
LIMIT 10;

# 查看选题的参考资料
SELECT t.title as topic_title, r.article_title, r.article_url 
FROM blog_topics t 
JOIN topic_references r ON t.id = r.topic_id 
WHERE t.id = 1;
```

## 数据库架构

### 热榜相关表

- `platforms` - 平台信息
- `news_items` - 新闻条目
- `title_changes` - 标题变更历史
- `rank_history` - 排名历史
- `crawl_records` - 抓取记录
- `crawl_source_status` - 抓取来源状态
- `push_records` - 推送记录

### RSS 相关表

- `rss_feeds` - RSS 源配置
- `rss_items` - RSS 条目
- `rss_crawl_records` - RSS 抓取记录
- `rss_crawl_status` - RSS 抓取状态
- `rss_push_records` - RSS 推送记录

### AI 博客选题相关表

- `blog_topics` - 博客选题
- `topic_references` - 选题参考资料

## 性能优化建议

### 1. 创建索引

主要索引已在 schema 中定义，如需额外优化：

```sql
-- 为常用查询字段创建索引
CREATE INDEX idx_news_created_at ON news_items(created_at DESC);
CREATE INDEX idx_rss_created_at ON rss_items(created_at DESC);
```

### 2. 定期清理

```sql
-- 删除30天前的数据
DELETE FROM news_items WHERE DATE(created_at) < CURRENT_DATE - INTERVAL '30 days';
DELETE FROM rss_items WHERE DATE(created_at) < CURRENT_DATE - INTERVAL '30 days';
```

### 3. 数据库维护

```sql
-- 更新统计信息
ANALYZE;

-- 清理死元组
VACUUM;

-- 完整清理（需要更多时间）
VACUUM FULL;
```

## 备份与恢复

### 备份数据库

```bash
# 备份整个数据库
pg_dump -h localhost -U trendradar_user -d trendradar > trendradar_backup.sql

# 备份特定表
pg_dump -h localhost -U trendradar_user -d trendradar -t blog_topics -t topic_references > blog_topics_backup.sql
```

### 恢复数据库

```bash
# 恢复数据库
psql -h localhost -U trendradar_user -d trendradar < trendradar_backup.sql
```

## 故障排查

### 连接失败

```bash
# 检查 PostgreSQL 服务状态
sudo systemctl status postgresql

# 检查连接
psql -h localhost -U trendradar_user -d trendradar -c "SELECT version();"
```

### 权限问题

```sql
-- 重新授权
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trendradar_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trendradar_user;
```

### 查看日志

```bash
# PostgreSQL 日志位置（Ubuntu）
sudo tail -f /var/log/postgresql/postgresql-*.log
```

## 常见问题

### Q: PostgreSQL 和 SQLite 可以同时使用吗？

A: 不建议同时使用。配置中选择一个作为主存储后端。如需切换，使用迁移工具。

### Q: 数据迁移会覆盖已存在的数据吗？

A: 默认跳过已存在的数据。使用 `--force` 参数可强制覆盖。

### Q: AI 博客选题只在 PostgreSQL 中保存吗？

A: 是的，博客选题持久化功能仅在 PostgreSQL 后端中实现。SQLite 后端仅在推送中显示，不持久化。

## 进阶配置

### 使用连接池

如需高并发场景，可配置连接池（需修改代码集成 pgbouncer 或使用 SQLAlchemy）。

### 远程 PostgreSQL

如 PostgreSQL 部署在其他机器：

```yaml
postgresql:
  host: "192.168.1.100"  # 远程IP
  port: 5432
  # 其他配置...
```

确保防火墙允许连接：

```bash
# 在 PostgreSQL 服务器上
sudo ufw allow 5432/tcp
```

修改 PostgreSQL 配置允许远程连接：

```bash
# 编辑 postgresql.conf
listen_addresses = '*'

# 编辑 pg_hba.conf，添加
host    all    all    0.0.0.0/0    md5

# 重启服务
sudo systemctl restart postgresql
```

