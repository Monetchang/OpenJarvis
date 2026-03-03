# coding=utf-8
"""
文章过滤服务
"""
import re
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.filter import ArticleDomain, ArticleKeyword
from app.models.article import RSSItem

class FilterService:
    """文章过滤服务"""
    
    @staticmethod
    def match_keyword(text: str, keyword: str, is_regex: bool = False) -> bool:
        """
        匹配关键词
        
        Args:
            text: 待匹配文本（标题+摘要）
            keyword: 关键词
            is_regex: 是否为正则表达式
            
        Returns:
            是否匹配
        """
        if not text or not keyword:
            return False
            
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        if is_regex:
            try:
                pattern = re.compile(keyword, re.IGNORECASE)
                return bool(pattern.search(text))
            except re.error:
                return keyword_lower in text_lower
        else:
            return keyword_lower in text_lower
    
    @staticmethod
    def match_article(
        title: str,
        summary: str,
        keywords: List[ArticleKeyword]
    ) -> Tuple[bool, List[Dict]]:
        """
        匹配单篇文章
        
        Args:
            title: 文章标题
            summary: 文章摘要
            keywords: 关键词规则列表
            
        Returns:
            (是否匹配, 匹配的关键词信息列表)
        """
        if not keywords:
            return True, []
        
        text = f"{title} {summary or ''}"
        matched_keywords = []
        
        # 分离必须词、正向词、负向词
        required_keywords = [k for k in keywords if k.is_required]
        positive_keywords = [k for k in keywords if k.keyword_type == "positive" and not k.is_required]
        negative_keywords = [k for k in keywords if k.keyword_type == "negative"]
        
        # 检查负向词（过滤词）
        for keyword in negative_keywords:
            if FilterService.match_keyword(text, keyword.keyword_text, keyword.is_regex):
                return False, []
        
        # 检查必须词（所有必须词都要匹配）
        for keyword in required_keywords:
            if FilterService.match_keyword(text, keyword.keyword_text, keyword.is_regex):
                matched_keywords.append({
                    "id": keyword.id,
                    "text": keyword.keyword_text,
                    "alias": keyword.alias,
                    "type": "required"
                })
            else:
                return False, []
        
        # 检查正向词（至少匹配一个）
        if positive_keywords:
            matched_any = False
            for keyword in positive_keywords:
                if FilterService.match_keyword(text, keyword.keyword_text, keyword.is_regex):
                    matched_any = True
                    matched_keywords.append({
                        "id": keyword.id,
                        "text": keyword.keyword_text,
                        "alias": keyword.alias,
                        "type": "positive"
                    })
            
            if not matched_any and not required_keywords:
                return False, []
        
        return True, matched_keywords
    
    @staticmethod
    def filter_articles(
        articles: List[RSSItem],
        domain_id: Optional[int] = None,
        db: Optional[Session] = None
    ) -> List[Tuple[RSSItem, List[Dict]]]:
        """
        批量过滤文章
        
        Args:
            articles: 文章列表
            domain_id: 领域ID
            db: 数据库会话
            
        Returns:
            [(文章, 匹配的关键词信息), ...]
        """
        if not domain_id or not db:
            return [(article, []) for article in articles]
        
        # 获取该领域的关键词规则
        keywords = db.query(ArticleKeyword).filter(
            ArticleKeyword.domain_id == domain_id
        ).order_by(
            ArticleKeyword.priority.desc(),
            ArticleKeyword.created_at.desc()
        ).all()
        
        if not keywords:
            return [(article, []) for article in articles]
        
        # 获取限制数量
        max_results = None
        for keyword in keywords:
            if keyword.max_results is not None:
                if max_results is None or keyword.max_results < max_results:
                    max_results = keyword.max_results
        
        # 过滤文章
        filtered = []
        for article in articles:
            title = article.title or ""
            summary = article.summary or ""
            is_match, matched_keywords = FilterService.match_article(
                title, summary, keywords
            )
            
            if is_match:
                filtered.append((article, matched_keywords))
                
                # 应用限制数量
                if max_results and len(filtered) >= max_results:
                    break
        
        return filtered
    
    @staticmethod
    def filter_by_keywords(
        articles: List[RSSItem],
        positive_keywords: Optional[List[str]] = None,
        negative_keywords: Optional[List[str]] = None
    ) -> List[RSSItem]:
        """
        根据关键词列表过滤文章（简单匹配）
        
        Args:
            articles: 文章列表
            positive_keywords: 正向关键词列表
            negative_keywords: 负向关键词列表
            
        Returns:
            过滤后的文章列表
        """
        if not positive_keywords and not negative_keywords:
            return articles
        
        filtered = []
        for article in articles:
            text = f"{article.title or ''} {article.summary or ''}".lower()
            
            # 检查负向关键词
            if negative_keywords:
                excluded = False
                for keyword in negative_keywords:
                    if keyword.lower() in text:
                        excluded = True
                        break
                if excluded:
                    continue
            
            # 检查正向关键词
            if positive_keywords:
                matched = False
                for keyword in positive_keywords:
                    if keyword.lower() in text:
                        matched = True
                        break
                if not matched:
                    continue
            
            filtered.append(article)
        
        return filtered

    @staticmethod
    def two_phase_pipeline(
        articles: List[RSSItem],
        neg_keywords: List[ArticleKeyword],
        trusted_feed_ids: Optional[set] = None,
        other_max: int = 2,
        db: Optional[Session] = None,
    ) -> Tuple[List[RSSItem], str]:
        """
        两阶段管道（仅依据 DB 领域系统）:
        Phase1: 负向关键词过滤 → 候选集
        Phase2: 从 DB 加载启用领域+关键词，普通文章按领域分桶（首匹配），各桶取 domain.max_results；信任源直接保留。

        Returns: (filtered_articles, filter_tier)
        """
        trusted = trusted_feed_ids or set()

        # ── Phase 1: 负向过滤 ──
        if neg_keywords:
            candidates = []
            for article in articles:
                text = f"{article.title or ''} {article.summary or ''}"
                if not any(
                    FilterService.match_keyword(text, kw.keyword_text, kw.is_regex)
                    for kw in neg_keywords
                ):
                    candidates.append(article)
        else:
            candidates = list(articles)

        if not candidates:
            return articles, "fallback"

        trusted_articles = [a for a in candidates if a.feed_id in trusted]
        normal_articles = [a for a in candidates if a.feed_id not in trusted]

        # ── Phase 2: 从 DB 加载领域 + 关键词，分桶 ──
        if not db:
            result = list(candidates)
            result.sort(key=lambda a: (0 if a.published_at else 1, a.published_at or ""), reverse=True)
            return result, "soft"

        domains = db.query(ArticleDomain).filter(ArticleDomain.enabled == True).order_by(ArticleDomain.id).all()
        domain_keywords: Dict[int, List[ArticleKeyword]] = {}
        for d in domains:
            kws = db.query(ArticleKeyword).filter(
                ArticleKeyword.domain_id == d.id
            ).order_by(ArticleKeyword.priority.desc(), ArticleKeyword.created_at.desc()).all()
            if kws:
                domain_keywords[d.id] = kws

        buckets: List[List[Tuple[int, RSSItem]]] = [[] for _ in domains]
        other_bucket: List[RSSItem] = []

        for article in normal_articles:
            title = article.title or ""
            summary = article.summary or ""
            placed = False
            for i, domain in enumerate(domains):
                kws = domain_keywords.get(domain.id)
                if not kws:
                    continue
                is_match, matched = FilterService.match_article(title, summary, kws)
                if is_match and matched:
                    score = len(matched)
                    buckets[i].append((score, article))
                    placed = True
                    break
            if not placed:
                other_bucket.append(article)

        has_category_match = any(b for b in buckets)

        result: List[RSSItem] = []
        for i, domain in enumerate(domains):
            bucket = buckets[i]
            max_n = getattr(domain, "max_results", None) or 3
            bucket.sort(key=lambda x: (x[0], x[1].published_at or ""), reverse=True)
            result.extend(a for _, a in bucket[:max_n])

        other_bucket.sort(
            key=lambda a: (0 if a.published_at else 1, a.published_at or ""), reverse=True
        )
        result.extend(other_bucket[:other_max])
        result.extend(trusted_articles)

        if not result:
            return candidates, "soft"

        tier = "strict" if (has_category_match or trusted_articles) else "soft"
        result.sort(key=lambda a: (0 if a.published_at else 1, a.published_at or ""), reverse=True)
        return result, tier

