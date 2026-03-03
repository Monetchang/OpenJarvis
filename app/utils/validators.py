# coding=utf-8
"""
验证器工具
"""
from croniter import croniter


def validate_cron_expression(cron_expr: str) -> bool:
    """
    验证 cron 表达式是否有效

    Args:
        cron_expr: cron 表达式字符串

    Returns:
        bool: 是否有效
    """
    try:
        croniter(cron_expr)
        return True
    except Exception:
        return False


def validate_url(url: str) -> bool:
    """
    验证 URL 是否有效

    Args:
        url: URL 字符串

    Returns:
        bool: 是否有效
    """
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    import re
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

