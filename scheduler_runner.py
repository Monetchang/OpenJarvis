# coding=utf-8
"""
独立 Scheduler 进程入口

每 30 秒轮询一次：用 croniter 判断今天的推送时间是否已到，避免依赖 APScheduler 后台线程。
"""
import json
import logging
import signal
import sys
import threading
import time
from datetime import datetime, timedelta

import pytz
from croniter import croniter

from app.core.config import settings
from app.core.database import get_db_context
from app.models.config import AppConfig
from app.services.scheduler_service import run_digest_job, run_fetch_only_job

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # 每 30 秒检查一次


def _get_cron_from_db() -> str:
    try:
        with get_db_context() as db:
            cfg = db.query(AppConfig).filter(AppConfig.key == "rss_schedule").first()
            if cfg and cfg.value:
                try:
                    return json.loads(cfg.value)
                except (json.JSONDecodeError, TypeError):
                    return cfg.value
    except Exception as e:
        logger.warning("[scheduler] 读取 DB 配置失败，使用默认值: %s", e)
    return settings.RSS_SCHEDULE


def _get_tz():
    return pytz.timezone(getattr(settings, "TIMEZONE", "Asia/Shanghai"))


def _todays_fire_time(cron_expr: str) -> datetime | None:
    """返回今天 cron 的触发时间，如果今天没有则返回 None。"""
    tz = _get_tz()
    now = datetime.now(tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    it = croniter(cron_expr, today_start - timedelta(seconds=1))
    fire = it.get_next(datetime)
    if fire.date() == now.date():
        return fire
    return None


def _run_digest():
    try:
        result = run_digest_job(force_fetch=True, skip_when_no_fetch=False)
        if not result["success"]:
            logger.info("[scheduler] 无可用文章，跳过推送")
        else:
            logger.info("[scheduler] 已推送到 %d 个邮箱", result.get("sent", 0))
    except Exception:
        logger.exception("[scheduler] 推送任务异常")


def main():
    cron = _get_cron_from_db()
    logger.info("[scheduler] 启动，cron=%s", cron)

    tz = _get_tz()
    now = datetime.now(tz)
    last_run_date = None

    fire_time = _todays_fire_time(cron)
    if fire_time and now >= fire_time:
        logger.info("[scheduler] 检测到今天推送时间已过（%s），立即补跑", fire_time.strftime("%H:%M"))
        last_run_date = now.date()
        threading.Thread(target=_run_digest, daemon=True).start()
    elif getattr(settings, "STARTUP_PREFETCH_ENABLED", True):
        threading.Thread(target=run_fetch_only_job, daemon=True).start()

    def _shutdown(signum, frame):
        logger.info("[scheduler] 收到退出信号，关闭中...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    current_cron = cron

    while True:
        time.sleep(POLL_INTERVAL)

        try:
            new_cron = _get_cron_from_db()
            if new_cron != current_cron:
                logger.info("[scheduler] 检测到 cron 变更: %s -> %s", current_cron, new_cron)
                current_cron = new_cron
                cron = new_cron
        except Exception as e:
            logger.warning("[scheduler] 配置轮询失败: %s", e)

        tz = _get_tz()
        now = datetime.now(tz)
        fire_time = _todays_fire_time(cron)

        if fire_time and now >= fire_time and last_run_date != now.date():
            logger.info("[scheduler] 触发推送，cron=%s fire=%s", cron, fire_time.strftime("%H:%M"))
            last_run_date = now.date()
            threading.Thread(target=_run_digest, daemon=True).start()


if __name__ == "__main__":
    main()
