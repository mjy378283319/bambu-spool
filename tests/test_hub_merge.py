"""中枢报文合并自测：增量报文怎么并进缓存，状态怎么被记住。

覆盖（都来自 2026-09-18 的真实反馈）：
  - _deep_merge：`print.device` 是多层嵌套，浅合并 `{**old, **new}` 一旦碰到
    带 device 的增量就把整棵子树换掉 —— device.ctc 随之消失，**仓温在界面上
    变成「—」**，而且打印机不再重发整包就永远回不来。
  - 列表（ams / hms）必须整体替换：逐项合并会把已经拔掉的料盘留在里面。
  - 左(辅助) 选配风扇的记忆：有些固件只在它转着的时候才在 airduct.parts 里报它，
    见过一次就得记住「这台机器装了」，之后不转也仍是「已装·未转」而不是「未安装」。

运行： python tests/test_hub_merge.py
"""
from __future__ import annotations

import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.core.hub import PrinterHub, _deep_merge  # noqa: E402
from app.core.status import AIRDUCT_PART_LEFT_AUX  # noqa: E402

PASSED: list[str] = []
FAILED: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(label)
        print(f"  [通过] {label}")
    else:
        FAILED.append(label)
        print(f"  [失败] {label} {detail}")


SERIAL = "01S00A0000000000"


def full_report() -> dict:
    """一份「整包」：P2S 真机结构，仓温在 device.ctc.info.temp，
    左辅助风扇此刻在转（parts 里有 160）。"""
    return {"print": {
        "gcode_state": "RUNNING",
        "bed_temper": 55.0,
        "nozzle_temper": 220.0,
        "device": {
            "ctc": {"info": {"temp": 40 << 16 | 37}, "state": 0},
            "airduct": {
                "modeList": [{"modeId": 0, "ctrl": [16, 32, 160]}],
                "parts": [
                    {"func": 0, "id": 16, "state": 90},
                    {"func": 6, "id": 32, "state": 0},
                    {"func": 0, "id": AIRDUCT_PART_LEFT_AUX, "state": 40},
                ],
            },
        },
    }}


async def drive(hub_obj: PrinterHub, payload: dict) -> None:
    """把一包报文喂给中枢（跳过打印机查库与状态机，只验证合并与记忆）。"""
    await hub_obj._apply_payload(SERIAL, payload)


def test_deep_merge_pure() -> None:
    print("== _deep_merge 纯函数 ==")
    base = {"device": {"ctc": {"info": {"temp": 37}}, "airduct": {"modeCur": 0}}, "mc_percent": 10}
    delta = {"device": {"airduct": {"modeCur": 3}}, "mc_percent": 20}
    merged = _deep_merge(base, delta)
    check("嵌套字典递归合并，兄弟键不丢",
          merged["device"]["ctc"]["info"]["temp"] == 37, str(merged))
    check("同一子树里的新值生效", merged["device"]["airduct"]["modeCur"] == 3, str(merged))
    check("顶层标量被增量覆盖", merged["mc_percent"] == 20, str(merged))
    check("不改动传入的原对象", base["device"]["airduct"]["modeCur"] == 0, str(base))

    # 列表整体替换：ams 报的是「当前完整状态」
    lst = _deep_merge({"ams": {"ams": [{"id": 0}, {"id": 1}]}}, {"ams": {"ams": [{"id": 0}]}})
    check("列表整体替换（拔掉的单元不会残留）", len(lst["ams"]["ams"]) == 1, str(lst))
    check("空增量不动原值", _deep_merge({"a": {"b": 1}}, {})["a"]["b"] == 1)


