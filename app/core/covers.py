"""打印成果图：云端任务 cover 的抓取与本地缓存。

**为什么必须在结算那一刻就抓下来**：拓竹云任务接口给的 `cover` 是阿里云 OSS 的
**预签名 URL**（`X-Amz-Expires=1800`），**30 分钟就失效**。任务列表里存的 URL 过一会儿
再取就是 403，所以只能在轮询到任务记录时（轮询周期默认 60 秒，远小于 30 分钟）
把字节抓下来存成本地文件，界面再读本地文件。

**它是什么图**：真实数据里这些 URL 的文件名是 `plate_1.png` / `plate_12.png`，
也就是**切片时的盘面预览图**，不是打印机摄像头拍的最后一张画面——摄像头画面云端不提供
（要拿只能走局域网模式的摄像头流）。界面上要如实写清这个口径，别让人以为是实拍。
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

COVER_DIRNAME = "covers"
_TIMEOUT = 10.0
_MIN_BYTES = 512            # 比这还小的多半是错误页或占位图，别存
_ALLOWED = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def cover_dir() -> Path:
    """成果图目录（在 DATA_DIR 下，跟着数据卷一起持久化）。"""
    d = settings.data_dir / COVER_DIRNAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _suffix_of(url: str) -> str:
    """从 URL 路径推断扩展名；认不出来就按 png 存（真实数据都是 png）。"""
    stem = url.split("?", 1)[0].lower()
    for suf in _ALLOWED:
        if stem.endswith(suf):
            return suf
    return ".png"


def save_cover(url: str, job_id: int) -> str:
    """把云端封面抓下来存成 `<job_id><后缀>`，返回文件名；没抓到返回空串。

    任何异常都在这里吞掉并记日志——封面只是锦上添花，
    **绝不能让抓图失败影响扣重**（扣重才是主业）。
    """
    if not url or not job_id:
        return ""
    try:
        resp = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
        ctype = (resp.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
        if resp.status_code != 200 or not ctype.startswith("image/"):
            logger.info("打印成果图跳过：HTTP %s / %s", resp.status_code, ctype or "无 content-type")
            return ""
        if len(resp.content) < _MIN_BYTES:
            logger.info("打印成果图跳过：只有 %d 字节，多半不是正经图片", len(resp.content))
            return ""
        suffix = _suffix_of(url)
        name = f"{job_id}{suffix}"
        path = cover_dir() / name
        path.write_bytes(resp.content)
        logger.info("打印成果图已保存：任务 %s → %s（%d 字节）", job_id, path, len(resp.content))
        return name
    except Exception as exc:  # pragma: no cover - 网络异常种类太多，统一兜住
        logger.warning("打印成果图抓取失败（不影响扣重）：%s", exc)
        return ""


def cover_media_type(name: str) -> str:
    for suf, mime in _ALLOWED.items():
        if name.lower().endswith(suf):
            return mime
    return "image/png"
