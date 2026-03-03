# coding=utf-8
"""手动触发邮件推送：抓取 -> 生成选题 -> 推送到订阅邮箱"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.scheduler_service import run_digest_job

if __name__ == "__main__":
    print("正在执行: 抓取RSS -> 生成选题 -> 邮件推送...")
    result = run_digest_job(force_fetch=True, skip_when_no_fetch=False)
    if result["success"]:
        print(f"✅ 完成: 抓取 {result['fetched']} 篇, 推送 {result['articles']} 篇文章, {result['topics']} 个选题, 已发送至 {result['sent']} 个邮箱")
    else:
        print(f"❌ 失败: {result}")