def test_merge_keeps_chamber() -> None:
    print("== 增量报文不能吃掉仓温（本次反馈的核心场景）==")
    hub_obj = PrinterHub()
    hub_obj._printer_by_serial[SERIAL] = 1

    async def noop_transition(*_a, **_k) -> None:
        return None

    hub_obj._handle_transition = noop_transition  # type: ignore[assignment]

    async def run() -> None:
        await drive(hub_obj, full_report())
        first = hub_obj.states[1]
        check("整包解析出仓温 37℃", first.chamber_temper == 37.0, str(first.chamber_temper))
        check("整包解析出左(辅助) 40%", first.secondary_aux_fan_pct == 40,
              str(first.secondary_aux_fan_pct))

        # 关键一包：只带 device.airduct（风扇调速是最高频的增量）
        await drive(hub_obj, {"print": {"device": {"airduct": {
            "parts": [{"func": 0, "id": 16, "state": 60}, {"func": 6, "id": 32, "state": 0}],
        }}}})
        after = hub_obj.states[1]
        check("增量只带 airduct 时仓温仍在（浅合并会在这里丢掉 ctc）",
              after.chamber_temper == 37.0, str(after.chamber_temper))
        check("右(辅助) 跟着增量变到 60%", after.airduct_fan_pct == 60,
              str(after.airduct_fan_pct))
        check("没被增量提到的温度也还在", after.bed_temper == 55.0, str(after.bed_temper))

    asyncio.run(run())


def test_left_aux_remembered() -> None:
    print("== 左(辅助) 装过就记住（不转时不能变「未安装」）==")
    hub_obj = PrinterHub()
    hub_obj._printer_by_serial[SERIAL] = 1

    async def noop_transition(*_a, **_k) -> None:
        return None

    hub_obj._handle_transition = noop_transition  # type: ignore[assignment]

    async def run() -> None:
        await drive(hub_obj, full_report())
        check("转着的时候：已装 + 40%",
              hub_obj.states[1].secondary_aux_installed
              and hub_obj.states[1].secondary_aux_fan_pct == 40)

        # 风扇停了：固件不再上报这个部件，modeList 也不再提它（最苛刻的情况）
        await drive(hub_obj, {"print": {"device": {"airduct": {
            "modeList": [{"modeId": 0, "ctrl": [16, 32]}],
            "parts": [{"func": 0, "id": 16, "state": 0}, {"func": 6, "id": 32, "state": 0}],
        }}}})
        stopped = hub_obj.states[1]
        check("停了之后转速回到 None（界面不画假进度条）",
              stopped.secondary_aux_fan_pct is None, str(stopped.secondary_aux_fan_pct))
        check("停了之后仍算「已安装」→ 界面写「未转」而不是「未安装」",
              stopped.secondary_aux_installed, str(stopped.secondary_aux_installed))

        payload = hub_obj.state_dict(stopped, 1)
        check("下发 fans.secondary 为 null", payload["fans"]["secondary"] is None)
        check("下发 fans_installed.secondary 为 True",
              payload["fans_installed"]["secondary"] is True, str(payload.get("fans_installed")))

        # 从没见过的机器：不能凭空说人家装了
        other = PrinterHub()
        check("没见过的机器默认未安装",
              other.states.get(1) is None and not PrinterHub()._left_aux_serial, "")

    asyncio.run(run())

    # 完全不带 airduct 的机型（X1/P1/A1）
    plain = PrinterHub()
    plain._printer_by_serial[SERIAL] = 1

    async def noop2(*_a, **_k) -> None:
        return None

    plain._handle_transition = noop2  # type: ignore[assignment]

    async def run2() -> None:
        await drive(plain, {"print": {"bed_temper": 60.0}})
        check("没有自适应风道组件的机型：左(辅助) 不冒出来",
              not plain.states[1].secondary_aux_installed
              and plain.states[1].secondary_aux_fan_pct is None)

    asyncio.run(run2())


def main() -> int:
    test_deep_merge_pure()
    test_merge_keeps_chamber()
    test_left_aux_remembered()
    print("\n" + "─" * 52)
    print(f"通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        for name in FAILED:
            print(f"  未通过：{name}")
        return 1
    print("报文合并与状态记忆验证通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
