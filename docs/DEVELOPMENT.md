# OpenJarvis Backend - 开发指南

## 开发环境设置

### 1. 克隆项目
```bash
git clone <repository-url>
cd backend
```

### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖
```

### 4. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件配置数据库和 AI 服务
```

### 5. 初始化数据库
```bash
chmod +x scripts/init_db.sh
./scripts/init_db.sh
```

### 6. 启动开发服务器
```bash
uvicorn app.main:app --reload
```

## 项目结构说明

```
app/
├── api/              # API 层
│   ├── v1/           # API v1 版本
│   │   ├── endpoints/  # 具体端点
│   │   └── api.py    # 路由聚合
│   └── deps.py       # 依赖注入
├── core/             # 核心配置
│   ├── config.py     # 配置管理
│   └── database.py   # 数据库连接
├── models/           # ORM 模型
├── schemas/          # Pydantic 模式
├── services/         # 业务逻辑
└── utils/            # 工具函数
```

## 开发流程

### 添加新功能

1. **定义数据模型** (`app/models/`)
```python
# app/models/example.py
from app.core.database import Base
from sqlalchemy import Column, String

class Example(Base):
    __tablename__ = "examples"
    id = Column(String, primary_key=True)
    name = Column(String)
```

2. **定义 Schema** (`app/schemas/`)
```python
# app/schemas/example.py
from pydantic import BaseModel

class ExampleCreate(BaseModel):
    name: str

class ExampleResponse(BaseModel):
    id: str
    name: str
```

3. **实现业务逻辑** (`app/services/`)
```python
# app/services/example_service.py
def create_example(db, data):
    # 业务逻辑
    pass
```

4. **创建 API 端点** (`app/api/v1/endpoints/`)
```python
# app/api/v1/endpoints/example.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/")
def create(data: ExampleCreate):
    # 调用服务层
    pass
```

5. **注册路由** (`app/api/v1/api.py`)
```python
from app.api.v1.endpoints import example
api_router.include_router(example.router, prefix="/example", tags=["示例"])
```

## 代码规范

### 格式化
```bash
# 使用 Black 格式化
black app/

# 使用 isort 排序导入
isort app/
```

### 类型检查
```bash
mypy app/
```

### Linting
```bash
flake8 app/
```

## 测试

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/api/test_feed.py

# 测试覆盖率
pytest --cov=app tests/
```

### 编写测试
```python
# tests/api/test_example.py
def test_create_example(client):
    response = client.post("/api/v1/example/", json={"name": "test"})
    assert response.status_code == 200
```

## 调试

### 使用 pdb
```python
import pdb; pdb.set_trace()
```

### 日志
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Debug message")
```

## Git 工作流

### 分支命名
- `feature/功能名` - 新功能
- `fix/bug名` - Bug 修复
- `refactor/描述` - 重构

### Commit 规范
- `feat: 添加新功能`
- `fix: 修复 bug`
- `docs: 更新文档`
- `style: 代码格式调整`
- `refactor: 代码重构`
- `test: 添加测试`

## 常见问题

### Q: 数据库连接失败？
A: 检查 `.env` 中的数据库配置，确保 PostgreSQL 服务已启动

### Q: 导入错误？
A: 确保虚拟环境已激活，依赖已安装

### Q: API 返回 500 错误？
A: 查看控制台日志，检查数据库连接和配置

