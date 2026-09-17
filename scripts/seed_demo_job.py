"""给实拍工装灌一条演示用的打印任务（含扣重流水与一张成果图）。

为什么需要它：mock 模式只造打印机和料盘，不造打印任务 —— 打印记录页是空的，
「查看料盘 / 更改料盘」这两个按钮在真浏览器里根本没东西可点。
这个脚本补一条任务 + 一条扣重流水，让实拍断言能真的点下去。

成果图也在这里造假：真图是拓竹云的盘面预览图（OSS 预签名，30 分钟过期），
工装里没有云端可用，就在本地 covers/ 下写一张纯色 PNG 并把 cover_file 指过去，
这样实拍能验到的是「界面真的把图渲染出来了、尺寸没塌」，
而不只是「无图时的占位文案是对的」。

只跑在实拍用的临时库上（DATA_DIR 指向 data/_shotui），不碰生产数据。
**这条是靠下面的守卫强制的**：DATA_DIR 没设、或指到默认的 ./data，
脚本会直接退出而不是照写 —— 早前就发生过一次「以为灌到临时库、
其实落进了默认库」的静默事故（DATA_DIR 传了个 Git-Bash 风格 `/c/...` 路径，
Windows 的 Python 认不出来，`os.getenv` 拿到值但 resolve 成了别的地方）。
幂等：已经灌过就跳过。

运行： DATA_DIR=<绝对 Windows 路径> BAMBU_MOCK=1 python scripts/seed_demo_job.py
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("BAMBU_MOCK", "1")

from sqlmodel import select  # noqa: E402

from app.core.covers import cover_dir  # noqa: E402
from app.core.deduction import usage_cost  # noqa: E402
from app.db import init_db, session_scope  # noqa: E402
from app.models import PrintJob, Spool, UsageRecord  # noqa: E402

JOB_TITLE = "演示打印任务"
SPOOL_NAME = "演示料盘"
COVER_W, COVER_H = 320, 240


def _make_plate_png() -> bytes:
    """造一张 320×240 的示意「盘面预览图」：深灰底 + 中间一个浅色圆。

    不引 Pillow（部署镜像里没有），手写最小 PNG：IHDR + IDAT + IEND，
    像素用 filter 0 逐行拼。画个圆是为了让「图片确实被解码渲染」看得出来，
    不是一块纯色（纯色图如果没加载出来，背景色也能冒充）。
    """
    cx, cy, r = COVER_W / 2, COVER_H / 2, min(COVER_W, COVER_H) * 0.35
    raw = bytearray()
    for y in range(COVER_H):
        raw.append(0)                      # 每行的 filter 字节
        for x in range(COVER_W):
            inside = ((x - cx) ** 2 + (y - cy) ** 2) <= r * r
            raw += bytes((214, 214, 214) if inside else (58, 58, 62))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", COVER_W, COVER_H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))


def _guard_data_dir() -> None:
    """拒绝在「看起来像生产库」的 DATA_DIR 上跑。

    这个脚本会写打印任务、扣重流水和成果图，全是真数据。
    早前踩过一次：`DATA_DIR=$(pwd)/data/_x` 在 Git-Bash 里展开成 `/c/Users/...`，
    Windows 的 Python 认不出这个路径，于是 `settings.data_dir` 回落到默认 `./data`，
    脚本照写不误、还打印了「已灌入」——数据落进了不该落的地方而没人发现。
    """
    from app.config import settings
    raw = (os.getenv("DATA_DIR") or "").strip()
    if not raw:
        sys.exit("拒绝执行：必须显式设置 DATA_DIR 指向临时库，不能落到默认 ./data。\n"
                 "  例：DATA_DIR=C:/Users/me/proj/data/_shotui")
    # Git-Bash 风格 `/c/Users/...` 在 Windows Python 眼里是「当前盘根下的 c/Users/...」，
    # 会被 resolve 成 `C:\c\Users\...`（凭空造出一棵 C:\c 目录树）。
    # 这类路径必须直接拒掉，不能让它「跑成功了」却落在别处。
    if raw.startswith("/"):
        sys.exit(f"拒绝执行：DATA_DIR 是 POSIX 风格路径，Windows 上会被解析成盘根下的相对路径。\n"
                 f"  收到：{raw}\n"
                 f"  应为：C:/Users/... （盘符开头）")
    resolved = str(settings.data_dir).replace("\\", "/").rstrip("/")
    import pathlib
    default = str(pathlib.Path(ROOT) / "data").replace("\\", "/").rstrip("/")
    if resolved == default or not resolved.lower().endswith(("_shotui", "_seedtest", "_tmp")):
        sys.exit(f"拒绝执行：DATA_DIR 看着像生产库，不往里写。\n"
                 f"  实际解析到：{resolved}\n"
                 f"  只允许以 _shotui / _seedtest / _tmp 结尾的临时目录。")


def main() -> int:
    _guard_data_dir()
    init_db()
    with session_scope() as session:
        if session.exec(select(PrintJob).where(PrintJob.title == JOB_TITLE)).first():
            print("演示任务已存在，跳过")
            return 0

        spool = session.exec(select(Spool).where(Spool.name == SPOOL_NAME)).first()
        if spool is None:
            spool = Spool(
                name=SPOOL_NAME, brand="Bambu Lab", material="PLA",
                color_name="黑", color_hex="#1A1A1A",
                spool_weight=250.0, initial_weight=1000.0,
                remaining_weight=800.0, used_weight=200.0, price=99.0,
            )
            session.add(spool)
            session.commit()
            session.refresh(spool)

        weight = 120.0
        filaments = [{
            "index": 0, "filament_id": "GFA00", "material": spool.material,
            "color": spool.color_hex, "weight_g": weight,
            "ams_id": 0, "tray_id": 0, "slot_label": "AMS A · 槽位 1",
            "spool_id": spool.id, "spool_name": spool.name,
            "match_strategy": "演示数据", "deducted_g": weight, "deducted": True,
            "cost": round(usage_cost(spool, weight), 2),
        }]
        now = _dt.datetime.utcnow()
        job = PrintJob(
            printer_id=1, serial="DEMO000000000", task_id="demo-1",
            title=JOB_TITLE, status="finished",
            started_at=now - _dt.timedelta(hours=1), finished_at=now,
            duration_seconds=3600, progress_at_end=100.0,
            total_weight_g=weight, source="cloud_task",
            deduction_applied=True, note="实拍工装的演示数据",
            filaments_json=json.dumps(filaments, ensure_ascii=False),
            # cover_url 留空：真实场景里它是 30 分钟就过期的 OSS 预签名链接，
            # 在这里填一个假链接会让界面看起来「本该能取云端图」，误导后来的人。
            cover_url="",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        # 真的写一张图到 covers/，并把 cover_file 指过去 —— 界面才会走「有图」那条分支
        name = f"{job.id}.png"
        (cover_dir() / name).write_bytes(_make_plate_png())
        job.cover_file = name
        session.add(job)
        session.commit()

        # 「更改料盘」按钮要有这条流水才可用（它调 /api/usages/{id}/move）
        session.add(UsageRecord(
            spool_id=spool.id, printer_id=1, job_id=job.id, filament_index=0,
            weight_g=weight, source="cloud_task", note="演示扣重",
        ))
        session.commit()
    print(f"已灌入演示任务（{JOB_TITLE}）与一条扣重流水")
    return 0


if __name__ == "__main__":
    sys.exit(main())
