"""槽位展示名自测（AMS / AMS HT / 外挂料盘的编号语义）。

料盘库存列表里「这盘料装在哪儿」那一栏，来自 GET /api/spools 的 slots[].label。
老实现是 `f"AMS {ams_id + 1} · 槽位 {tray_id + 1}"`：

  - 普通 AMS 的 ams_id 是 0..3，+1 之后看着「没问题」；
  - 但 AMS HT 上报的是 128..131，于是库存列表里会显示成「AMS 129」；
  - 外挂料盘上报 ams_id = -1，会显示成「AMS 0」。

编号语义统一在 core.hub.ams_display_name，这里既测纯函数，也走一遍真实接口，
保证「列表里的那串字」是对的（写错了在界面上看着很正常，只有装了 HT 才暴露）。

运行： python tests/test_slot_label.py
"""
from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ["BAMBU_MOCK"] = "1"
os.environ["DATA_DIR"] = os.path.join(ROOT, "data", "testslotlabel")
os.environ["ALLOW_PUBLIC_SETUP"] = "1"

from app.api.routes import _slot_label  # noqa: E402
from app.core.hub import ams_display_name  # noqa: E402
from app.db import engine, init_db, session_scope  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Printer, SlotBinding, Spool  # noqa: E402
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
    try:
        engine.dispose()
    except Exception:
        pass
    data_dir = os.environ["DATA_DIR"]
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir, ignore_errors=True)
    os.makedirs(data_dir, exist_ok=True)
    init_db()


# ── 1. 纯函数 ────────────────────────────────────────────────────
def test_pure() -> None:
    print("== 槽位展示名（纯函数） ==")
    for ams, tray, want in [
        (0, 0, "AMS A · 槽位 1"),
        (1, 2, "AMS B · 槽位 3"),
        (3, 3, "AMS D · 槽位 4"),
        (5, 0, "AMS 5 · 槽位 1"),      # 认不出的编号：原样带上，别硬套 A/B/C/D
        (128, 0, "HT A · 槽位 1"),
        (129, 1, "HT B · 槽位 2"),
        (131, 3, "HT D · 槽位 4"),
        (-1, 0, "外挂料盘"),
        (-1, 3, "外挂料盘"),           # 外挂只有一路，槽位号没意义
    ]:
        got = _slot_label(ams, tray)
        check(f"_slot_label({ams}, {tray}) -> {got!r}", got == want, f"实际 {got!r}")

    check("AMS HT 不会拼出「AMS 129」", "129" not in _slot_label(128, 0), _slot_label(128, 0))
    check("外挂料盘不会显示成「AMS -1」",
          "AMS" not in _slot_label(-1, 0), _slot_label(-1, 0))
    # 与 core.hub 的编号规则同源：改了那边这里必须跟着变
    for ams in (0, 2, 128, 130):
        check(f"ams={ams} 的单元名与 hub 一致",
              ams_display_name(ams) in _slot_label(ams, 0), _slot_label(ams, 0))


# ── 2. 走真实接口：料盘列表里的「装在哪儿」 ─────────────────────
def test_http_labels() -> None:
    print("== GET /api/spools 里的槽位标签 ==")
    client = TestClient(app)
    r = client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})
    check("初始化管理员（测试前置）", r.status_code in (200, 409), r.text[:120])

    with session_scope() as session:
        printer = Printer(serial="TESTSLOT01", name="测试机", model="P2S")
        session.add(printer)
        spool = Spool(
            name="PLA 黑", brand="Bambu Lab", material="PLA", color_name="黑",
            color_hex="#1A1A1A", spool_weight=250.0,
            initial_weight=1000.0, remaining_weight=800.0,
        )
        session.add(spool)
        session.commit()
        session.refresh(printer)
        session.refresh(spool)
        printer_id, spool_id = printer.id, spool.id

        # 一盘料同时挂在：普通 AMS 的 A1、AMS HT 的 A1、外挂料盘
        for ams_id, tray_id in ((0, 0), (128, 0), (-1, 0)):
            session.add(SlotBinding(printer_id=printer_id, ams_id=ams_id,
                                    tray_id=tray_id, spool_id=spool_id))
        session.commit()

    r = client.get("/api/spools?archived=false")
    check("料盘列表接口正常", r.status_code == 200, r.text[:120])
    rows = {item["id"]: item for item in r.json().get("spools", [])}
    slots = rows.get(spool_id, {}).get("slots", [])
    labels = [s["label"] for s in slots]
    check("三个槽位都带出来了", len(labels) == 3, str(labels))
    check("普通 AMS 显示成「AMS A · 槽位 1」", "AMS A · 槽位 1" in labels, str(labels))
    check("AMS HT 显示成「HT A · 槽位 1」", "HT A · 槽位 1" in labels, str(labels))
    check("外挂料盘单独写", "外挂料盘" in labels, str(labels))
    check("列表里不出现「AMS 129」这种拼接（老 bug）",
          not any("129" in x for x in labels), str(labels))
    check("槽位条目带 printer_id / ams_id / tray_id（前端要用来定位）",
          all({"printer_id", "ams_id", "tray_id"} <= set(s) for s in slots), str(slots))

    # /api/bindings 也要带上同样的信息，不然两处口径会分叉
    r = client.get("/api/bindings")
    check("绑定接口正常", r.status_code == 200, r.text[:120])
    binds = r.json().get("bindings", [])
    check("绑定接口返回了这 3 条", len(binds) == 3, str(len(binds)))
    check("绑定接口里的 ams_id 是原始编号（128 不能被改写成 129）",
          sorted(b["ams_id"] for b in binds) == [-1, 0, 128],
          str(sorted(b["ams_id"] for b in binds)))


# ── 主流程 ───────────────────────────────────────────────────────
def main() -> int:
    reset()
    test_pure()
    test_http_labels()

    print("")
    print("=" * 58)
    if FAILED:
        print(f"通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
        print(f"失败项： {FAILED}")
        return 1
    print(f"通过 {len(PASSED)} 项，失败 0 项")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    sys.exit(main())
