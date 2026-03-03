# RSS 解析策略文档

## 概述

本文档详细描述了一套通用的 RSS/Atom/JSON Feed 解析框架，支持多种格式和数据结构的统一处理。该策略可直接复用到其他项目中。

**主要特性：**
- ✅ 支持 RSS 2.0、Atom 1.0、JSON Feed 1.1 三种格式
- ✅ 自动格式检测和转换
- ✅ 多层次日期时间解析（容错能力强）
- ✅ HTML 清理和文本规范化
- ✅ 灵活的字段映射和备选方案

---

## 支持的格式

### 1. RSS 2.0

**标准元素：**
```xml
<rss version="2.0">
  <channel>
    <item>
      <title>文章标题</title>
      <link>https://example.com/article</link>
      <pubDate>Mon, 22 Feb 2026 10:00:00 GMT</pubDate>
      <description>文章摘要或内容</description>
      <author>author@example.com</author>
      <guid isPermaLink="false">unique-id</guid>
    </item>
  </channel>
</rss>
```

**时间格式：** RFC 2822（如 `Mon, 22 Feb 2026 10:00:00 GMT`）

### 2. Atom 1.0

**标准元素：**
```xml
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>文章标题</title>
    <link href="https://example.com/article" rel="alternate" type="text/html"/>
    <published>2026-02-22T10:00:00Z</published>
    <updated>2026-02-22T10:30:00Z</updated>
    <summary>文章摘要</summary>
    <content type="html">文章内容</content>
    <author>
      <name>作者名称</name>
      <email>author@example.com</email>
    </author>
    <id>urn:uuid:unique-id</id>
  </entry>
</feed>
```

**时间格式：** ISO 8601（如 `2026-02-22T10:00:00Z` 或 `2026-02-22T10:00:00+08:00`）

### 3. JSON Feed 1.1

**标准结构：**
```json
{
  "version": "https://jsonfeed.org/version/1.1",
  "title": "Feed 标题",
  "items": [
    {
      "id": "unique-id",
      "title": "文章标题",
      "url": "https://example.com/article",
      "date_published": "2026-02-22T10:00:00Z",
      "date_modified": "2026-02-22T10:30:00Z",
      "summary": "文章摘要",
      "content_text": "纯文本内容",
      "content_html": "<p>HTML 内容</p>",
      "authors": [
        {"name": "作者名称"}
      ]
    }
  ]
}
```

**时间格式：** ISO 8601

---

## 解析流程

### 流程图

```
输入：Feed 内容（XML 或 JSON）
  ↓
检测格式
  ├─ 是否为 JSON Feed？ → 走 JSON Feed 解析路径
  └─ 否 → 走 feedparser 解析路径
  ↓
验证内容合法性
  ├─ 成功 → 继续
  └─ 失败 → 抛出异常
  ↓
遍历每个条目 (entry/item)
  ↓
提取字段
  ├─ 标题 (title)
  ├─ 链接 (url/link)
  ├─ 发布时间 (published_at)
  ├─ 摘要 (summary)
  ├─ 作者 (author)
  └─ 唯一标识 (guid/id)
  ↓
清理文本
  ├─ HTML 实体解码
  ├─ 移除 HTML 标签
  └─ 移除多余空白
  ↓
返回标准化结果
```

---

## 字段解析策略

### 标题 (Title)

**RSS 2.0：**
```xml
<title>文章标题</title>
```

**Atom：**
```xml
<title>文章标题</title>
```

**JSON Feed：**
```json
{
  "title": "文章标题",
  "content_text": "如果 title 为空，取前 100 字符"
}
```

**解析逻辑：**
```
1. 获取 title 字段
2. 若为空：
   - JSON Feed: 使用 content_text 前 100 字符 + "..."
   - RSS/Atom: 返回空值（过滤掉）
3. 清理 HTML 实体和标签
4. 验证非空，否则返回 None
```

### 链接 (URL)

