FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .
RUN chmod +x /app/docker-entrypoint.sh

RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

EXPOSE 12135

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "12135", "--workers", "4"]

