"""料盘管理与品牌归一自测。

覆盖：
  - normalize_brand：英文别名 / 大小写 / 多余空格都归到规范名，自定义品牌原样保留
  - BRAND_PRESETS 无重复项（同一品牌不再出现「Bambu Lab」+「拓竹」两份）
  - _migrate_data：老库里的历史品牌写法启动时自动收口，且幂等、不误伤自定义品牌
  - HTTP 建单 / 改单时品牌被归一
  - DELETE /api/spools/{id}：无流水直接删；有流水默认 409 保护；
    force=true 连带清理使用流水、槽位绑定，并把打印任务明细里的引用置空

运行： python tests/test_admin.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ["BAMBU_MOCK"] = "1"
os.environ["DATA_DIR"] = os.path.join(ROOT, "data", "testadmin")
# 让测试客户端（非内网来源）也能完成首次初始化
os.environ["ALLOW_PUBLIC_SETUP"] = "1"

from sqlmodel import select  # noqa: E402

from app.catalog import BRAND_PRESETS, normalize_brand  # noqa: E402
from app.db import _migrate_data, init_db, session_scope  # noqa: E402
from app.main import app  # noqa: E402
from app.models import PrintJob, SlotBinding, Spool, UsageRecord  # noqa: E402
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


# ── 1. 品牌归一（纯函数） ─────────────────────────────────────────
def test_normalize() -> None:
    print("== 品牌归一 ==")
    cases = [
        ("Bambu Lab", "拓竹"),
        ("bambulab", "拓竹"),
        ("BAMBU LAB", "拓竹"),
        ("  拓竹  ", "拓竹"),
        ("拓竹", "拓竹"),
        ("拓竹科技", "拓竹"),
        ("bambu", "拓竹"),
        ("polymaker", "Polymaker"),
        ("POLYMAKER", "Polymaker"),
        ("PolyMaker", "Polymaker"),
        ("kecelled", "Kexcelled"),          # 常见拼写变体
        ("KEXCELLED", "Kexcelled"),
        ("esun", "eSUN 易生"),
        ("易生", "eSUN 易生"),
        ("三绿", "三绿 Sunlu"),
        ("", ""),
    ]
    for raw, want in cases:
        got = normalize_brand(raw)
        check(f"normalize({raw!r}) -> {want}", got == want, f"实际 {got!r}")

    # 自定义品牌不应被改写
    for raw in ("自家作坊", "MyBrand PLA", "某宝白牌"):
        check(f"自定义品牌保留：{raw}", normalize_brand(raw) == raw, normalize_brand(raw))


# ── 2. 品牌下拉框无重复 ───────────────────────────────────────────
def test_no_duplicate_brands() -> None:
    print("== 品牌预设去重 ==")
    check("BRAND_PRESETS 无重复项", len(BRAND_PRESETS) == len(set(BRAND_PRESETS)),
          str([b for b in BRAND_PRESETS if BRAND_PRESETS.count(b) > 1]))
    check("不含英文旧写法 Bambu Lab", "Bambu Lab" not in BRAND_PRESETS, str(BRAND_PRESETS))
    check("含规范名 拓竹", "拓竹" in BRAND_PRESETS)
    check("含「其他」兜底项", "其他" in BRAND_PRESETS)
    # 每个预设项自身都应是规范写法（再归一不变）
    unstable = [b for b in BRAND_PRESETS if normalize_brand(b) != b]
    check("所有预设项都已是规范名", not unstable, str(unstable))


# ── 3. 历史数据迁移 ───────────────────────────────────────────────
def test_brand_migration() -> None:
    print("== 历史品牌写法迁移 ==")
    reset()
    # 直接落库，绕过接口层的归一（模拟老库里的脏数据）
    with session_scope() as session:
        session.add(Spool(name="旧1", brand="Bambu Lab", material="PLA", color_name="黑",
                          color_hex="#1A1A1A", initial_weight=1000.0, remaining_weight=1000.0))
        session.add(Spool(name="旧2", brand="bambulab", material="PETG", color_name="蓝",
                          color_hex="#1E88E5", initial_weight=1000.0, remaining_weight=1000.0))
        session.add(Spool(name="自定义", brand="自家作坊", material="PLA", color_name="红",
                          color_hex="#D32F2F", initial_weight=1000.0, remaining_weight=1000.0))

    _migrate_data()

    with session_scope() as session:
        by_name = {s.name: s.brand for s in session.exec(select(Spool)).all()}
    check("Bambu Lab -> 拓竹", by_name.get("旧1") == "拓竹", str(by_name))
    check("bambulab -> 拓竹", by_name.get("旧2") == "拓竹", str(by_name))
    check("自定义品牌未被误改", by_name.get("自定义") == "自家作坊", str(by_name))

    # 幂等：再跑一次不应有任何变化
    _migrate_data()
    with session_scope() as session:
        again = {s.name: s.brand for s in session.exec(select(Spool)).all()}
    check("迁移幂等", again == by_name, f"{again} != {by_name}")


# ── 4. HTTP：建单 / 改单归一 ──────────────────────────────────────
def test_http_brand() -> None:
    print("== HTTP：品牌归一 ==")
    reset()
    client = TestClient(app)
    r = client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})
    check("setup 成功", r.status_code == 200, str(r.status_code))

    r = client.post("/api/spools", json={
        "brand": "Bambu Lab", "material": "PLA", "color_name": "黑",
        "color_hex": "#1A1A1A", "initial_weight": 1000, "price": 88.0,
    })
    check("建单成功", r.status_code == 200, r.text)
    body = r.json()
    check("建单时品牌已归一", body.get("brand") == "拓竹", str(body.get("brand")))
    check("默认名随归一后的品牌生成", body.get("name", "").startswith("拓竹"), str(body.get("name")))
    sid = body["id"]

    r = client.patch(f"/api/spools/{sid}", json={"brand": "polymaker"})
    check("改单时品牌已归一",
          r.status_code == 200 and r.json().get("brand") == "Polymaker", r.text)

    # 品牌下拉框接口也不应有重复
    r = client.get("/api/catalog")
    if r.status_code == 200:
        brands = r.json().get("brands", [])
        check("catalog.brands 无重复", len(brands) == len(set(brands)), str(brands))
        check("catalog.brands 无 Bambu Lab", "Bambu Lab" not in brands, str(brands))


# ── 5. HTTP：删除料盘 ─────────────────────────────────────────────
def _seed_spool_with_history() -> tuple[int, int]:
    """造一盘有 2 条流水 + 1 条槽位绑定 + 1 个打印任务引用它的料盘。"""
    with session_scope() as session:
        spool = Spool(name="待删料盘", brand="拓竹", material="PLA", color_name="深绿",
                      color_hex="#1F5B3A", spool_weight=250.0, initial_weight=1000.0,
                      remaining_weight=780.0, used_weight=220.0, price=100.0)
        session.add(spool)
        session.commit()
        sid = spool.id

        job = PrintJob(
            printer_id=1, title="测试任务", status="finished", source="cloud_task",
            total_weight_g=220.0, deduction_applied=True,
            filaments_json=json.dumps([
                {"index": 0, "filament_id": "GFA00", "material": "PLA", "color": "#1F5B3A",
                 "weight_g": 220.0, "ams_id": 0, "tray_id": 0, "slot_label": "AMS 1 · 槽位 1",
                 "spool_id": sid, "spool_name": "待删料盘", "match_strategy": "按槽位绑定",
                 "deducted_g": 220.0, "deducted": True, "cost": 22.0},
            ], ensure_ascii=False),
        )
        session.add(job)
        session.add(SlotBinding(printer_id=1, ams_id=0, tray_id=0, spool_id=sid))
        session.add(UsageRecord(spool_id=sid, job_id=None, weight_g=200.0, source="auto",
                                note="打印任务"))
        session.add(UsageRecord(spool_id=sid, weight_g=20.0, source="manual", note="手动补录"))
        session.commit()
        return sid, job.id


def test_http_delete() -> None:
    print("== HTTP：删除料盘 ==")
    reset()
    client = TestClient(app)
    client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})

    # 5.1 无流水的料盘：一次删掉，不该被拦
    r = client.post("/api/spools", json={
        "brand": "Polymaker", "material": "PLA", "color_name": "白",
        "color_hex": "#FFFFFF", "initial_weight": 1000,
    })
    clean_id = r.json()["id"]
    r = client.delete(f"/api/spools/{clean_id}")
    check("无流水料盘直接删除 200", r.status_code == 200, r.text)
    check("删除后 detail 计数为 0",
          r.status_code == 200 and r.json().get("deleted_usages") == 0, r.text)

    # 5.2 有流水的料盘：默认 409 保护
    sid, job_id = _seed_spool_with_history()
    r = client.delete(f"/api/spools/{sid}")
    check("有流水时默认 409", r.status_code == 409, str(r.status_code))
    detail = ""
    try:
        detail = r.json().get("detail", "")
    except Exception:
        detail = r.text
    check("409 提示里带了流水条数", "2 条" in detail, detail)
    check("409 后料盘仍然存在", client.get(f"/api/spools/{sid}").status_code == 200)

    # 5.3 force 删除：连带清理
    r = client.delete(f"/api/spools/{sid}?force=true")
    check("force 删除 200", r.status_code == 200, r.text)
    payload = r.json() if r.status_code == 200 else {}
    check("汇报删除流水 2 条", payload.get("deleted_usages") == 2, str(payload))
    check("汇报删除绑定 1 条", payload.get("deleted_bindings") == 1, str(payload))
    check("汇报更新任务 1 个", payload.get("jobs_updated") == 1, str(payload))

    check("料盘已不存在", client.get(f"/api/spools/{sid}").status_code == 404)

    with session_scope() as session:
        left = session.exec(select(UsageRecord).where(UsageRecord.spool_id == sid)).all()
        bind = session.exec(select(SlotBinding).where(SlotBinding.spool_id == sid)).all()
        check("使用流水已清空", not left, str(len(left)))
        check("槽位绑定已清空", not bind, str(len(bind)))

        job = session.get(PrintJob, job_id)
        entries = json.loads(job.filaments_json) if job else []
        check("打印任务本身保留", job is not None)
        check("任务明细里的料盘引用已置空",
              entries and entries[0].get("spool_id") is None, str(entries[:1]))
        check("任务明细保留克重",
              entries and abs(entries[0].get("weight_g", 0) - 220.0) < 1e-9, str(entries[:1]))
        check("明细标注了料盘已删除",
              entries and "料盘已删除" in entries[0].get("match_strategy", ""), str(entries[:1]))
        check("任务总克重未被改动", job and abs(job.total_weight_g - 220.0) < 1e-9,
              str(job.total_weight_g if job else None))

    # 5.4 再删一次 → 404
    r = client.delete(f"/api/spools/{sid}?force=true")
    check("重复删除返回 404", r.status_code == 404, str(r.status_code))

    # 5.5 删除后统计不再包含这盘料的价格
    r = client.get("/api/stats")
    check("统计接口 200", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        check("已删料盘的价格不再计入",
              abs(r.json().get("price_total", -1) - 0.0) < 1e-9, str(r.json().get("price_total")))


if __name__ == "__main__":
    print("== 品牌归一 ==")
    test_normalize()
    test_no_duplicate_brands()
    test_brand_migration()
    test_http_brand()
    test_http_delete()
    print(f"\n通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        print("失败项：", FAILED)
        sys.exit(1)
    print("全部通过")
