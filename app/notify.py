"""通知推送：可选，配了 NOTIFY_WEBHOOK 才生效。

兼容常见自托管通知服务（ntfy / Bark / 企业微信机器人 / 自建 webhook）：
统一 POST JSON {"title":..., "message":..., "text": "<title>\\n<message>"}。
"""
from __future__ import annotations

import logging

import httpx

from .config import settings

logger = logging.getLogger(__name__)


async def notify(title: str, message: str) -> None:
    url = settings.notify_webhook
    if not url:
        return
    payload = {"title": title, "message": message, "text": f"{title}\n{message}"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            await client.post(url, json=payload)
    except Exception as exc:  # 通知失败不能影响主流程
        logger.warning("通知推送失败：%s", exc)
