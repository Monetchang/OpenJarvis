#!/usr/bin/env python3
# coding=utf-8
"""临时脚本：删除当日生成的选题，便于重新生成"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_db_context
from app.models.ai import BlogTopic

if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db_context() as db:
        count = db.query(BlogTopic).filter(BlogTopic.date == today).delete()
        db.commit()
    print(f"已删除 {today} 的 {count} 个选题")
