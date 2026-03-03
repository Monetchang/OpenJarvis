#!/usr/bin/env python3
# coding=utf-8
"""将 ARTICLE_CATEGORY_RULES 迁移到 DB 领域系统：ALTER TABLE、清空旧领域、创建 6 个领域并写入关键词"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.models.filter import ArticleDomain, ArticleKeyword

DOMAINS = [
    {
        "name": "AI模型架构与算法",
        "max_results": 3,
        "required_patterns": [r"模型|算法|架构", r"AI|人工智能|深度学习"],
        "keywords": ["Transformer", "MoE", "注意力机制", "RLHF", "量化", "蒸馏", "LoRA"],
    },
    {
        "name": "AI大模型技术",
        "max_results": 3,
        "required_patterns": [r"大模型|大语言模型|LLM"],
        "keywords": ["OpenAI", "Claude", "DeepSeek", "Gemini", "Llama"],
    },
    {
        "name": "AI应用与工具",
        "max_results": 5,
        "required_patterns": [r"AI|人工智能", r"应用|工具|产品|框架"],
        "keywords": ["RAG", "检索增强", "知识库", "Agent评测", "AI Agent基准", "Copilot", "代码生成", "LangChain", "Embedding", "Prompt"],
    },
    {
        "name": "AI基础设施",
        "max_results": 2,
        "required_patterns": [r"AI|计算", r"GPU|芯片|算力"],
        "keywords": ["NVIDIA", "CUDA", "TPU", "Hugging Face", "分布式训练"],
    },
    {
        "name": "机器学习前沿",
        "max_results": 2,
        "required_patterns": [],
        "keywords": ["计算机视觉", "NLP", "多模态", "生成式AI", "Diffusion", "NeRF"],
    },
    {
        "name": "AI落地应用",
        "max_results": 2,
        "required_patterns": [r"落地|实现|部署|应用案例"],
        "keywords": ["自动驾驶", "具身智能", "机器人", "医疗AI", "AI编程"],
    },
]


def main():
    db = SessionLocal()
    try:
        try:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE article_domains ADD COLUMN max_results INTEGER DEFAULT 3"))
                conn.commit()
            print("ALTER TABLE article_domains: 已添加 max_results 列")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ALTER TABLE: max_results 列已存在，跳过")
            else:
                raise

        db.query(ArticleKeyword).delete()
        db.query(ArticleDomain).delete()
        db.commit()
        print("已清空 article_keywords 与 article_domains")

        for d in DOMAINS:
            domain = ArticleDomain(
                name=d["name"],
                enabled=True,
                max_results=d["max_results"],
            )
            db.add(domain)
            db.flush()
            for pattern in d["required_patterns"]:
                kw = ArticleKeyword(
                    domain_id=domain.id,
                    keyword_type="positive",
                    keyword_text=pattern,
                    is_regex=True,
                    is_required=True,
                )
                db.add(kw)
            for kw_text in d["keywords"]:
                kw = ArticleKeyword(
                    domain_id=domain.id,
                    keyword_type="positive",
                    keyword_text=kw_text,
                    is_regex=False,
                    is_required=False,
                )
                db.add(kw)
            print(f"  领域: {d['name']} max_results={d['max_results']} 必须词={len(d['required_patterns'])} 关键词={len(d['keywords'])}")
        db.commit()
        print("seed_domain_keywords 完成")
    finally:
        db.close()


if __name__ == "__main__":
    main()
