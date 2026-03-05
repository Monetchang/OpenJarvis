#!/usr/bin/env python3
"""将 config/default_sources.json 中的 RSS 源写入数据库，替换现有源。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import get_db_context, engine
from app.models.feed import RSSFeed
from app.models.article import RSSItem
from sqlalchemy import text

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default_sources.json"


def main():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        sources = json.load(f)

    with get_db_context() as db:
        db.execute(text("DELETE FROM rss_items"))
        db.execute(text("DELETE FROM rss_feeds"))

        for s in sources:
            feed = RSSFeed(
                id=s["id"],
                name=s["name"],
                feed_url=s["url"],
                is_active=1 if s.get("enabled", True) else 0,
                source_type=s.get("type", "rss"),
                use_proxy_override=1 if s.get("use_proxy") else (0 if "use_proxy" in s else None),
                refresh_interval_minutes=s.get("refresh_interval_minutes", 30),
                tags=s.get("tags", []),
            )
            db.add(feed)

    print(f"已替换为 {len(sources)} 个 RSS 源")


if __name__ == "__main__":
    main()
