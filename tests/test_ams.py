"""AMS / AMS HT 状态归一自测。

覆盖：
  - ams_display_name：0..3 归成 AMS A..D，128..131 归成 HT A..D，
    其余 id 不冒充普通单元（老代码拿 ams_id + 1 会把 AMS HT 显示成「129」）
  - ams_kind：区分普通 AMS 与高温烘干版 AMS HT
  - clean_ams_model：固件把序列号塞进 info 时不能当型号展示
  - remain_grams：空槽 / 未上报 remain 返回 None，其余按标称满重折算克重
  - _bit_set：位串没覆盖到的槽位返回 None，否则 AMS HT 整排会被误判成空
  - state_dict：kind / name / slot_count / remain_weight_g / fans.heatbreak 都下发

运行： python tests/test_ams.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ["BAMBU_MOCK"] = "1"
os.environ["DATA_DIR"] = os.path.join(ROOT, "data", "testams")

from app.cloud.mock import MOCK_HT_ID, MockSource  # noqa: E402
from app.core.hub import (  # noqa: E402
    ams_display_name,
    ams_kind,
    clean_ams_model,
    hub,
    remain_grams,
)
from app.core.status import TrayState, _bit_set, parse_report  # noqa: E402

PASSED: list[str] = []
FAILED: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(label)
        print(f"  [通过] {label}")
    else:
        FAILED.append(label)
        print(f"  [失败] {label} {detail}")


# ── 1. 编号与类型（纯函数） ─────────────────────────────────────
def test_display_name() -> None:
    print("== AMS / HT 编号归一 ==")
    for idx, letter in enumerate("ABCD"):
        expected = f"AMS {letter}"
        check(f"ams_id={idx} → {expected}", ams_display_name(idx) == expected, ams_display_name(idx))
    for idx, letter in enumerate("ABCD"):
        ams_id = 128 + idx
        expected = f"HT {letter}"
        check(f"ams_id={ams_id} → {expected}", ams_display_name(ams_id) == expected, ams_display_name(ams_id))
    check("AMS HT 不再显示成「AMS 129」", ams_display_name(128) != "AMS 129")
    check("超范围 id 原样带出", ams_display_name(9) == "AMS 9", ams_display_name(9))
    check("kind：普通 AMS", ams_kind(0) == "ams" and ams_kind(3) == "ams")
    check("kind：AMS HT", ams_kind(128) == "ht" and ams_kind(131) == "ht")
    check("kind：132 不算 HT", ams_kind(132) == "ams")


def test_model_clean() -> None:
    print("== AMS 型号清洗 ==")
    check("长串序列号不当型号", clean_ams_model("10002003", 0) == "AMS", clean_ams_model("10002003", 0))
    check("HT 的序列号回落到 AMS HT", clean_ams_model("10002004", 128) == "AMS HT",
          clean_ams_model("10002004", 128))
    check("正常型号原样保留", clean_ams_model("AMS 2 Pro", 0) == "AMS 2 Pro")
    check("空值回落到默认名", clean_ams_model("", 0) == "AMS")
    check("短数字不算序列号", clean_ams_model("123", 0) == "123")


def test_remain_grams() -> None:
    print("== 槽位克重折算 ==")
    half = TrayState(occupied=True, remain=50, tray_weight=1000.0)
    check("50% × 1000g = 500g", remain_grams(half) == 500.0, str(remain_grams(half)))
    small = TrayState(occupied=True, remain=24, tray_weight=750.0)
    check("750g 盘按比例折算", remain_grams(small) == 180.0, str(remain_grams(small)))
    empty = TrayState(occupied=False, remain=50, tray_weight=1000.0)
    check("空槽不计克重", remain_grams(empty) is None)
    unknown = TrayState(occupied=True, remain=-1, tray_weight=1000.0)
    check("未上报 remain 不计克重", remain_grams(unknown) is None)
    zero = TrayState(occupied=True, remain=0, tray_weight=1000.0)
    check("remain=0 得 0g 而不是 None", remain_grams(zero) == 0.0, str(remain_grams(zero)))


def test_bit_string() -> None:
    print("== 位串越界保护 ==")
    check("空位串返回 None", _bit_set("", 0) is None)
    check("非法位串返回 None", _bit_set("zz", 0) is None)
    check("负数下标返回 None", _bit_set("f", -1) is None)
    check("宽度内 1 位判为 True", _bit_set("b", 0) is True)
    check("宽度内 0 位判为 False", _bit_set("b", 2) is False)
    check("超出位宽返回 None（AMS HT 的关键）", _bit_set("b", MOCK_HT_ID * 4) is None)
    check("超出位宽返回 None（靠后的普通单元）", _bit_set("b", 6) is None)


# ── 2. 解析 mock 上报 ──────────────────────────────────────────
def test_parsed_state() -> None:
    print("== 解析 mock 上报 ==")
    state = parse_report({"print": MockSource()._base()})
    check("解析成功", state is not None)
    if state is None:
        return
    check("两个 AMS 单元", len(state.ams_units) == 2, str(len(state.ams_units)))
    first = state.ams_units[0]
    check("首个单元是四槽普通 AMS", first.ams_id == 0 and len(first.trays) == 4)
    check("位串生效：槽位 3 为空", not first.trays[2].occupied)
    check("位串生效：槽位 1 有料", first.trays[0].occupied)

    ht = next((unit for unit in state.ams_units if unit.ams_id == MOCK_HT_ID), None)
    check("AMS HT 已上报", ht is not None)
    if ht is not None:
        check("AMS HT 单槽位且有料", len(ht.trays) == 1 and ht.trays[0].occupied)
        check("AMS HT 湿度是百分比口径", float(ht.humidity) > 5, str(ht.humidity))
    check("外挂料盘有料", state.external_spool is not None and state.external_spool.occupied)


def test_state_dict() -> None:
    print("== 下发字段 ==")
    state = parse_report({"print": MockSource()._base()})
    payload = hub.state_dict(state, 1)
    units = {unit["ams_id"]: unit for unit in payload["ams"]}

    check("含普通 AMS 单元", 0 in units)
    check("含 AMS HT 单元", MOCK_HT_ID in units)
    if 0 in units:
        unit = units[0]
        check("普通单元 kind=ams", unit["kind"] == "ams")
        check("普通单元 name=AMS A", unit["name"] == "AMS A", str(unit.get("name")))
        check("普通单元 slot_count=4", unit["slot_count"] == 4)
        check("普通单元 model 已清洗", unit["model"] == "AMS 2 Pro", str(unit.get("model")))
        tray = unit["trays"][1]
        check("槽位带 remain_weight_g", tray["remain_weight_g"] == 640.0, str(tray.get("remain_weight_g")))
        check("槽位带 tray_type", tray["tray_type"] == "PETG", str(tray.get("tray_type")))
        check("空槽 remain_weight_g 为 None", unit["trays"][2]["remain_weight_g"] is None)
    if MOCK_HT_ID in units:
        unit = units[MOCK_HT_ID]
        check("HT 单元 kind=ht", unit["kind"] == "ht")
        check("HT 单元 name=HT A", unit["name"] == "HT A", str(unit.get("name")))
        check("HT 单元 slot_count=1", unit["slot_count"] == 1)

    ext = payload.get("external_spool") or {}
    check("外挂料盘带克重", ext.get("remain_weight_g") == 760.0, str(ext))
    check("外挂料盘带材料", ext.get("tray_type") == "PLA", str(ext))

    fans = payload.get("fans") or {}
    for key in ("cooling", "aux", "chamber", "heatbreak", "secondary"):
        check(f"风扇通道含 {key}", key in fans)


if __name__ == "__main__":
    test_display_name()
    test_model_clean()
    test_remain_grams()
    test_bit_string()
    test_parsed_state()
    test_state_dict()
    print(f"\n通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        print("失败项：", FAILED)
        sys.exit(1)
    print("全部通过")