**RSS 2.0：**
```xml
<link>https://example.com/article</link>
```

**Atom：**
```xml
<!-- 可能多个 link，优先选择 rel="alternate" 的 -->
<link href="https://example.com" rel="alternate" type="text/html"/>
<link href="https://example.com" rel="self"/>
```

**JSON Feed：**
```json
{
  "url": "https://example.com/article",
  "external_url": "备选"
}
```

**解析逻辑（Atom）：**
```python
# 优先级：rel="alternate" > type="text/html" > 第一个link
url = None
for link in links:
    if link.get("rel") == "alternate":
        url = link.get("href")
        break
    elif link.get("type", "").startswith("text/html"):
        url = link.get("href")
        break
if not url and links:
    url = links[0].get("href")
```

### 发布时间 (Published At)

**优先级顺序：**

#### 第1层：Feedparser 自动解析（最常用）
```python
# feedparser 自动将日期转为时间元组
date_struct = entry.get("published_parsed") \
              or entry.get("updated_parsed")

if date_struct:
    # date_struct = (2026, 2, 22, 10, 0, 0)
    dt = datetime(*date_struct[:6])
    return dt.isoformat()  # "2026-02-22T10:00:00"
```

**适用格式：**
- RSS 2.0: `Mon, 22 Feb 2026 10:00:00 GMT`
- Atom: `2026-02-22T10:00:00Z`

#### 第2层：RFC 2822 邮件日期格式
```python
from email.utils import parsedate_to_datetime

date_str = entry.get("published") or entry.get("updated")
try:
    dt = parsedate_to_datetime(date_str)
    return dt.isoformat()
except (ValueError, TypeError):
    pass
```

**适用格式：**
- `Mon, 22 Feb 2026 10:00:00 GMT`
- `22 Feb 2026 10:00:00 +0000`
- `Mon, 22 Feb 2026 10:00:00 +0800`

#### 第3层：ISO 8601 直接解析
```python
date_str = date_str.replace("Z", "+00:00")  # Z 表示 UTC
dt = datetime.fromisoformat(date_str)
return dt.isoformat()
```

**适用格式：**
- `2026-02-22T10:00:00Z`
- `2026-02-22T10:00:00+08:00`
- `2026-02-22T10:00:00.123Z`

#### 第4层：失败处理
```python
# 所有方案都失败
return None  # 文章保留但无发布时间

# 在新鲜度过滤时，无时间的文章不会被删除
# 如果需要过滤，可单独处理
```

**时间解析决策树：**
```
有 published_parsed？
  ├─ YES → 返回
  └─ NO ↓

有 updated_parsed？
  ├─ YES → 返回
  └─ NO ↓

尝试 RFC 2822 解析
  ├─ SUCCESS → 返回
  └─ FAIL ↓

尝试 ISO 8601 解析
  ├─ SUCCESS → 返回
  └─ FAIL ↓

返回 None
```

### 摘要 (Summary)

**优先级：**
```
RSS: summary > description > content[0].value
Atom: summary > content.value
JSON Feed: summary > content_text
```

**处理流程：**
```python
1. 获取摘要字段
2. 若为空，尝试备选字段
3. 清理 HTML
4. 若长度 > 500 字符，截断并追加 "..."
5. 返回 None 或清理后的字符串
```

### 作者 (Author)

**优先级：**
```
RSS: author > dc:creator
Atom: author.name（列表）> author（单个）
JSON Feed: authors[].name（列表）
```

**解析逻辑：**
```python
# RSS / Atom 单作者
author = entry.get("author")
if author:
    return clean_text(author)

# Atom / JSON Feed 多作者
authors = entry.get("authors", [])
if authors:
    names = [a.get("name", "") for a in authors if isinstance(a, dict)]
    if names:
        return ", ".join(names)

return None
```

### 唯一标识 (GUID/ID)

**优先级：**
```
RSS: guid.value > guid > link（降级）
Atom: id > link
JSON Feed: id > url
```

---

