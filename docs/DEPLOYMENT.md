# OpenJarvis Backend - 部署指南

## 生产环境部署

### 1. 使用 Docker

```bash
# 构建镜像
docker build -t openjarvis-backend .

# 运行容器
docker run -d \
  --name openjarvis-backend \
  -p 12135:12135 \
  --env-file .env \
  openjarvis-backend
```

### 2. 使用 Supervisor

```ini
[program:openjarvis]
command=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 12135 --workers 4
directory=/path/to/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/openjarvis.err.log
stdout_logfile=/var/log/openjarvis.out.log
```

### 3. 使用 systemd

创建 `/etc/systemd/system/openjarvis.service`:

```ini
[Unit]
Description=OpenJarvis Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 12135 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl daemon-reload
sudo systemctl enable openjarvis
sudo systemctl start openjarvis
```

### 4. Nginx 反向代理

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:12135;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 性能优化

### 1. Worker 数量
```bash
# 计算公式: (2 x CPU核心数) + 1
uvicorn app.main:app --workers 9  # 假设4核CPU
```

### 2. 数据库连接池
在 `app/core/database.py` 中调整:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,      # 增加连接池大小
    max_overflow=40,   # 增加溢出连接数
)
```

### 3. Redis 缓存（可选）
添加 Redis 缓存层以提升性能

## 监控

### 1. 健康检查
```bash
curl http://localhost:12135/health
```

### 2. 日志
```bash
# 查看日志
tail -f /var/log/openjarvis.out.log
```

## 备份

### 数据库备份
```bash
pg_dump -U postgres rss_ai_service > backup_$(date +%Y%m%d).sql
```

### 恢复
```bash
psql -U postgres rss_ai_service < backup_20240101.sql
```

