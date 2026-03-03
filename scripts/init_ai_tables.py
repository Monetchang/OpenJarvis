#!/usr/bin/env python3
# coding=utf-8
"""创建 AI 选题相关表（blog_topics, topic_references）。仅当表不存在时创建。"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine
from app.models.ai import BlogTopic, TopicReference

if __name__ == "__main__":
    BlogTopic.__table__.create(engine, checkfirst=True)
    TopicReference.__table__.create(engine, checkfirst=True)
    print("AI 表已就绪: blog_topics, topic_references")