## 文本清理策略

### HTML 实体解码

```python
import html

# 解码常见实体
html.unescape("&lt;tag&gt;")  # "<tag>"
html.unescape("&amp;")         # "&"
html.unescape("&#x3C;")        # "<"
html.unescape("&nbsp;")        # " "
```

### HTML 标签移除

```python
import re

# 移除所有 HTML 标签
text = re.sub(r'<[^>]+>', '', text)

# 示例
"<p>Hello <b>world</b></p>"  # → "Hello world"
```

### 空白规范化

```python
# 多个连续空白 → 单个空格
text = re.sub(r'\s+', ' ', text)
text = text.strip()

# 示例
"Hello    world\n\n"  # → "Hello world"
```

### 完整清理函数

```python
def clean_text(text: str) -> str:
    """清理文本：解码 HTML、移除标签、规范化空白"""
    if not text:
        return ""
    
    # 1. 解码 HTML 实体
    text = html.unescape(text)
    
    # 2. 移除 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 3. 规范化空白
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

# 测试
input_text = "<p>Hello &amp; <b>world</b>&nbsp;&nbsp;&nbsp;</p>"
output = clean_text(input_text)
# output = "Hello & world"
```

---

## 格式自动检测

### 检测 JSON Feed

```python
def is_json_feed(content: str) -> bool:
    """
    检测内容是否为 JSON Feed 格式
    
    JSON Feed 必须包含 version 字段，值中含有 jsonfeed.org
    """
    content = content.strip()
    
    # 快速检查
    if not content.startswith("{"):
        return False
    
    try:
        data = json.loads(content)
        version = data.get("version", "")
        return "jsonfeed.org" in version
    except (json.JSONDecodeError, TypeError):
        return False

# 示例
is_json_feed('{"version": "https://jsonfeed.org/version/1.1"}')  # True
is_json_feed('<?xml version="1.0"?><rss>...</rss>')  # False
```

### 使用 Feedparser 处理 RSS/Atom

```python
import feedparser

content = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>示例</title>
      ...
    </item>
  </channel>
</rss>"""

feed = feedparser.parse(content)

# 检查解析是否成功
if feed.bozo and not feed.entries:
    raise ValueError(f"解析失败: {feed.bozo_exception}")

# 遍历条目
for entry in feed.entries:
    title = entry.get("title", "")
    # ... 处理每个条目
```

---

## 错误处理

### 解析异常

```python
class RSSParseError(Exception):
    """RSS 解析错误基类"""
    pass

# 处理 JSON 解析错误
try:
    data = json.loads(content)
except json.JSONDecodeError as e:
    raise RSSParseError(f"JSON 解析失败: {e}")

# 处理 feedparser 解析错误
feed = feedparser.parse(content)
if feed.bozo and not feed.entries:
    raise RSSParseError(f"RSS/Atom 解析失败: {feed.bozo_exception}")
```

### 单条目异常处理

```python
items = []
for entry in feed.entries:
    try:
        item = parse_entry(entry)
        if item:  # None 表示该条目无效（如标题为空）
            items.append(item)
    except Exception as e:
        # 记录错误但继续处理其他条目
        logger.warning(f"条目解析失败: {e}")
        continue

return items
```

### 日期解析降级

```python
def parse_date(entry: dict) -> Optional[str]:
    """
    解析发布日期，支持多种格式和自动降级
    """
    # 第1层：feedparser 自动解析
    date_struct = entry.get("published_parsed")
    if date_struct:
        try:
            dt = datetime(*date_struct[:6])
            return dt.isoformat()
        except (ValueError, TypeError):
            pass
    
    # 第2层：RFC 2822
    date_str = entry.get("published")
    if date_str:
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.isoformat()
        except (ValueError, TypeError):
            pass
    
    # 第3层：ISO 8601
    if date_str:
        try:
            date_str = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(date_str)
            return dt.isoformat()
        except (ValueError, TypeError):
            pass
    
    # 全部失败
    return None
```

