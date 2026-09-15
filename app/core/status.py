"""把拓竹云 MQTT 上报的 report 报文解析成结构化状态。

报文字段来源（已核对）：
- greghesp/ha-bambulab pybambu/models.py（AMS tray 字段、tray_now 语义、hms）
- Doridian/OpenBambuAPI（MQTT 主题与字段）
- coelacant1/Bambu-Lab-Cloud-API（AMS / filament 字段表）

关键的几个语义：
- tray_now: 255=无料，254=外挂料盘，其余 = ams_id*4 + tray_id
- tray_exist_bits: 十六进制位串，第 (ams_id*4+tray_id) 位为 1 表示该槽位有料
- tray[].remain: 剩余百分比（100=满卷）。无 RFID 的第三方料盘为 -1
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

    cooling_fan: int = 0
    aux_fan: int = 0
    chamber_fan: int = 0
    heatbreak_fan: int = 0

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
    state.chamber_temper = _as_float(block.get("chamber_temper"))

    state.cooling_fan = _as_int(block.get("cooling_fan_speed"))
    state.aux_fan = _as_int(block.get("big_fan1_speed"))
    state.chamber_fan = _as_int(block.get("big_fan2_speed"))
    state.heatbreak_fan = _as_int(block.get("heatbreak_fan_speed"))

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
