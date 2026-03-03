# coding=utf-8
"""
时间工具模块

提供统一的时间处理函数
"""

import logging
from datetime import datetime
from typing import Optional

import pytz

logger = logging.getLogger(__name__)

# 默认时区常量
DEFAULT_TIMEZONE = "Asia/Shanghai"


def get_configured_time(timezone: str = DEFAULT_TIMEZONE) -> datetime:
    """
    获取配置时区的当前时间

    Args:
        timezone: 时区名称，如 'Asia/Shanghai', 'America/Los_Angeles'

    Returns:
        带时区信息的当前时间
    """
    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        logger.warning("未知时区 '%s'，使用默认时区 %s", timezone, DEFAULT_TIMEZONE)
        tz = pytz.timezone(DEFAULT_TIMEZONE)
    return datetime.now(tz)


def is_within_days(
    iso_time: str,
    max_days: int,
    timezone: str = DEFAULT_TIMEZONE,
) -> bool:
    """
    检查 ISO 格式时间是否在指定天数内

    用于 RSS 文章新鲜度过滤，判断文章发布时间是否超过指定天数。

    Args:
        iso_time: ISO 格式时间字符串（如 '2025-12-29T00:20:00' 或带时区）
        max_days: 最大天数（文章发布时间距今不超过此天数则返回 True）
            - max_days > 0: 正常过滤，保留 N 天内的文章
            - max_days <= 0: 禁用过滤，保留所有文章
        timezone: 时区名称（用于获取当前时间）

    Returns:
        True 如果时间在指定天数内（应保留），False 如果超过指定天数（应过滤）
        如果无法解析时间，返回 True（保留文章）
    """
    # 无时间戳或禁用过滤时，保留文章
    if not iso_time:
        return True
    if max_days <= 0:
        return True  # max_days=0 表示禁用过滤

    try:
        dt = None

        # 尝试解析带时区的格式
        if "+" in iso_time or iso_time.endswith("Z"):
            iso_time_normalized = iso_time.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(iso_time_normalized)
            except ValueError:
                pass

        # 尝试解析不带时区的格式（假设为 UTC）
        if dt is None:
            try:
                if "T" in iso_time:
                    dt = datetime.fromisoformat(iso_time.replace("T", " ").split(".")[0])
                else:
                    dt = datetime.fromisoformat(iso_time.split(".")[0])
                dt = pytz.UTC.localize(dt)
            except ValueError:
                pass

        if dt is None:
            # 无法解析时间，保留文章
            return True

        # 获取当前时间（配置的时区，带时区信息）
        now = get_configured_time(timezone)

        # 计算时间差（两个带时区的 datetime 相减会自动处理时区差异）
        diff = now - dt
        days_diff = diff.total_seconds() / (24 * 60 * 60)

        return days_diff <= max_days

    except Exception:
        # 出错时保留文章
        return True


def parse_published_date(published_at: str) -> Optional[datetime]:
    """
    解析 published_at 字符串为 datetime 对象
    
    Args:
        published_at: ISO 格式时间字符串
        
    Returns:
        datetime 对象，如果解析失败返回 None
    """
    if not published_at:
        return None
    
    try:
        # 尝试解析带时区的格式
        if "+" in published_at or published_at.endswith("Z"):
            published_at_normalized = published_at.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(published_at_normalized)
            except ValueError:
                pass
        
        # 尝试解析不带时区的格式
        if "T" in published_at:
            dt = datetime.fromisoformat(published_at.replace("T", " ").split(".")[0])
        else:
            dt = datetime.fromisoformat(published_at.split(".")[0])
        
        # 如果没有时区信息，假设为 UTC
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        
        return dt
    except (ValueError, TypeError):
        return None


def is_today(published_at: str, timezone: str = DEFAULT_TIMEZONE) -> bool:
    """
    判断 published_at 是否为今天
    
    Args:
        published_at: ISO 格式时间字符串
        timezone: 时区名称
        
    Returns:
        True 如果是今天，False 如果不是或无法解析
    """
    dt = parse_published_date(published_at)
    if dt is None:
        return False
    
    # 获取今天的日期（配置的时区）
    now = get_configured_time(timezone)
    today = now.date()
    
    # 将 published_at 转换为配置时区的日期
    if dt.tzinfo:
        # 转换为配置时区
        tz = pytz.timezone(timezone)
        dt_local = dt.astimezone(tz)
    else:
        # 如果没有时区信息，假设为 UTC 并转换
        tz = pytz.timezone(timezone)
        dt_local = pytz.UTC.localize(dt).astimezone(tz)
    
    return dt_local.date() == today