---

## 数据结构定义

### 输入数据结构

```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class ParsedRSSItem:
    """解析后的 RSS 条目（统一格式）"""
    title: str                  # 必需，非空
    url: str                    # 链接（可能为空）
    published_at: Optional[str] = None  # ISO 8601 格式
    summary: Optional[str] = None        # 摘要/描述
    author: Optional[str] = None         # 作者信息
    guid: Optional[str] = None           # 唯一标识

# 输出格式示例
ParsedRSSItem(
    title="Introduction to RAG Systems",
    url="https://example.com/rag",
    published_at="2026-02-22T10:00:00",
    summary="This article explains RAG architecture...",
    author="John Doe",
    guid="urn:uuid:abc-123"
)
```

---

## 实现示例

### 最小化实现

```python
import feedparser
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional

class RSSParser:
    def parse(self, content: str) -> List[dict]:
        """解析 RSS/Atom 内容"""
        feed = feedparser.parse(content)
        
        if feed.bozo and not feed.entries:
            raise ValueError(f"解析失败: {feed.bozo_exception}")
        
        items = []
        for entry in feed.entries:
            item = {
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "published_at": self._parse_date(entry),
                "summary": entry.get("summary", ""),
                "author": entry.get("author", ""),
                "guid": entry.get("id") or entry.get("link")
            }
            
            if item["title"]:  # 标题非空才保留
                items.append(item)
        
        return items
    
    def _parse_date(self, entry: dict) -> Optional[str]:
        """尝试多种方式解析日期"""
        # 方法1：feedparser 自动解析
        date_struct = entry.get("published_parsed")
        if date_struct:
            try:
                return datetime(*date_struct[:6]).isoformat()
            except:
                pass
        
        # 方法2：RFC 2822
        date_str = entry.get("published")
        if date_str:
            try:
                return parsedate_to_datetime(date_str).isoformat()
            except:
                pass
        
        # 方法3：ISO 8601
        if date_str:
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
            except:
                pass
        
        return None

# 使用示例
parser = RSSParser()
with open("feed.xml") as f:
    items = parser.parse(f.read())
for item in items:
    print(f"{item['title']} - {item['published_at']}")
```

### 完整实现（参考 TrendRadar）

参见项目文件：[trendradar/crawler/rss/parser.py](../trendradar/crawler/rss/parser.py)

---

## 测试用例

### RSS 2.0 测试

```xml
<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Breaking: New AI Model Released</title>
      <link>https://techcrunch.com/article</link>
      <pubDate>Mon, 22 Feb 2026 10:00:00 GMT</pubDate>
      <description>&lt;p&gt;OpenAI released a new model&lt;/p&gt;</description>
      <author>reporter@techcrunch.com</author>
      <guid>https://techcrunch.com/article</guid>
    </item>
  </channel>
</rss>
```

**预期输出：**
```json
{
  "title": "Breaking: New AI Model Released",
  "url": "https://techcrunch.com/article",
  "published_at": "2026-02-22T10:00:00",
  "summary": "OpenAI released a new model",
  "author": "reporter@techcrunch.com",
  "guid": "https://techcrunch.com/article"
}
```

### Atom 测试

```xml
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>AI Agent Benchmark Results</title>
    <link href="https://simonwillison.net/article" rel="alternate" type="text/html"/>
    <published>2026-02-22T10:00:00Z</published>
    <updated>2026-02-22T10:30:00Z</updated>
    <summary>Comparison of popular AI agents</summary>
    <author>
      <name>Simon Willison</name>
    </author>
    <id>tag:simonwillison.net,2026:article</id>
  </entry>
</feed>
```

**预期输出：**
```json
{
  "title": "AI Agent Benchmark Results",
  "url": "https://simonwillison.net/article",
  "published_at": "2026-02-22T10:00:00",
  "summary": "Comparison of popular AI agents",
  "author": "Simon Willison",
  "guid": "tag:simonwillison.net,2026:article"
}
```

