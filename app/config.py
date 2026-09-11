"""运行配置：全部来自环境变量，容器化友好。"""
from __future__ import annotations

import os
from pathlib import Path


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, "")).strip())
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, "")).strip())
    except (TypeError, ValueError):
        return default


class Settings:
    def __init__(self) -> None:
        self.data_dir = Path(os.getenv("DATA_DIR", "./data")).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.data_dir / "bambu_spool.db"
        self.database_url = os.getenv("DATABASE_URL") or f"sqlite:///{self.db_path.as_posix()}"
        # 加密拓竹账号密码用的密钥文件
        self.secret_key_path = self.data_dir / "secret.key"

        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = _int("PORT", 8971)

        # 访问口令。留空表示不鉴权（仅建议在内网使用）
        self.app_password = os.getenv("APP_PASSWORD", "").strip()

        # 拓竹账号区域：china / global。决定 API 域名与 MQTT broker。
        self.region = os.getenv("BAMBU_REGION", "china").strip().lower()

        # 模拟模式：无需真实打印机与账号即可完整体验流程
        self.mock_mode = _bool("BAMBU_MOCK", False)

        # 云 MQTT
        self.mqtt_keepalive = _int("BAMBU_MQTT_KEEPALIVE", 30)
        self.reconnect_min_delay = _float("BAMBU_RECONNECT_MIN", 3.0)
        self.reconnect_max_delay = _float("BAMBU_RECONNECT_MAX", 120.0)

        # 任务历史轮询间隔（秒）。拓竹任务记录通常在打印结束后几十秒内出现。
        self.task_poll_interval = _int("TASK_POLL_INTERVAL", 60)
        # 一个任务结束后，最多回查多少分钟内的云端任务记录
        self.task_match_window_minutes = _int("TASK_MATCH_WINDOW_MINUTES", 20)

        # 自动扣重
        self.auto_deduct = _bool("AUTO_DEDUCT", True)
        self.deduct_on_failure = _bool("DEDUCT_ON_FAILURE", True)
        # 进度低于该百分比视为误报任务，不生成记录
        self.min_progress_to_record = _float("MIN_PROGRESS_TO_RECORD", 1.0)

        # 通知 webhook（可选）：收到 POST {"title":..., "message":...}
        self.notify_webhook = os.getenv("NOTIFY_WEBHOOK", "").strip()

        # 令牌剩余不足多少小时时尝试自动重新登录
        self.token_renew_before_hours = _float("TOKEN_RENEW_BEFORE_HOURS", 3.0)


settings = Settings()
