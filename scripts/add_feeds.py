#!/usr/bin/env python3
# coding=utf-8
"""批量添加 RSS 订阅源"""
import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.feed import RSSFeed

FEEDS = [
    ("MachineLearningMastery.com", "https://machinelearningmastery.com/blog/feed/"),
    ("MarkTechPost", "https://www.marktechpost.com/feed/"),
    ("Lil'Log", "https://lilianweng.github.io/index.xml"),
    ("Anthropic Press Releases", "https://feedproxy.feedly.com/5b36e586-cfce-45df-9d64-1cf9fed78e5b"),
    ("The AI Blog", "https://blogs.microsoft.com/ai/feed/"),
    ("AI News", "https://www.artificialintelligence-news.com/feed/"),
    ("Artificial Intelligence on Medium", "https://medium.com/feed/tag/artificial-intelligence"),
    ("MIT News - CSAIL", "http://web.mit.edu/newsoffice/topic/mitcomputers-rss.xml"),
    ("The Stanford AI Lab Blog", "http://ai.stanford.edu/blog/feed.xml"),
    ("Towards Data Science - Medium", "https://towardsdatascience.com/feed"),
    ("MIT News - Artificial intelligence", "http://news.mit.edu/rss/topic/artificial-intelligence2"),
    ("Artificial Intelligence (AI) | TechCrunch", "https://techcrunch.com/tag/artificial-intelligence/feed/"),
    ("OpenAI", "https://blog.openai.com/rss/"),
    ("DeepMind", "https://deepmind.com/blog/feed/basic/"),
    ("Becoming Human: Artificial Intelligence Magazine", "https://becominghuman.ai/feed"),
    ("AWS Machine Learning Blog", "https://aws.amazon.com/blogs/amazon-ai/feed/"),
    ("机器之心", "http://www.jiqizhixin.com/rss"),
    ("infoq", "http://www.infoq.com/cn/feed"),
    ("美团技术团队", "https://tech.meituan.com/feed/"),
]

def main():
    db = SessionLocal()
    added = 0
    for name, url in FEEDS:
        if db.query(RSSFeed).filter(RSSFeed.feed_url == url).first():
            print(f"已存在: {name}")
            continue
        feed = RSSFeed(
            id=f"feed_{uuid.uuid4().hex[:8]}",
            name=name,
            feed_url=url,
            is_active=1,
            push_count=10,
        )
        db.add(feed)
        added += 1
        print(f"添加: {name}")
    db.commit()
    db.close()
    print(f"\n共添加 {added} 个订阅源")

if __name__ == "__main__":
    main()
