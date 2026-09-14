"""价格与每打印费用自测。

覆盖：
  - 每盘料的 price / price_per_g / stock_value 计算
  - /api/stats 的汇总：耗材总价值、库存余值、已消耗价值、累计打印耗材费
  - 一次打印任务的耗材费（cost_total）与每条用量的 cost
  - 老数据（filaments_json 无 cost 快照）按当前单价实时折算
  - 通过 HTTP 端到端验证料盘建单带价格、统计接口返回汇总

运行： python tests/test_price.py
"""
from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ["BAMBU_MOCK"] = "1"
os.environ["DATA_DIR"] = os.path.join(ROOT, "data", "testprice")
# 让测试客户端（非内网来源）也能完成首次初始化
os.environ["ALLOW_PUBLIC_SETUP"] = "1"

from sqlmodel import select  # noqa: E402

from app.api import routes  # noqa: E402
from app.core.deduction import usage_cost  # noqa: E402
from app.db import init_db, session_scope  # noqa: E402
from app.main import app  # noqa: E402
from app.models import PrintJob, Spool  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

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
    from app.db import engine
    try:
        engine.dispose()  # 关闭连接池，Windows 上才能删掉 db 文件
    except Exception:
        pass
    data_dir = os.environ["DATA_DIR"]
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir, ignore_errors=True)
    os.makedirs(data_dir, exist_ok=True)
    init_db()


def seed() -> tuple[int, int, int]:
    """三盘料：A/B 有价，C 无价（不计入费用汇总）。"""
    with session_scope() as session:
        a = Spool(
            name="PLA 黑", brand="Bambu Lab", material="PLA", color_name="黑",
            color_hex="#1A1A1A", spool_weight=250.0, initial_weight=1000.0,
            remaining_weight=600.0, used_weight=400.0, price=100.0,
        )
        b = Spool(
            name="PETG 蓝", brand="Bambu Lab", material="PETG", color_name="蓝",
            color_hex="#1E88E5", spool_weight=250.0, initial_weight=1000.0,
            remaining_weight=1000.0, used_weight=0.0, price=120.0,
        )
        c = Spool(
            name="ABS 灰（无价）", brand="Bambu Lab", material="ABS", color_name="灰",
            color_hex="#888888", spool_weight=250.0, initial_weight=500.0,
            remaining_weight=300.0, used_weight=200.0, price=0.0,
        )
        session.add(a)
        session.add(b)
        session.add(c)
        session.commit()
        return a.id, b.id, c.id


def make_job(session, spool_a: int, spool_b: int, with_snapshot: bool) -> int:
    if with_snapshot:
        filaments = [
            {"index": 0, "filament_id": "GFA00", "material": "PLA", "color": "#1A1A1A",
             "weight_g": 200.0, "ams_id": 0, "tray_id": 0, "slot_label": "AMS 1 · 槽位 1",
             "spool_id": spool_a, "spool_name": "PLA 黑", "match_strategy": "耗材编号一致",
             "deducted_g": 200.0, "deducted": True, "cost": 20.0},
            {"index": 1, "filament_id": "GFG02", "material": "PETG", "color": "#1E88E5",
             "weight_g": 100.0, "ams_id": 0, "tray_id": 1, "slot_label": "AMS 1 · 槽位 2",
             "spool_id": spool_b, "spool_name": "PETG 蓝", "match_strategy": "耗材编号一致",
             "deducted_g": 100.0, "deducted": True, "cost": 12.0},
        ]
    else:
        # 老数据：没有 cost 快照，应回退到当前单价实时折算
        filaments = [
            {"index": 0, "filament_id": "GFA00", "material": "PLA", "color": "#1A1A1A",
             "weight_g": 100.0, "ams_id": 0, "tray_id": 0, "slot_label": "AMS 1 · 槽位 1",
             "spool_id": spool_a, "spool_name": "PLA 黑", "match_strategy": "耗材编号一致",
             "deducted_g": 100.0, "deducted": True},
        ]
    job = PrintJob(
        printer_id=1, serial="01S00A0000000000", title="测试打印",
        status="finished", total_weight_g=300.0 if with_snapshot else 100.0,
        filaments_json=__import__("json").dumps(filaments, ensure_ascii=False),
        deduction_applied=True, source="cloud_task",
    )
    session.add(job)
    session.commit()
    return job.id


