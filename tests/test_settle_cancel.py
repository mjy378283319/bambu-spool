"""中途中断任务的扣重规则自测。

覆盖 1.0.37 起的行为：打印机按「停止」/掉线时只回 IDLE、不报 FAILED，
这类任务以前判成 cancelled 后一分不扣，料白吃了账面不动。现在按结束进度折算。

运行： python tests/test_settle_cancel.py
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ["BAMBU_MOCK"] = "1"
os.environ["DATA_DIR"] = os.path.join(ROOT, "data", "testcancel")

from sqlmodel import select  # noqa: E402

from app.cloud.mock import MockSource  # noqa: E402
from app.config import settings  # noqa: E402
from app.core.hub import hub  # noqa: E402
from app.db import init_db, session_scope  # noqa: E402
from app.models import PrintJob, Printer, SlotBinding, Spool, UsageRecord  # noqa: E402

SERIAL = "01S00A0000000000"
PASSED: list[str] = []
FAILED: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(label)
        print(f"  [通过] {label}")
    else:
        FAILED.append(label)
        print(f"  [失败] {label} {detail}")


def reset() -> None:
    data_dir = os.environ["DATA_DIR"]
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir, ignore_errors=True)
    os.makedirs(data_dir, exist_ok=True)
    init_db()


def seed() -> tuple[int, int, int]:
    with session_scope() as session:
        pr = session.exec(select(Printer)).first()
        if pr is None:
            raise RuntimeError("模拟设备未创建")
        a = Spool(
            name="PLA 黑", brand="Bambu Lab", material="PLA", color_name="黑色",
            color_hex="#1A1A1A", spool_weight=250.0, initial_weight=1000.0,
            remaining_weight=1000.0, tray_info_idx="GFA00",
        )
        b = Spool(
            name="PETG 蓝", brand="Bambu Lab", material="PETG", color_name="蓝色",
            color_hex="#1E88E5", spool_weight=250.0, initial_weight=1000.0,
            remaining_weight=1000.0, tray_info_idx="GFG02",
        )
        session.add(a)
        session.add(b)
        session.flush()
        session.add(SlotBinding(printer_id=pr.id, ams_id=0, tray_id=0, spool_id=a.id))
        session.add(SlotBinding(printer_id=pr.id, ams_id=0, tray_id=1, spool_id=b.id))
        return pr.id, a.id, b.id


def base_block(state: str = "IDLE", **overrides) -> dict:
    block = MockSource(SERIAL)._base()
    block["gcode_state"] = state
    block.update(overrides)
    return block


def cloud_task(task_id: int, title: str, start: datetime, total: float = 12.58) -> dict:
    """整份模型的用量：9.42 + 3.16 = 12.58 g（与进度无关，所以要靠进度折算）。"""
    return {
        "id": task_id,
        "title": title,
        "deviceId": SERIAL,
        "deviceModel": "P2S",
        "startTime": (start - timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endTime": (start + timedelta(minutes=22)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "weight": total,
        "length": 4185,
        "amsDetailMapping": [
            {"ams": 0, "filamentId": "GFA00", "filamentType": "PLA",
             "sourceColor": "1A1A1AFF", "targetColor": "1A1A1AFF", "weight": 9.42},
            {"ams": 1, "filamentId": "GFG02", "filamentType": "PETG",
             "sourceColor": "1E88E5FF", "targetColor": "1E88E5FF", "weight": 3.16},
        ],
    }


def spool_remaining(spool_id: int) -> float:
    with session_scope() as session:
        return session.get(Spool, spool_id).remaining_weight


async def main() -> int:
    print("拓竹耗材管家 · 中途中断任务扣重自测")
    reset()

    hub._loop = asyncio.get_running_loop()
    hub._ensure_mock_printer()
    hub._load_printers()
    printer_id, spool_a, spool_b = seed()

    print("\n1. 默认配置：中途停止也要扣")
    check("deduct_on_cancel 默认开启", settings.deduct_on_cancel is True, str(settings.deduct_on_cancel))

    started = datetime.utcnow()
    await hub._apply_payload(SERIAL, {"print": base_block()})
    await hub._apply_payload(SERIAL, {"print": base_block(
        "RUNNING", subtask_name="打一半停掉.stl", task_id="55550001", mc_percent=40)})
    check("任务已开始", printer_id in hub._open)

    # 用户按了停止：打印机只回 IDLE，不报 FAILED
    await hub._apply_payload(SERIAL, {"print": base_block(
        "IDLE", subtask_name="打一半停掉.stl", task_id="55550001", mc_percent=40)})

    with session_scope() as session:
        job = session.exec(
            select(PrintJob).where(PrintJob.task_id == "55550001")
        ).first()
    check("已生成打印记录", job is not None)
    check("状态判为已取消", job is not None and job.status == "cancelled",
          job.status if job else "-")
    check("结束进度记为 40%", job is not None and abs(job.progress_at_end - 40) < 0.01,
          str(job.progress_at_end if job else "-"))
    check("已进入待结算队列", job is not None and job.id in hub.pending_jobs())

    print("\n2. 按 40% 折算扣重（不是整份 12.58 g）")
    task = cloud_task(55550001, "打一半停掉.stl", started)

    async def fake_tasks():
        return [task]

    hub.fetch_cloud_tasks = fake_tasks  # type: ignore[assignment]
    result = await hub.settle_pending()

    with session_scope() as session:
        job = session.get(PrintJob, job.id)
        a = session.get(Spool, spool_a)
        b = session.get(Spool, spool_b)
        records = session.exec(
            select(UsageRecord).where(UsageRecord.job_id == job.id)
        ).all()

    check("结算成功 1 条", result.get("settled") == 1, str(result))
    check("标记为已扣重", job.deduction_applied)
    check("总扣减 5.03 g（12.58 × 40%）", abs(job.total_weight_g - 5.03) < 0.02,
          str(job.total_weight_g))
    check("黑色 PLA 扣 3.77 g", abs(a.remaining_weight - 996.23) < 0.02, str(a.remaining_weight))
    check("蓝色 PETG 扣 1.26 g", abs(b.remaining_weight - 998.74) < 0.02, str(b.remaining_weight))
    check("生成 2 条扣重流水", len(records) == 2, str(len(records)))

    filaments = json.loads(job.filaments_json)
    check("流水标注了折算依据",
          all("未完成任务按 40% 计" in f["match_strategy"] for f in filaments),
          str([f["match_strategy"] for f in filaments]))

    print("\n3. 失败任务仍按进度折算（回归）")
    a_before, b_before = a.remaining_weight, b.remaining_weight
    started2 = datetime.utcnow()
    await hub._apply_payload(SERIAL, {"print": base_block(
        "RUNNING", subtask_name="打到75失败.stl", task_id="55550002", mc_percent=75)})
    await hub._apply_payload(SERIAL, {"print": base_block(
        "FAILED", subtask_name="打到75失败.stl", task_id="55550002", mc_percent=75)})

    with session_scope() as session:
        job2 = session.exec(
            select(PrintJob).where(PrintJob.task_id == "55550002")
        ).first()
    check("失败任务进入待结算", job2 is not None and job2.id in hub.pending_jobs())

    task2 = cloud_task(55550002, "打到75失败.stl", started2)

    async def fake_tasks2():
        return [task2]

    hub.fetch_cloud_tasks = fake_tasks2  # type: ignore[assignment]
    await hub.settle_pending()

    with session_scope() as session:
        job2 = session.get(PrintJob, job2.id)
        a2 = session.get(Spool, spool_a)
        b2 = session.get(Spool, spool_b)
    check("失败任务总扣 9.44 g（12.58 × 75%）", abs(job2.total_weight_g - 9.44) < 0.02,
          str(job2.total_weight_g))
    check("A 盘累计扣到 7.07 g", abs(a2.remaining_weight - (a_before - 7.065)) < 0.02,
          str(a2.remaining_weight))
    check("B 盘累计扣到 2.37 g", abs(b2.remaining_weight - (b_before - 2.37)) < 0.02,
          str(b2.remaining_weight))

    print("\n4. 没有结束进度的老任务：不扣 0 g、留给手动补录")
    orphan = PrintJob(
        printer_id=printer_id, serial=SERIAL, title="老记录没有进度", status="cancelled",
        started_at=datetime.utcnow(), finished_at=datetime.utcnow(), progress_at_end=0,
    )
    with session_scope() as session:
        session.add(orphan)
        session.flush()
        orphan_id = orphan.id

    async def fake_tasks3():
        return []

    hub.fetch_cloud_tasks = fake_tasks3  # type: ignore[assignment]
    hub.retry_settle(orphan_id)
    await hub.settle_pending(force_job_id=orphan_id)

    with session_scope() as session:
        orphan = session.get(PrintJob, orphan_id)
    check("没有被标记成已扣重", orphan.deduction_applied is False)
    check("note 提示手动补录", "手动录入" in (orphan.note or ""), orphan.note)
    check("已移出待结算队列", orphan_id not in hub.pending_jobs())

    print("\n5. 关掉开关后，中途取消不扣（用户可自行选择）")
    settings.deduct_on_cancel = False
    try:
        a_before3 = spool_remaining(spool_a)
        started3 = datetime.utcnow()
        await hub._apply_payload(SERIAL, {"print": base_block(
            "RUNNING", subtask_name="关开关测试.stl", task_id="55550003", mc_percent=60)})
        await hub._apply_payload(SERIAL, {"print": base_block(
            "IDLE", subtask_name="关开关测试.stl", task_id="55550003", mc_percent=60)})

        with session_scope() as session:
            job3 = session.exec(
                select(PrintJob).where(PrintJob.task_id == "55550003")
            ).first()
        check("仍然生成任务记录", job3 is not None)
        check("但不进入待结算队列", job3 is not None and job3.id not in hub.pending_jobs())
        check("料盘克重未变", abs(spool_remaining(spool_a) - a_before3) < 0.01)
    finally:
        settings.deduct_on_cancel = True

    print("\n" + "─" * 52)
    print(f"通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        for name in FAILED:
            print(f"  未通过：{name}")
        return 1
    print("中途中断扣重规则验证通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
