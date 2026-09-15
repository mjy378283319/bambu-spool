"""风扇档位换算、自适应风道组件与仓温解析自测。

覆盖（这些都是拿真机报文核对过的坑）：
  - fan_percent：拓竹的 cooling_fan_speed / big_fan1_speed / big_fan2_speed /
    heatbreak_fan_speed 上报的是 **0-15 的 PWM 档位**，不是百分比。
    直接当百分比显示就会变成「14%」这种明显不对的数字（实际是 90%）。
    口径与官方 App、ha-bambulab 一致：value / 15 * 100 再按 10% 取整。
  - airduct_fans：自适应风道切换组件（P2S / X2）的风扇转速。
    真机 P2S 样本（ha-bambulab MOCK-P2S.json）里
        parts = [{"func":0,"id":16,"state":90}, {"func":6,"id":32,"state":0}]
    所以判定依据是 **func==0 表示风扇、func==6 表示风门**，另外兼容 ha-bambulab
    用的 id==160。`state` 本身就是百分比，**不能再除以 15**。
    ⚠️ 关键：P2S 真机上 big_fan1_speed / big_fan2_speed 恒为 0，
    它的辅助部件冷却风扇只在 airduct 里报 —— 只看 big_fan1 会永远显示 0%。
  - 仓温：P2S / 新固件在 device.ctc.info.temp（低 16 位=当前值、高 16 位=目标值），
    X1 等机型在 print.chamber_temper。只认后者的话 P2S 上仓温永远是「—」。
  - state_dict：fans 五个通道与 chamber_target 都要下发，且 aux 要用 airduct 的值。

运行： python tests/test_fans_temps.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ["BAMBU_MOCK"] = "1"
os.environ["DATA_DIR"] = os.path.join(ROOT, "data", "testfans")

from app.core.hub import hub  # noqa: E402
from app.core.status import (  # noqa: E402
    airduct_fan_percent,
    airduct_fans,
    fan_percent,
    parse_report,
)

PASSED: list[str] = []
FAILED: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(label)
        print(f"  [通过] {label}")
    else:
        FAILED.append(label)
        print(f"  [失败] {label} {detail}")


def parts(*pairs):
    """按 (func, id, state) 生成 airduct 块。"""
    return {
        "device": {
            "airduct": {
                "parts": [
                    {"func": f, "id": i, "state": s} for (f, i, s) in pairs
                ]
            }
        }
    }


# ── 1. 风扇档位换算 ─────────────────────────────────────────────
def test_fan_percent() -> None:
    print("== 风扇 0-15 档位 → 百分比 ==")
    check("NaN 值按 0 处理", fan_percent(None) == 0 and fan_percent("") == 0)
    check("非法值按 0 处理", fan_percent("abc") == 0)
    check("负值按 0 处理", fan_percent(-3) == 0)
    check("0 档 → 0%", fan_percent("0") == 0)

    check("15 档 → 100%", fan_percent("15") == 100, str(fan_percent("15")))
    check("14 档 → 90%（不是 14%！）", fan_percent("14") == 90, str(fan_percent("14")))
    check("13 档 → 90%", fan_percent(13) == 90, str(fan_percent(13)))
    check("10 档 → 70%", fan_percent("10") == 70, str(fan_percent("10")))
    check("1 档 → 10%", fan_percent(1) == 10, str(fan_percent(1)))
    check("超范围值封顶 100%", fan_percent(99) == 100, str(fan_percent(99)))

    # 这是这次修的 bug：旧代码把档位直接当百分比，屏幕上会出现「14%」这种数字
    check("档位不再被当成百分比直接显示", fan_percent("14") != 14)


# ── 2. 自适应风道组件里的风扇（P2S / X2） ────────────────────────
def test_airduct_fans() -> None:
    print("== 自适应风道组件（airduct.parts） ==")

    # 真机 P2S 样本：func 0 = 风扇（state 90），func 6 = 风门
    real = parts((0, 16, 90), (6, 32, 0))
    check("真机 P2S 只认 func==0 那台风扇", airduct_fans(real) == [90], str(airduct_fans(real)))
    check("真机样本取第一台就是辅助部件冷却风扇", airduct_fan_percent(real) == 90)

    check("state 已是百分比，直接透传", airduct_fans(parts((0, 16, 70))) == [70])
    check("state=0 也认（风扇停转）", airduct_fans(parts((0, 16, 0))) == [0])
    check("风门 func==6 不当风扇", airduct_fans(parts((6, 32, 90))) == [])
    check("没装的机型 → 空列表", airduct_fans({"device": {}}) == [])
    check("整条 device 缺失 → 空列表", airduct_fans({}) == [])
    check("老机型没有 device 块 → 空列表", airduct_fans({"big_fan1_speed": "5"}) == [])
    check("没有组件时单值接口返回 None", airduct_fan_percent({"big_fan1_speed": "5"}) is None)
    check("state 超范围封顶 100", airduct_fans(parts((0, 16, 150))) == [100])

    # 兼容：ha-bambulab 用 id==160 认「第二辅助风扇」
    check("id==160 即使 func 非 0 也认", airduct_fans(parts((9, 160, 40))) == [40])

    # 装了左侧那台选配风扇就有两台
    two = parts((0, 16, 90), (0, 160, 40))
    check("两台风扇按上报顺序返回", airduct_fans(two) == [90, 40], str(airduct_fans(two)))
    check("单值接口只取第一台", airduct_fan_percent(two) == 90)

    check("部件不是字典也不炸", airduct_fans({"device": {"airduct": {"parts": ["x"]}}}) == [])
    check("parts 缺失不炸", airduct_fans({"device": {"airduct": {}}}) == [])


# ── 3. 仓温两个来源 ─────────────────────────────────────────────
def test_chamber_temp() -> None:
    print("== 仓温（chamber_temper / device.ctc） ==")
    old = parse_report({"print": {"chamber_temper": 31.5}})
    check("老机型 chamber_temper 生效", old is not None and old.chamber_temper == 31.5,
          str(old and old.chamber_temper))

    # P2S：ctc.info.temp 是 32 位打包值，低 16 位当前值、高 16 位目标值
    packed = parse_report({"print": {"device": {"ctc": {"info": {"temp": (40 << 16) | 37}}}}})
    check("ctc 打包值解出当前仓温 37", packed is not None and packed.chamber_temper == 37.0,
          str(packed and packed.chamber_temper))
    check("ctc 打包值解出目标仓温 40", packed is not None and packed.chamber_target == 40.0,
          str(packed and packed.chamber_target))

    only_now = parse_report({"print": {"device": {"ctc": {"info": {"temp": 43}}}}})
    check("ctc 只带当前值时目标为 0", only_now is not None and only_now.chamber_temper == 43.0
          and only_now.chamber_target == 0.0)

    both = parse_report({"print": {"chamber_temper": 30.0, "device": {"ctc": {"info": {"temp": 43}}}}})
    check("两个来源都有时优先 chamber_temper", both is not None and both.chamber_temper == 30.0,
          str(both and both.chamber_temper))

    none = parse_report({"print": {}})
    check("都没有时仓温为 0", none is not None and none.chamber_temper == 0.0)
    check("device 不是字典时不炸", parse_report({"print": {"device": "x"}}) is not None)


# ── 4. 真机 P2S 报文（字段取自 ha-bambulab 的 MOCK-P2S.json） ────
REAL_P2S = {
    "gcode_state": "RUNNING",
    "mc_percent": 89,
    "bed_temper": 55.0,
    "bed_target_temper": 55.0,
    "nozzle_temper": 220.0,
    "nozzle_target_temper": 220.0,
    # 真机这一档 big_fan1 / big_fan2 都是 "0"
    "cooling_fan_speed": "10",
    "big_fan1_speed": "0",
    "big_fan2_speed": "0",
    "heatbreak_fan_speed": "15",
    "aux_part_fan": True,
    "device": {
        "ctc": {"info": {"temp": 37}, "state": 0},
        "airduct": {
            "modeCur": 0,
            "modeList": [{"modeId": 0, "ctrl": [16, 32], "off": []}],
            "parts": [
                {"func": 0, "id": 16, "state": 90},
                {"func": 6, "id": 32, "state": 0},
            ],
        },
    },
}


def test_real_p2s_report() -> None:
    print("== 真机 P2S 报文 ==")
    state = parse_report({"print": REAL_P2S})
    check("解析成功", state is not None)
    if state is None:
        return
    check("部件冷却风扇 70%（10/15）", state.cooling_fan_pct == 70, str(state.cooling_fan_pct))
    check("热端风扇 100%（15/15）", state.heatbreak_fan_pct == 100, str(state.heatbreak_fan_pct))
    check("big_fan1 真机为 0，不能拿它当辅助风扇",
          state.aux_fan_pct == 0, str(state.aux_fan_pct))
    check("辅助部件冷却风扇从 airduct 取到 90%",
          state.airduct_fan_pct == 90, str(state.airduct_fan_pct))
    check("真机 P2S 没装左侧选配风扇 → secondary 为 None",
          state.secondary_aux_fan_pct is None, str(state.secondary_aux_fan_pct))
    check("仓温 37℃", state.chamber_temper == 37.0, str(state.chamber_temper))
    check("热床 55/55℃", state.bed_temper == 55.0 and state.bed_target == 55.0)
    check("喷嘴 220/220℃", state.nozzle_temper == 220.0 and state.nozzle_target == 220.0)

    payload = hub.state_dict(state, 1)
    fans = payload.get("fans") or {}
    for key in ("cooling", "aux", "chamber", "heatbreak", "secondary"):
        check(f"下发风扇通道 {key}", key in fans, str(fans))
    check("下发的 aux 用的是 airduct 的值（90）而不是 big_fan1（0）",
          fans.get("aux") == 90, str(fans))
    check("下发 chamber（真机 0，P2S 无此硬件）", fans.get("chamber") == 0, str(fans))
    check("下发 chamber_target", payload.get("chamber_target") == 0.0, str(payload.get("chamber_target")))
    check("下发仓温", payload.get("chamber_temper") == 37.0, str(payload.get("chamber_temper")))
    check("P2S 三台风扇都能取到值（部件 / 辅助 / 热端）",
          fans.get("cooling") == 70 and fans.get("aux") == 90 and fans.get("heatbreak") == 100,
          str(fans))

    # 装了左侧选配风扇的机器
    with_left = parse_report({"print": {**REAL_P2S, "device": {
        "ctc": REAL_P2S["device"]["ctc"],
        "airduct": {"parts": [
            {"func": 0, "id": 16, "state": 90},
            {"func": 0, "id": 160, "state": 40},
            {"func": 6, "id": 32, "state": 0},
        ]},
    }}})
    check("装了左侧风扇时 secondary 取到 40%",
          with_left is not None and with_left.secondary_aux_fan_pct == 40,
          str(with_left and with_left.secondary_aux_fan_pct))
    check("装了左侧风扇时 aux 仍是 90%",
          with_left is not None and (hub.state_dict(with_left, 1)["fans"] or {}).get("aux") == 90)


if __name__ == "__main__":
    test_fan_percent()
    test_airduct_fans()
    test_chamber_temp()
    test_real_p2s_report()
    print(f"\n通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        print("失败项：", FAILED)
        sys.exit(1)
    print("全部通过")
