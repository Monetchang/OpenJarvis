#!/usr/bin/env python3
# coding=utf-8
"""
导入关键词规则到数据库
"""
import re
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.filter import ArticleDomain, ArticleKeyword


def parse_keyword_line(line: str):
    """
    解析关键词行
    
    返回: (keyword_text, is_regex, is_required, keyword_type, alias, max_results)
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    # 提取限制数量 @数字
    max_results = None
    match = re.search(r'@(\d+)', line)
    if match:
        max_results = int(match.group(1))
        line = re.sub(r'@\d+', '', line).strip()
    
    # 检查是否为必须词 (+)
    is_required = False
    if line.startswith('+'):
        is_required = True
        line = line[1:].strip()
    
    # 检查是否为过滤词 (!)
    keyword_type = 'positive'
    if line.startswith('!'):
        keyword_type = 'negative'
        line = line[1:].strip()
    
    # 检查别名 (=> 别名)
    alias = None
    if ' => ' in line:
        parts = line.split(' => ', 1)
        line = parts[0].strip()
        alias = parts[1].strip()
    
    # 检查是否为正则表达式 (/.../)
    is_regex = False
    keyword_text = line
    if line.startswith('/') and line.endswith('/'):
        is_regex = True
        keyword_text = line[1:-1]  # 去掉首尾的 /
    elif line.startswith('/'):
        # 可能是多行正则，但这里简化处理
        is_regex = True
        keyword_text = line[1:]
    
    return {
        'keyword_text': keyword_text,
        'is_regex': is_regex,
        'is_required': is_required,
        'keyword_type': keyword_type,
        'alias': alias,
        'max_results': max_results
    }


def parse_keyword_groups(content: str):
    """
    解析关键词组
    
    返回: [(group_name, keywords, max_results), ...]
    """
    groups = []
    current_group = None
    current_keywords = []
    current_max_results = None
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # 跳过注释和空行
        if not line or line.startswith('#'):
            continue
        
        # 检查组名 [组名]
        if line.startswith('[') and line.endswith(']'):
            # 保存上一个组
            if current_group:
                groups.append((current_group, current_keywords, current_max_results))
            
            # 开始新组
            current_group = line[1:-1]
            current_keywords = []
            current_max_results = None
            continue
        
        # 解析关键词行
        keyword_data = parse_keyword_line(line)
        if keyword_data:
            # 如果这行有 max_results，应用到整个组
            if keyword_data['max_results'] is not None:
                current_max_results = keyword_data['max_results']
                keyword_data['max_results'] = None  # 不在单个关键词上设置
            
            current_keywords.append(keyword_data)
    
    # 保存最后一个组
    if current_group:
        groups.append((current_group, current_keywords, current_max_results))
    
    return groups


# 领域名称映射
DOMAIN_MAPPING = {
    'AI模型架构与算法': 'AI模型架构与算法创新',
    'AI大模型技术': '大模型训练与推理技术',
    'AI应用与工具': 'RAG技术与知识库构建',  # RAG相关关键词
    'AI应用与工具_Agent': 'AI Agent开发与评测',  # Agent相关关键词（特殊处理）
    'AI基础设施': 'AI基础设施与工具链',
    '机器学习前沿': '机器学习前沿研究',
    'AI落地应用': 'AI工程实践与落地应用',
}

# Agent相关关键词（需要映射到AI Agent开发与评测领域）
AGENT_KEYWORDS = {
    'Agent', '智能体', 'Agent评测', 'AI Agent基准', 
    '多智能体', 'Multi-Agent', 'Copilot', '代码生成', '自动化'
}


def _import_single_keyword(db: Session, domain: ArticleDomain, kw_data: dict) -> int:
    """导入单个关键词，返回导入数量（0或1）"""
    # 检查是否已存在
    existing = db.query(ArticleKeyword).filter(
        ArticleKeyword.domain_id == domain.id,
        ArticleKeyword.keyword_text == kw_data['keyword_text'],
        ArticleKeyword.keyword_type == kw_data['keyword_type']
    ).first()
    
    if existing:
        print(f"  跳过已存在: {kw_data['keyword_text']}")
        return 0
    
    keyword = ArticleKeyword(
        domain_id=domain.id,
        keyword_type=kw_data['keyword_type'],
        keyword_text=kw_data['keyword_text'],
        is_regex=kw_data['is_regex'],
        is_required=kw_data['is_required'],
        alias=kw_data['alias'],
        priority=0,
        max_results=kw_data['max_results']
    )
    
    db.add(keyword)
    kw_type = '正则' if kw_data['is_regex'] else '普通'
    kw_category = kw_data['keyword_type']
    required_mark = ' [必须]' if kw_data['is_required'] else ''
    max_mark = f' [限制{kw_data["max_results"]}条]' if kw_data['max_results'] else ''
    print(f"  + {kw_data['keyword_text']} ({kw_type}, {kw_category}{required_mark}{max_mark})")
    return 1


def import_keywords(db: Session):
    """导入关键词到数据库"""
    
    # 关键词规则内容
    keyword_rules = """