### JSON Feed 测试

```json
{
  "version": "https://jsonfeed.org/version/1.1",
  "title": "AI News",
  "items": [
    {
      "id": "1",
      "title": "LLM Optimization Techniques",
      "url": "https://example.com/llm-opt",
      "date_published": "2026-02-22T10:00:00Z",
      "summary": "New methods for optimizing large language models",
      "authors": [{"name": "Dr. Jane Smith"}]
    }
  ]
}
```

**预期输出：**
```json
{
  "title": "LLM Optimization Techniques",
  "url": "https://example.com/llm-opt",
  "published_at": "2026-02-22T10:00:00",
  "summary": "New methods for optimizing large language models",
  "author": "Dr. Jane Smith",
  "guid": "1"
}
```

---

## 性能考虑

### 推荐配置

| 参数 | 推荐值 | 说明 |
|------|-------|------|
| 请求超时 | 15-30秒 | RSS 源响应时间差异大 |
| 最大摘要长度 | 500 字符 | 平衡信息量和性能 |
| User-Agent | 自定义 | 某些源会检查 UA |
| 请求重试 | 1-3 次 | 网络不稳定时有帮助 |
| 连接池 | 启用 | 多源并发请求时提升性能 |

### 优化建议

```python
# 1. 使用连接池
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=2, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

# 2. 设置合理超时
response = session.get(url, timeout=(5, 10))  # (连接超时, 读超时)

# 3. 并发请求多个 RSS 源
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(parse_feed, feed_urls)
```

---

## 常见问题

### Q: 某个 RSS 源无发布时间怎么办？

**A:** 系统会返回 `published_at: None`，此时：
- ✅ 文章仍然保存到数据库
- ✅ 参与关键词匹配和推送
- ❌ 不会被新鲜度过滤删除

### Q: 如何处理包含多个作者的情况？

**A:** 系统自动将多个作者用 `, ` 连接：
```
"author": "John Doe, Jane Smith, Bob Johnson"
```

### Q: 某些源时间格式非标准怎么办？

**A:** 多层解析策略确保兼容性。如仍无法解析，返回 `None` 而不是报错。

### Q: 如何处理被截断的摘要？

**A:** 系统自动检测长度并追加 `...`：
```python
if len(summary) > 500:
    summary = summary[:500] + "..."
```

---

## 扩展点

### 自定义字段映射

```python
# 为某个特定源自定义字段提取
CUSTOM_FIELD_MAP = {
    "techcrunch": {
        "title": "post_title",           # 自定义字段名
        "url": "post_url",
        "published_at": "publish_date",  # 可能需要额外转换
    }
}

def parse_entry_with_custom_map(entry, feed_id):
    field_map = CUSTOM_FIELD_MAP.get(feed_id)
    if field_map:
        title = entry.get(field_map["title"])
        # ... 使用自定义映射
    else:
        title = entry.get("title")
    # ... 标准处理
```

### 自定义时间格式

```python
# 添加新的时间格式支持
CUSTOM_DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y",
    "%Y年%m月%d日",
]

def parse_date_with_custom_formats(date_str):
    # 首先尝试标准方法...
    
    # 然后尝试自定义格式
    for fmt in CUSTOM_DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.isoformat()
        except ValueError:
            continue
    
    return None
```

---

## 参考资源

- [RSS 2.0 规范](https://www.rssboard.org/rss-specification)
- [Atom 1.0 规范](https://tools.ietf.org/html/rfc4287)
- [JSON Feed 1.1 规范](https://www.jsonfeed.org/version/1.1/)
- [Feedparser 文档](https://feedparser.readthedocs.io/)
- [Python datetime](https://docs.python.org/3/library/datetime.html)

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-02-22 | 初始文档，包含完整解析策略 |

---

## 许可证

本文档内容可自由复用，仅需保留原始出处注释。

**原始项目：** [TrendRadar](https://github.com/sansan0/TrendRadar)