def test_logic() -> None:
    reset()
    a_id, b_id, c_id = seed()

    # 1) 单盘料的价格派生字段
    with session_scope() as session:
        a = session.get(Spool, a_id)
        d = routes.spool_dict(a)
        check("spool_dict.price", d["price"] == 100.0, str(d))
        check("spool_dict.price_per_g", abs(d["price_per_g"] - 0.1) < 1e-9, str(d["price_per_g"]))
        check("spool_dict.stock_value", abs(d["stock_value"] - 60.0) < 1e-9, str(d["stock_value"]))

    # 2) usage_cost 公式
    with session_scope() as session:
        a = session.get(Spool, a_id)
        check("usage_cost 基本", abs(usage_cost(a, 250.0) - 25.0) < 1e-9, str(usage_cost(a, 250.0)))
        check("usage_cost 无价返回0", usage_cost(session.get(Spool, c_id), 100.0) == 0.0)
        check("usage_cost 负量返回0", usage_cost(a, -5.0) == 0.0)

    # 3) 两打印任务（带快照 / 不带快照）
    with session_scope() as session:
        j1 = make_job(session, a_id, b_id, with_snapshot=True)
        j2 = make_job(session, a_id, b_id, with_snapshot=False)

        # job_cost 对带快照任务
        cost1, usages1 = routes.job_cost(session.get(PrintJob, j1), session)
        check("job_cost 带快照=32", abs(cost1 - 32.0) < 1e-9, str(cost1))
        check("job_cost 每条 cost", abs(usages1[0].cost - 20.0) < 1e-9 and abs(usages1[1].cost - 12.0) < 1e-9,
              str([u.cost for u in usages1]))

        # job_cost 对老数据（无快照）→ 按当前单价 0.1*100=10
        cost2, usages2 = routes.job_cost(session.get(PrintJob, j2), session)
        check("job_cost 老数据回退=10", abs(cost2 - 10.0) < 1e-9, str(cost2))

    # 4) /api/stats 汇总
    with session_scope() as session:
        st = routes.stats(session)
        check("stats.price_total=220", abs(st["price_total"] - 220.0) < 1e-9, str(st["price_total"]))
        check("stats.stock_value=180", abs(st["stock_value"] - 180.0) < 1e-9, str(st["stock_value"]))
        check("stats.used_value=40", abs(st["used_value"] - 40.0) < 1e-9, str(st["used_value"]))
        check("stats.print_cost_total=42", abs(st["print_cost_total"] - 42.0) < 1e-9, str(st["print_cost_total"]))
        check("stats.by_material_price", st["by_material_price"].get("PLA") == 100.0
              and st["by_material_price"].get("PETG") == 120.0, str(st["by_material_price"]))
        check("stats.无价盘不计入", "ABS" not in st["by_material_price"], str(st["by_material_price"]))


def test_http() -> None:
    """端到端：登录 → 建带价格料盘 → 统计接口返回汇总。"""
    reset()
    client = TestClient(app)
    # 首次初始化管理员（TestClient 来源是 127.0.0.1，视为内网直连）
    r = client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})
    check("setup 成功", r.status_code == 200, str(r.status_code))

    # 建一盘有价料盘
    r = client.post("/api/spools", json={
        "brand": "Bambu Lab", "material": "PLA", "color_name": "黑",
        "color_hex": "#1A1A1A", "initial_weight": 1000, "remaining_weight": 500,
        "price": 88.0,
    })
    check("建料盘带价格", r.status_code == 200 and abs(r.json()["price"] - 88.0) < 1e-9, str(r.text))
    sid = r.json()["id"]

    # 统计接口应反映这盘料的汇总
    r = client.get("/api/stats")
    check("stats 接口 200", r.status_code == 200, str(r.status_code))
    data = r.json()
    check("stats 接口 price_total=88", abs(data["price_total"] - 88.0) < 1e-9, str(data["price_total"]))
    check("stats 接口 stock_value=44", abs(data["stock_value"] - 44.0) < 1e-9, str(data["stock_value"]))

    # PATCH 改价
    r = client.patch(f"/api/spools/{sid}", json={"price": 99.0})
    check("PATCH 改价", r.status_code == 200 and abs(r.json()["price"] - 99.0) < 1e-9, str(r.text))


if __name__ == "__main__":
    print("== 逻辑测试 ==")
    test_logic()
    print("== HTTP 端到端 ==")
    test_http()
    print(f"\n通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        print("失败项：", FAILED)
        sys.exit(1)
    print("全部通过")
