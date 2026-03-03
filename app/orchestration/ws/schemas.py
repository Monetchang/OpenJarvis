from pydantic import BaseModel


ALLOWED_STYLES = frozenset(["专业报告", "博客随笔", "营销文案", "技术教程", "新闻资讯"])
ALLOWED_AUDIENCES = frozenset(["技术从业者", "普通消费者", "学生群体", "企业管理者", "创业者"])


class WorkflowStartPayload(BaseModel):
    title: str
    refs: list[str]
    style: str
    audience: str
    language: str = "zh-CN"
    length: str = "medium"
    idea_id: str | None = None


class WorkflowStartMessage(BaseModel):
    type: str = "workflow.start"
    payload: WorkflowStartPayload
