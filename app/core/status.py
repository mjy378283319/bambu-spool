"""把拓竹云 MQTT 上报的 report 报文解析成结构化状态。

报文字段来源（已核对）：
- greghesp/ha-bambulab pybambu/models.py（AMS tray 字段、tray_now 语义、hms）
- Doridian/OpenBambuAPI（MQTT 主题与字段）
- coelacant1/Bambu-Lab-Cloud-API（AMS / filament 字段表）

关键的几个语义：
- tray_now: 255=无料，254=外挂料盘，其余 = ams_id*4 + tray_id
- tray_exist_bits: 十六进制位串，第 (ams_id*4+tray_id) 位为 1 表示该槽位有料
- tray[].remain: 剩余百分比（100=满卷）。无 RFID 的第三方料盘为 -1
- 风扇 *fan_speed 上报的是 0-15 的 PWM 档位，不是百分比（见 fan_percent）
- 仓温：P2S/新固件在 device.ctc.info.temp（低 16 位当前值、高 16 位目标值），
  X1 等机型在 print.chamber_temper
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from ..catalog import (
    GCODE_STATE_LABELS,
    STAGE_LABELS,
    hms_module,
    hms_severity,
    hms_text,
    normalize_color,
)

EMPTY_COLOR_MARKERS = {"", "00000000", "000000", "#000000"}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return round(float(value), 2)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _bit_set(bits_hex: str, index: int) -> Optional[bool]:
    """读取十六进制位串的第 index 位。无法解析时返回 None。"""
    if not bits_hex:
        return None
    text = str(bits_hex).strip()
    try:
        value = int(text, 16)
    except (TypeError, ValueError):
        return None
    if index < 0:
        return None
    # 位串宽度不够时返回 None：AMS HT 的 id 是 128，算出来是第 512 位，
    # 远超 tray_exist_bits 的 16 位宽度，硬读只会拿到 0 并把有料的槽位误判成空。
    # 返回 None 让 _parse_tray 退回「按 tray 内容判断」，HT 槽位才不会整排变空。
    if index >= len(text) * 4:
        return None
    return bool((value >> index) & 1)


# ── 自适应风道切换组件（P2S / X2）里的部件 ──────────────────────
# device.airduct.parts[] 是真机报文里的部件列表，靠 id 认身份、靠 func 区分品类：
#   func == 0  → 风扇类部件，state 就是转速百分比
#   func == 6 / 8 → 风门 / 风道切换机构（真机 P2S 是 {"func":6,"id":32}，
#                  另一个固件版本报 func 8，所以只按 id 认、不靠 func 认）
#
# 真机 P2S 样本（research/_MOCK-P2S.json）:
#   parts   = [{"func":0,"id":16,"state":90}, {"func":6,"id":32,"state":0}]
#   modeList= [{"ctrl":[16,32,160]}, {"ctrl":[16,32],"off":[160]}]
# 注意 **big_fan1_speed / big_fan2_speed 在这份真机报文里都是 0** —— P2S 的
# 辅助风扇不在 big_fan1 里报，而是在 airduct 里报，所以光看 big_fan1 永远显示 0%。
#
# 拓竹官方 App「空调系统 / 冷却模式」对 P2S 显示 4 行，命名与本文件一致：
#   部件 / 右(辅助) / 左(辅助) / 外排
# 官方 Wiki（P2S 冷却风扇系统、风扇介绍）说明：
#   - 部件冷却风扇：工具头前盖组件内置（M106 P1）
#   - 右(辅助)：自适应风道切换组件自带的风扇，装在腔室右侧（M106 P2）
#   - 左(辅助)：选配的 12W 左侧辅助风扇（M106 P10），没装就不该显示数值
#   - 外排：选配的外排风扇套件，装在背板，自带控制板（M142 自动外排）
#     → 套件装好后会被并入空调系统，外排不在 parts 的固定三个 id 里。
AIRDUCT_FAN_FUNC = 0
# 自适应风道切换组件自带的辅助风扇 → 面板「右(辅助)」
AIRDUCT_PART_RIGHT_AUX = 16
# 风道切换风门，不是风扇，面板不显示
AIRDUCT_PART_FLAP = 32
# 左侧选配辅助风扇 → 面板「左(辅助)」；ha-bambulab 用 id==160 认这台
AIRDUCT_PART_LEFT_AUX = 160
# 已知的非风扇部件，识别「剩余的风扇部件」时要排掉
AIRDUCT_NON_FAN_IDS = frozenset({AIRDUCT_PART_FLAP})


def fan_percent(raw: Any) -> int:
    """把风扇上报值换算成百分比。

    拓竹的 cooling_fan_speed / big_fan1_speed / big_fan2_speed / heatbreak_fan_speed
    上报的是 **0-15 的 PWM 档位**，不是百分比——直接当百分比显示会变成
    「14%」这种明显不对的数字（实际是 93%）。官方 App 与 ha-bambulab 都按
    value / 15 * 100 换算、再按 10% 取整（风扇本身就按 10% 一档调节），这里照做：
    14 → 90%、15 → 100%、10 → 70%、0 → 0%。
    """
    value = _as_int(raw, -1)
    if value < 0:
        return 0
    percent = min(value, 15) / 15 * 100
    return max(0, min(100, int(round(percent / 10.0)) * 10))


def airduct_part_states(block: dict) -> dict[int, int]:
    """自适应风道切换组件里各部件的 state（百分比），按部件 id 索引。

    `state` 本身就是百分比（0-100），**不能再除以 15**，直接透传。
    没装这个组件的机型（X1 / P1 / A1）不上报 device.airduct，返回空字典，
    界面据此隐藏这些行。
    """
    device = block.get("device")
    if not isinstance(device, dict):
        return {}
    airduct = device.get("airduct")
    if not isinstance(airduct, dict):
        return {}
    out: dict[int, int] = {}
    for part in airduct.get("parts") or []:
        if not isinstance(part, dict):
            continue
        part_id = _as_int(part.get("id"), -1)
        if part_id < 0:
            continue
        out[part_id] = max(0, min(100, _as_int(part.get("state"))))
    return out


def airduct_fans(block: dict) -> list[int]:
    """组件里的**风扇**转速（百分比），按上报顺序。

    风门（id 32）不算风扇，会被排掉；其余部件一律按风扇看待 ——
    这样选了外排套件、固件多报一个部件时也能自动带出来。
    func 存在且等于 0 的部件也算（兜底认法，id 表没覆盖的机型靠它）。
    """
    parts = _airduct_parts(block)
    out: list[int] = []
    for part in parts:
        part_id = _as_int(part.get("id"), -1)
        if part_id in AIRDUCT_NON_FAN_IDS:
            continue
        is_fan = (
            _as_int(part.get("func"), -1) == AIRDUCT_FAN_FUNC
            or part_id in (AIRDUCT_PART_RIGHT_AUX, AIRDUCT_PART_LEFT_AUX)
        )
        if is_fan:
            out.append(max(0, min(100, _as_int(part.get("state")))))
    return out


def _airduct_parts(block: dict) -> list[dict]:
    """取 device.airduct.parts 里结构合法的条目。"""
    device = block.get("device")
    if not isinstance(device, dict):
        return []
    airduct = device.get("airduct")
    if not isinstance(airduct, dict):
        return []
    return [p for p in (airduct.get("parts") or []) if isinstance(p, dict)]


def airduct_fan_percent(block: dict) -> Optional[int]:
    """组件自带那台辅助部件冷却风扇（右辅助）的转速；没有该组件时返回 None。"""
    return airduct_part_states(block).get(AIRDUCT_PART_RIGHT_AUX)


def airduct_left_aux_percent(block: dict) -> Optional[int]:
    """左侧选配辅助风扇的转速；没装返回 None。"""
    return airduct_part_states(block).get(AIRDUCT_PART_LEFT_AUX)


def airduct_other_fan_percent(block: dict) -> Optional[int]:
    """除右/左辅助、风门之外的**额外风扇部件**的转速。

    外排风扇套件自带控制板、并入空调系统后，很可能就以新增部件的形式出现。
    认出来就优先用它当「外排」的读数，认不出来再退回 big_fan2。
    """
    known = {AIRDUCT_PART_RIGHT_AUX, AIRDUCT_PART_LEFT_AUX} | set(AIRDUCT_NON_FAN_IDS)
    for part in _airduct_parts(block):
        part_id = _as_int(part.get("id"), -1)
        if part_id in known or part_id < 0:
            continue
        if _as_int(part.get("func"), -1) == AIRDUCT_FAN_FUNC:
            return max(0, min(100, _as_int(part.get("state"))))
    return None


@dataclass
class TrayState:
    ams_id: int = 0
    tray_id: int = 0
    occupied: bool = False
    tray_type: str = ""
    sub_brands: str = ""
    color: str = "#000000"
    color_raw: str = ""
    remain: int = -1
    tray_weight: float = 1000.0
    diameter: float = 1.75
    info_idx: str = ""
    tag_uid: str = "0000000000000000"
    tray_uuid: str = ""
    k: float = 0.0
    drying_temp: float = 0.0
    drying_time: float = 0.0

    @property
    def slot_index(self) -> int:
        return self.ams_id * 4 + self.tray_id

    @property
    def has_rfid(self) -> bool:
        uid = (self.tag_uid or "").strip().upper()
        return bool(uid) and uid not in ("0", "0000000000000000", "00" * 8)

    @property
    def label(self) -> str:
        if not self.occupied:
            return "空槽位"
        parts = [p for p in (self.sub_brands or self.tray_type,) if p]
        return " ".join(parts) or "未识别耗材"


@dataclass
class AmsUnit:
    ams_id: int = 0
    model: str = "AMS"
    humidity: Any = ""
    temp: float = 0.0
    trays: list[TrayState] = field(default_factory=list)


@dataclass
class HmsError:
    attr: int = 0
    code: int = 0
    text: str = ""
    severity: str = "未知"
    module: str = "未知"


@dataclass
class PrinterState:
    serial: str = ""
    online: bool = False
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    gcode_state: str = "OFFLINE"
    state_label: str = "离线"
    stage_id: int = -1
    stage_label: str = "空闲"
    progress: int = 0
    remaining_minutes: int = 0
    layer_num: int = 0
    total_layer_num: int = 0
    speed_level: int = 0

    task_id: str = ""
    subtask_name: str = ""
    gcode_file: str = ""
    print_type: str = ""

    nozzle_temper: float = 0.0
    nozzle_target: float = 0.0
    bed_temper: float = 0.0
    bed_target: float = 0.0
    chamber_temper: float = 0.0
    chamber_target: float = 0.0

    # 都是百分比（0/10/…/100），由 fan_percent() 从原始档位换算
    cooling_fan_pct: int = 0
    aux_fan_pct: int = 0
    chamber_fan_pct: int = 0
    heatbreak_fan_pct: int = 0
    # 自适应风道切换组件自带的辅助风扇（P2S/X2「右(辅助)」）；没有该组件时为 None
    airduct_fan_pct: Optional[int] = None
    # 「左(辅助)」——左侧选配那台；只有上报了才不是 None
    secondary_aux_fan_pct: Optional[int] = None
    # 「外排」——外排风扇套件；没装 / 没上报时退回 big_fan2 档位，再没有才是 None
    exhaust_fan_pct: Optional[int] = None

    wifi_signal: str = ""
    lights: list[str] = field(default_factory=list)
    hms: list[HmsError] = field(default_factory=list)

    ams_units: list[AmsUnit] = field(default_factory=list)
    tray_now: int = 255
    external_spool: Optional[TrayState] = None
    # dev mode 关闭时固件要求对控制指令做 X.509 签名
    mqtt_signature_required: bool = False

    @property
    def is_active(self) -> bool:
        return self.gcode_state in ("PREPARE", "RUNNING", "PAUSE")

    @property
    def all_trays(self) -> list[TrayState]:
        trays: list[TrayState] = []
        for unit in self.ams_units:
            trays.extend(unit.trays)
        return trays

    @property
    def loaded_trays(self) -> list[TrayState]:
        return [t for t in self.all_trays if t.occupied]

    def tray_by_slot(self, slot_index: int) -> Optional[TrayState]:
        for tray in self.all_trays:
            if tray.slot_index == slot_index:
                return tray
        return None


def _parse_tray(raw: dict, ams_id: int, tray_id: int, occupied: Optional[bool]) -> TrayState:
    color_raw = _as_str(raw.get("tray_color"))
    tray_type = _as_str(raw.get("tray_type"))
    info_idx = _as_str(raw.get("tray_info_idx"))

    if occupied is None:
        # 没有位串可用时，用内容判断是否装料
        occupied = bool(tray_type or info_idx) and color_raw.strip().upper() not in EMPTY_COLOR_MARKERS
        if not occupied and color_raw.strip().upper() not in EMPTY_COLOR_MARKERS and raw.get("tag_uid"):
            occupied = True

    return TrayState(
        ams_id=ams_id,
        tray_id=tray_id,
        occupied=bool(occupied),
        tray_type=tray_type,
        sub_brands=_as_str(raw.get("tray_sub_brands")),
        color=normalize_color(color_raw),
        color_raw=color_raw,
        remain=_as_int(raw.get("remain"), -1),
        tray_weight=_as_float(raw.get("tray_weight"), 1000.0),
        diameter=_as_float(raw.get("tray_diameter"), 1.75),
        info_idx=info_idx,
        tag_uid=_as_str(raw.get("tag_uid")),
        tray_uuid=_as_str(raw.get("tray_uuid")),
        k=_as_float(raw.get("k")),
        drying_temp=_as_float(raw.get("drying_temp")),
        drying_time=_as_float(raw.get("drying_time")),
    )


def parse_report(payload: dict, serial: str = "") -> Optional[PrinterState]:
    """解析一条 report 消息。不含 print 块时返回 None。"""
    block = payload.get("print")
    if not isinstance(block, dict):
        return None

    state = PrinterState(serial=serial, online=True)

    state.gcode_state = _as_str(block.get("gcode_state"), "UNKNOWN").upper()
    state.state_label = GCODE_STATE_LABELS.get(state.gcode_state, state.gcode_state)
    state.progress = _as_int(block.get("mc_percent"))
    state.remaining_minutes = _as_int(block.get("mc_remaining_time"))
    state.layer_num = _as_int(block.get("layer_num"))
    state.total_layer_num = _as_int(block.get("total_layer_num"))
    state.speed_level = _as_int(block.get("spd_lvl"))

    stage = _as_int(block.get("stg_cur"), -1)
    state.stage_id = stage
    state.stage_label = STAGE_LABELS.get(stage, f"阶段 {stage}" if stage >= 0 else "空闲")

    state.task_id = _as_str(block.get("task_id"))
    state.subtask_name = _as_str(block.get("subtask_name"))
    state.gcode_file = _as_str(block.get("gcode_file"))
    state.print_type = _as_str(block.get("print_type"))

    state.nozzle_temper = _as_float(block.get("nozzle_temper"))
    state.nozzle_target = _as_float(block.get("nozzle_target_temper"))
    state.bed_temper = _as_float(block.get("bed_temper"))
    state.bed_target = _as_float(block.get("bed_target_temper"))

    # 仓温：P2S / 新固件放在 device.ctc.info.temp，是个 32 位打包值
    # （低 16 位 = 当前温度，高 16 位 = 目标温度）；X1 等老机型直接在
    # print.chamber_temper。原来只读后者，所以 P2S 上仓温一直是「—」。
    if block.get("chamber_temper") is not None:
        state.chamber_temper = _as_float(block.get("chamber_temper"))
    else:
        ctc = block.get("device")
        ctc = ctc.get("ctc") if isinstance(ctc, dict) else None
        ctc = ctc.get("info") if isinstance(ctc, dict) else None
        packed = ctc.get("temp") if isinstance(ctc, dict) else None
        if packed is not None:
            value = _as_int(packed)
            state.chamber_temper = float(value & 0xFFFF)
            state.chamber_target = float((value >> 16) & 0xFFFF)

    state.cooling_fan_pct = fan_percent(block.get("cooling_fan_speed"))
    state.aux_fan_pct = fan_percent(block.get("big_fan1_speed"))
    state.chamber_fan_pct = fan_percent(block.get("big_fan2_speed"))
    state.heatbreak_fan_pct = fan_percent(block.get("heatbreak_fan_speed"))

    # P2S/X2 的辅助风扇报在自适应风道组件里，按部件 id 取，比 big_fan1 可靠。
    # 没装该组件的机型（X1/P1/A1）这里就是 None，界面改走 big_fan1。
    state.airduct_fan_pct = airduct_fan_percent(block)
    state.secondary_aux_fan_pct = airduct_left_aux_percent(block)

    # 外排：套件并入空调系统后会多报一个风扇部件，优先用它；
    # 没有就退回 big_fan2（X 系列与 P2S 外排/腔体都走这一路档位）
    extra = airduct_other_fan_percent(block)
    if extra is not None:
        state.exhaust_fan_pct = extra
    elif block.get("big_fan2_speed") is not None:
        state.exhaust_fan_pct = state.chamber_fan_pct

    state.wifi_signal = _as_str(block.get("wifi_signal"))

    for light in block.get("lights_report") or []:
        if isinstance(light, dict) and light.get("mode") == "on":
            state.lights.append(_as_str(light.get("node"), "light"))

    for item in block.get("hms") or []:
        if not isinstance(item, dict):
            continue
        attr = _as_int(item.get("attr"))
        code = _as_int(item.get("code"))
        state.hms.append(
            HmsError(
                attr=attr,
                code=code,
                text=hms_text(attr, code),
                severity=hms_severity(attr),
                module=hms_module(attr),
            )
        )

    # print.fun 是十六进制位串，bit 29 表示固件要求 MQTT 指令签名
    fun = _as_str(block.get("fun"))
    if fun:
        try:
            state.mqtt_signature_required = bool((int(fun, 16) >> 28) & 1)
        except ValueError:
            pass

    # ── AMS ──
    ams_block = block.get("ams") or {}
    exist_bits = _as_str(ams_block.get("tray_exist_bits"))
    state.tray_now = _as_int(ams_block.get("tray_now"), 255)

    units: list[AmsUnit] = []
    for raw_unit in ams_block.get("ams") or []:
        if not isinstance(raw_unit, dict):
            continue
        ams_id = _as_int(raw_unit.get("id"))
        unit = AmsUnit(
            ams_id=ams_id,
            model=_as_str(raw_unit.get("info"), "AMS").split(";")[0] or "AMS",
            humidity=raw_unit.get("humidity", ""),
            temp=_as_float(raw_unit.get("temp")),
        )
        trays_raw = raw_unit.get("tray") or []
        for idx, raw_tray in enumerate(trays_raw):
            if not isinstance(raw_tray, dict):
                continue
            tray_id = _as_int(raw_tray.get("id"), idx)
            unit.trays.append(
                _parse_tray(raw_tray, ams_id, tray_id, _bit_set(exist_bits, ams_id * 4 + tray_id))
            )
        units.append(unit)
    state.ams_units = units

    # AMS 型号兼容：新固件把型号放在 ams[].info，旧固件没有
    for unit in state.ams_units:
        if not unit.model or unit.model == "AMS":
            raw_ids = ams_block.get("ams") or []
            for raw_unit in raw_ids:
                if isinstance(raw_unit, dict) and _as_int(raw_unit.get("id")) == unit.ams_id:
                    unit.model = _as_str(raw_unit.get("info"), "AMS").split(";")[0] or "AMS"

    # ── 外挂料盘 ──
    vt = block.get("vt_tray")
    if isinstance(vt, dict):
        state.external_spool = _parse_tray(vt, ams_id=-1, tray_id=0, occupied=None)

    return state


def diff_summary(old: Optional[PrinterState], new: PrinterState) -> list[str]:
    """生成人类可读的变化摘要，用于时间线。"""
    if old is None:
        return []
    changes: list[str] = []
    if old.gcode_state != new.gcode_state:
        changes.append(f"状态 {old.state_label} → {new.state_label}")
    if old.task_id != new.task_id and new.task_id:
        changes.append(f"新任务 {new.subtask_name or new.task_id}")
    loaded_old = {(t.ams_id, t.tray_id): t.info_idx for t in old.loaded_trays}
    loaded_new = {(t.ams_id, t.tray_id): t.info_idx for t in new.loaded_trays}
    for key in set(loaded_old) | set(loaded_new):
        if loaded_old.get(key) != loaded_new.get(key):
            ams_id, tray_id = key
            changes.append(f"AMS{ams_id + 1} 槽位{tray_id + 1} 耗材变化")
    for err in new.hms:
        if not any(e.text == err.text for e in old.hms):
            changes.append(f"报错 {err.text}")
    return changes
