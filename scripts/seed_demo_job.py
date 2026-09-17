"""给实拍工装灌一条演示用的打印任务（含扣重流水）。

为什么需要它：mock 模式只造打印机和料盘，不造打印任务 —— 打印记录页是空的，
「查看料盘 / 更改料盘」这两个按钮在真浏览器里根本没东西可点。
这个脚本补一条任务 + 一条扣重流水，让实拍断言能真的点下去。

只跑在实拍用的临时库上（DATA_DIR 指向 data/_shotui），不碰生产数据。
幂等：已经灌过就跳过。

运行： BAMBU_MOCK=1 DATA_DIR=<shotui> python scripts/seed_demo_job.py
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("BAMBU_MOCK", "1")

from sqlmodel import select  # noqa: E402

from app.core.deduction import usage_cost  # noqa: E402
from app.db import init_db, session_scope  # noqa: E402
from app.models import PrintJob, Spool, UsageRecord  # noqa: E402

JOB_TITLE = "演示打印任务"
SPOOL_NAME = "演示料盘"


def main() -> int:
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
        )
        session.add(job)
        session.commit()
        session.refresh(job)

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