[AI模型架构与算法]
+/模型|算法|架构/
+/AI|人工智能|机器学习|深度学习/
Transformer
/MoE|混合专家/
注意力机制
/RLHF|强化学习/
训练
推理
微调
/LoRA|适配器/
量化
蒸馏
!股价
!融资
!市值
@3

[AI大模型技术]
+/大模型|大语言模型|LLM/
OpenAI
DeepSeek
深度求索
Claude
Anthropic
/GPT-\d+|ChatGPT/
Gemini
Llama
Mistral
智谱
文心
通义
Kimi
零一万物
!股价
!融资
!上市
@3

[AI应用与工具]
+/AI|人工智能/
+/应用|工具|产品|平台|框架/
RAG
检索增强
知识库
Agent
智能体
Agent评测
AI Agent基准
/多智能体|Multi-Agent/
Copilot
代码生成
自动化
LangChain
向量数据库
Embedding
/评测|基准测试|Benchmark/
Prompt
提示词
!娱乐
!游戏
!股价
@5

[AI基础设施]
+/AI|人工智能|计算/
/GPU|芯片|算力|数据中心/
NVIDIA
英伟达
CUDA
TPU
Hugging Face
模型部署
推理服务
分布式训练
!股价
!涨停
@2

[机器学习前沿]
计算机视觉
自然语言处理
/NLP|语音识别/
多模态
生成式AI
Diffusion
/GAN|对抗网络/
NeRF
3D重建
!应用场景
!商业化
@2

[AI落地应用]
+/落地|实现|部署|应用案例/
自动驾驶
具身智能
机器人
医疗AI
代码助手
AI编程
智能客服
!概念
!炒作
@2
"""
    
    groups = parse_keyword_groups(keyword_rules)
    
    # 获取所有领域
    domains = db.query(ArticleDomain).all()
    domain_map = {domain.name: domain for domain in domains}
    
    imported_count = 0
    
    for group_name, keywords, group_max_results in groups:
        # 特殊处理：AI应用与工具组需要拆分
        if group_name == 'AI应用与工具':
            # 分为两个领域：RAG 和 Agent
            rag_domain_name = DOMAIN_MAPPING.get('AI应用与工具')
            agent_domain_name = DOMAIN_MAPPING.get('AI应用与工具_Agent')
            
            rag_domain = domain_map.get(rag_domain_name) if rag_domain_name else None
            agent_domain = domain_map.get(agent_domain_name) if agent_domain_name else None
            
            if not rag_domain:
                print(f"警告: 数据库中不存在领域: {rag_domain_name}")
                continue
            
            # 分离关键词
            rag_keywords = []
            agent_keywords = []
            
            for kw_data in keywords:
                kw_text = kw_data['keyword_text'].lower()
                is_agent = False
                
                # 检查是否为Agent相关关键词
                for agent_kw in AGENT_KEYWORDS:
                    if agent_kw.lower() in kw_text or kw_text in agent_kw.lower():
                        is_agent = True
                        break
                
                # 检查正则表达式是否匹配Agent相关
                if kw_data['is_regex']:
                    for agent_kw in AGENT_KEYWORDS:
                        if agent_kw.lower() in kw_data['keyword_text']:
                            is_agent = True
                            break
                
                if is_agent and agent_domain:
                    agent_keywords.append(kw_data)
                else:
                    rag_keywords.append(kw_data)
            
            # 导入RAG关键词
            print(f"\n处理领域: {rag_domain_name} (ID: {rag_domain.id})")
            print(f"  关键词数量: {len(rag_keywords)}")
            for idx, kw_data in enumerate(rag_keywords):
                if idx == 0 and group_max_results is not None:
                    kw_data['max_results'] = group_max_results
                imported_count += _import_single_keyword(db, rag_domain, kw_data)
            
            # 导入Agent关键词
            if agent_domain and agent_keywords:
                print(f"\n处理领域: {agent_domain_name} (ID: {agent_domain.id})")
                print(f"  关键词数量: {len(agent_keywords)}")
                for idx, kw_data in enumerate(agent_keywords):
                    if idx == 0 and group_max_results is not None:
                        kw_data['max_results'] = group_max_results
                    imported_count += _import_single_keyword(db, agent_domain, kw_data)
            
            continue
        
        # 普通组处理
        domain_name = DOMAIN_MAPPING.get(group_name)
        if not domain_name:
            print(f"警告: 未找到领域映射: {group_name}")
            continue
        
        domain = domain_map.get(domain_name)
        if not domain:
            print(f"警告: 数据库中不存在领域: {domain_name}")
            continue
        
        print(f"\n处理领域: {domain_name} (ID: {domain.id})")
        print(f"  关键词数量: {len(keywords)}")
        
        # 导入关键词
        for idx, kw_data in enumerate(keywords):
            # 如果组级别有 max_results，应用到第一个关键词
            if idx == 0 and group_max_results is not None:
                kw_data['max_results'] = group_max_results
            
            imported_count += _import_single_keyword(db, domain, kw_data)
    
    db.commit()
    print(f"\n导入完成！共导入 {imported_count} 个关键词规则")


if __name__ == '__main__':
    db = SessionLocal()
    try:
        import_keywords(db)
    except Exception as e:
        db.rollback()
        print(f"错误: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

