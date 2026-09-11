"""端到端流程自测：不依赖真实打印机与拓竹账号。

直接驱动中枢的状态机与结算逻辑，验证：
  绑定槽位 → 收到打印状态 → 任务开始 → 任务结束 → 云端克重匹配 → 扣减到正确料盘

运行： python tests/test_flow.py
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
os.environ["DATA_DIR"] = os.path.join(ROOT, "data", "testflow")

from sqlmodel import select  # noqa: E402

from app.cloud.mock import MockSource  # noqa: E402
from app.core.hub import hub  # noqa: E402
from app.db import init_db, session_scope  # noqa: E402
from app.models import Printer, PrintJob, SlotBinding, Spool, UsageRecord  # noqa: E402

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
    """清空测试数据。注意目录要先重建，否则 SQLite 无法创建库文件。"""
    data_dir = os.environ["DATA_DIR"]
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir, ignore_errors=True)
    os.makedirs(data_dir, exist_ok=True)
    init_db()


def seed() -> tuple[int, int, int, int]:
    """建两盘料 + 绑定到 AMS1 的槽位 1、槽位 2。"""
    with session_scope() as session:
        printer = session.exec(select(Printer)).first()
        if printer is None:
            raise RuntimeError("模拟设备未创建")
        a = Spool(
            name="Bambu Lab PLA Basic 黑色", brand="Bambu Lab", material="PLA",
            color_name="黑色", color_hex="#1A1A1A", spool_weight=250.0,
            initial_weight=1000.0, remaining_weight=1000.0, tray_info_idx="GFA00",
        )
        b = Spool(
            name="Bambu Lab PETG HF 蓝色", brand="Bambu Lab", material="PETG",
            color_name="蓝色", color_hex="#1E88E5", spool_weight=250.0,
            initial_weight=1000.0, remaining_weight=1000.0, tray_info_idx="GFG02",
        )
        session.add(a)
        session.add(b)
        session.flush()
        session.add(SlotBinding(printer_id=printer.id, ams_id=0, tray_id=0, spool_id=a.id))
        session.add(SlotBinding(printer_id=printer.id, ams_id=0, tray_id=1, spool_id=b.id))
        return printer.id, a.id, b.id, 0


def base_block(state: str = "IDLE", **overrides) -> dict:
    block = MockSource(SERIAL)._base()
    block["gcode_state"] = state
    block.update(overrides)
    return block


async def main() -> int:
    print("拓竹耗材管家 · 端到端流程自测")
    reset()

    # 手工装配中枢，不启动后台线程，保证过程可控
    hub._loop = asyncio.get_running_loop()
    hub._ensure_mock_printer()
    hub._load_printers()
    printer_id, spool_a, spool_b, _ = seed()

    serial = SERIAL
    job_started = datetime.utcnow()

    print("\n1. 收到空闲状态")
    await hub._apply_payload(serial, {"print": base_block()})
    check("状态已缓存", hub.states.get(printer_id) is not None)
    state = hub.states[printer_id]
    check("识别到 AMS", len(state.ams_units) == 1, f"实际 {len(state.ams_units)}")
    check("槽位 1 有料", state.ams_units[0].trays[0].occupied)
    check("槽位 2 空置", not state.ams_units[0].trays[2].occupied)
    check("耗材编号解析正确", state.ams_units[0].trays[0].info_idx == "GFA00")

    print("\n2. 打印开始 → 自动建任务")
    await hub._apply_payload(serial, {"print": base_block(
        "PREPARE", subtask_name="WALL-E_机械臂.stl", stg_cur=1)})
    check("已开出一条进行中的任务", printer_id in hub._open)
    await hub._apply_payload(serial, {"print": base_block(
        "RUNNING", subtask_name="WALL-E_机械臂.stl", task_id="12345678",
        mc_percent=30, stg_cur=0)})
    check("任务标题已记录", hub._open[printer_id]["title"] == "WALL-E_机械臂.stl")
    check("任务编号已记录", hub._open[printer_id]["task_id"] == "12345678")

    print("\n3. 打印完成 → 关任务并进入待结算")
    await hub._apply_payload(serial, {"print": base_block(
        "RUNNING", subtask_name="WALL-E_机械臂.stl", task_id="12345678", mc_percent=100)})
    await hub._apply_payload(serial, {"print": base_block(
        "FINISH", subtask_name="WALL-E_机械臂.stl", task_id="12345678", mc_percent=100)})

    with session_scope() as session:
        job = session.exec(select(PrintJob)).first()
    check("已生成打印记录", job is not None)
    check("任务状态为已完成", job is not None and job.status == "finished",
          f"实际 {job.status if job else '-'}")
    check("已进入待结算队列", job is not None and job.id in hub.pending_jobs())
    check("此时还没扣重", job is not None and not job.deduction_applied)

    print("\n4. 云端任务记录到位 → 自动匹配并扣重")
    task = {
        "id": 12345678,
        "title": "WALL-E_机械臂.stl",
        "deviceId": serial,
        "deviceModel": "P2S",
        "startTime": (job_started - timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endTime": (job_started + timedelta(minutes=22)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "weight": 12.58,
        "length": 4185,
        "amsDetailMapping": [
            {"ams": 0, "filamentId": "GFA00", "filamentType": "PLA",
             "sourceColor": "1A1A1AFF", "targetColor": "1A1A1AFF", "weight": 9.42},
            {"ams": 1, "filamentId": "GFG02", "filamentType": "PETG",
             "sourceColor": "1E88E5FF", "targetColor": "1E88E5FF", "weight": 3.16},
        ],
    }

    async def fake_tasks():
        return [task]

    hub.fetch_cloud_tasks = fake_tasks  # type: ignore[assignment]
    result = await hub.settle_pending()

    check("结算成功 1 条", result.get("settled") == 1, f"实际 {result}")

    with session_scope() as session:
        job = session.get(PrintJob, job.id)
        a = session.get(Spool, spool_a)
        b = session.get(Spool, spool_b)
        records = session.exec(select(UsageRecord)).all()

    check("任务标记为已扣重", job.deduction_applied)
    check("数据来源标记为云端任务", job.source == "cloud_task", job.source)
    check("任务总用量 = 12.58 g", abs(job.total_weight_g - 12.58) < 0.01, str(job.total_weight_g))
    check("黑色 PLA 扣了 9.42 g", abs(a.remaining_weight - 990.58) < 0.01, str(a.remaining_weight))
    check("蓝色 PETG 扣了 3.16 g", abs(b.remaining_weight - 996.84) < 0.01, str(b.remaining_weight))
    check("已用重量同步累加", abs(a.used_weight - 9.42) < 0.01, str(a.used_weight))
    check("生成 2 条使用流水", len(records) == 2, f"实际 {len(records)}")
    check("流水都挂到了料盘上", all(r.spool_id for r in records))

    filaments = json.loads(job.filaments_json)
    check("明细条数 = 2", len(filaments) == 2, str(len(filaments)))
    check(
        "匹配依据为「耗材编号 + 颜色一致」",
        all(f["match_strategy"] == "耗材编号 + 颜色一致" for f in filaments),
        str([f["match_strategy"] for f in filaments]),
    )
    check("明细指向正确料盘", filaments[0]["spool_id"] == spool_a and filaments[1]["spool_id"] == spool_b)
    check("已从待结算队列移除", job.id not in hub.pending_jobs())

    print("\n5. 重复结算不应重复扣重")
    result2 = await hub.settle_pending(force_job_id=job.id)
    with session_scope() as session:
        a2 = session.get(Spool, spool_a)
    check("重复结算被跳过", abs(a2.remaining_weight - 990.58) < 0.01, str(a2.remaining_weight))

    print("\n6. 未绑定料盘的槽位只记流水、不扣重")
    with session_scope() as session:
        session.exec(select(SlotBinding)).all()  # 触发加载
        binding = session.exec(
            select(SlotBinding).where(SlotBinding.ams_id == 0, SlotBinding.tray_id == 1)
        ).first()
        session.delete(binding)

    job2 = PrintJob(printer_id=printer_id, serial=serial, title="未绑定测试", status="finished",
                    started_at=datetime.utcnow(), finished_at=datetime.utcnow(), progress_at_end=100)
    with session_scope() as session:
        session.add(job2)
        session.flush()
        job2_id = job2.id

    task2 = dict(task)
    task2["id"] = 99999999
    task2["title"] = "未绑定测试"

    async def fake_tasks2():
        return [task2]

    hub.fetch_cloud_tasks = fake_tasks2  # type: ignore[assignment]
    hub.retry_settle(job2_id)
    await hub.settle_pending(force_job_id=job2_id)

    with session_scope() as session:
        b3 = session.get(Spool, spool_b)
        orphan = session.exec(
            select(UsageRecord).where(UsageRecord.spool_id == None)  # noqa: E711
        ).all()

    check("未绑定槽位不扣任何料盘", abs(b3.remaining_weight - 996.84) < 0.01, str(b3.remaining_weight))
    check("仍留下待认领的流水", len(orphan) >= 1, f"实际 {len(orphan)}")

    print("\n" + "─" * 52)
    print(f"通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        for name in FAILED:
            print(f"  未通过：{name}")
        return 1
    print("全流程验证通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
