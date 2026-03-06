# coding=utf-8
"""
独立 Scheduler 进程入口

与 Web 进程分离，避免多 worker 重复执行定时任务。
通过轮询数据库感知 rss_schedule 配置变更，无需重启即可生效。
"""
import json
import logging
import signal
import sys
import time

from app.core.config import settings
from app.core.database import get_db_context
from app.models.config import AppConfig
from app.services import scheduler_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 60  # 每隔 60 秒检查一次配置变更


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


def main():
    cron = _get_cron_from_db()
    logger.info("[scheduler] 启动，cron=%s", cron)
    scheduler_service.init_scheduler(cron)
    current_cron = cron

    def _shutdown(signum, frame):
        logger.info("[scheduler] 收到退出信号，关闭中...")
        scheduler_service.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    while True:
        time.sleep(POLL_INTERVAL)
        try:
            new_cron = _get_cron_from_db()
            if new_cron != current_cron:
                logger.info("[scheduler] 检测到 cron 变更: %s -> %s", current_cron, new_cron)
                scheduler_service.reschedule(new_cron)
                current_cron = new_cron
        except Exception as e:
            logger.warning("[scheduler] 配置轮询失败: %s", e)


if __name__ == "__main__":
    main()
