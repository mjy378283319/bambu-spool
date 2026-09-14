"""扣重引擎：把拓竹云任务记录里的每槽位克重，落到具体的料盘上。

云任务记录（GET /v1/user-service/my/tasks）每条含：
  weight                 本次打印总耗材重量（克）
  length                 总长度
  amsDetailMapping[]     每个用料槽位一条：
      ams        槽位编号（低置信度，只作辅助线索）
      filamentId 耗材预设编号，与 AMS 上报的 tray_info_idx 同源（如 GFA00 / GFL99）
      sourceColor / targetColor  该槽位用到的颜色（RRGGBBAA）
      weight     该槽位本次消耗克重
      filamentType 材料类型

匹配策略按置信度从高到低依次尝试，并把用到的策略写进记录，
界面上会显示匹配依据，用户可随时纠正。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from sqlmodel import Session, select

from ..catalog import normalize_color
from ..models import PrintJob, SlotBinding, Spool, UsageRecord, utcnow
from .status import PrinterState, TrayState


@dataclass
class FilamentUsage:
    index: int = 0
    filament_id: str = ""
    material: str = ""
    color: str = "#000000"
    weight_g: float = 0.0
    ams_id: int = -1
    tray_id: int = -1
    slot_label: str = ""
    spool_id: Optional[int] = None
    spool_name: str = ""
    match_strategy: str = "未匹配"
    deducted_g: float = 0.0
    deducted: bool = False
    # 本条用量消耗的料材费用（¥），扣重时按「单价 × 克重」折算并快照保存。
    cost: float = 0.0


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return round(float(value), 3)
    except (TypeError, ValueError):
        return default


def usage_cost(spool: "Spool | None", weight_g: float) -> float:
    """按「单价 × 克重」折算一条用量的费用（¥）。

    单价 = 整盘价 / 满盘净重。未登记价格、净重为 0 或用量非正时返回 0。
    """
    if spool is None or weight_g <= 0 or spool.initial_weight <= 0 or spool.price <= 0:
        return 0.0
    return round(spool.price / spool.initial_weight * weight_g, 4)


def _decode_ams_hint(value: Any) -> Optional[tuple[int, int]]:
    """ams 字段编码为 ams_id*4+tray_id，与 tray_now 同构。254/255 表示外挂/无。"""
    try:
        num = int(value)
    except (TypeError, ValueError):
        return None
    if num in (254, 255) or num < 0:
        return None
    return num // 4, num % 4


def _slot_label(ams_id: int, tray_id: int) -> str:
    if ams_id < 0:
        return "外挂料盘"
    return f"AMS {ams_id + 1} · 槽位 {tray_id + 1}"


def match_entry(
    entry: dict,
    loaded: list[TrayState],
    external: Optional[TrayState],
    claimed: set[tuple[int, int]],
) -> tuple[Optional[TrayState], str]:
    """为一条 amsDetailMapping 找到对应的槽位。"""
    filament_id = str(entry.get("filamentId") or "").strip().upper()
    color = normalize_color(str(entry.get("targetColor") or entry.get("sourceColor") or ""))
    hint = _decode_ams_hint(entry.get("ams"))

    available = [t for t in loaded if (t.ams_id, t.tray_id) not in claimed]

    # 1) 耗材编号一致 —— 最强依据
    by_id = [t for t in available if t.info_idx.strip().upper() == filament_id] if filament_id else []
    if by_id:
        same_color = [t for t in by_id if t.color.upper() == color.upper()]
        if len(same_color) == 1:
            return same_color[0], "耗材编号 + 颜色一致"
        if len(by_id) == 1:
            return by_id[0], "耗材编号一致"
        if hint:
            for tray in by_id:
                if (tray.ams_id, tray.tray_id) == hint:
                    return tray, "耗材编号 + 槽位线索"

    # 2) 颜色一致
    by_color = [t for t in available if t.color.upper() == color.upper() and color != "#000000"]
    if len(by_color) == 1:
        return by_color[0], "颜色一致"
    if len(by_color) > 1 and hint:
        for tray in by_color:
            if (tray.ams_id, tray.tray_id) == hint:
                return tray, "颜色一致 + 槽位线索"

    # 3) 槽位线索
    if hint:
        for tray in available:
            if (tray.ams_id, tray.tray_id) == hint:
                return tray, "槽位线索"

    # 4) 只有一个候选时直接采用
    if len(available) == 1:
        return available[0], "唯一在机料盘"

    # 5) 没写耗材编号的条目通常来自外挂料盘
    if not filament_id and external and external.occupied:
        return external, "外挂料盘"

    return None, "未匹配"


def build_usages(task: dict, state: Optional[PrinterState]) -> list[FilamentUsage]:
    """把云端任务记录 + 当前槽位状态，变成逐条用量。"""
    mapping = task.get("amsDetailMapping") or []
    loaded = state.loaded_trays if state else []
    external = state.external_spool if state else None

    usages: list[FilamentUsage] = []
    claimed: set[tuple[int, int]] = set()
    total = _as_float(task.get("weight"))
    counted = 0.0

    for idx, entry in enumerate(mapping):
        if not isinstance(entry, dict):
            continue
        weight = _as_float(entry.get("weight"))
        counted += weight
        tray, strategy = match_entry(entry, loaded, external, claimed)
        if tray is not None:
            claimed.add((tray.ams_id, tray.tray_id))

        usages.append(
            FilamentUsage(
                index=idx,
                filament_id=str(entry.get("filamentId") or ""),
                material=str(entry.get("filamentType") or (tray.tray_type if tray else "")),
                color=normalize_color(str(entry.get("targetColor") or entry.get("sourceColor") or "")),
                weight_g=weight,
                ams_id=tray.ams_id if tray else -1,
                tray_id=tray.tray_id if tray else -1,
                slot_label=_slot_label(tray.ams_id, tray.tray_id) if tray else "",
                match_strategy=strategy,
            )
        )

    # 云端总量与明细对不上时，把差额补到未匹配的条目上
    if total > 0 and abs(counted - total) > 0.05 and usages and counted == 0:
        usages[0].weight_g = total

    return usages


def resolve_spools(session: Session, printer_id: int, usages: list[FilamentUsage]) -> None:
    """根据槽位绑定关系，给每条用量找到料盘。"""
    bindings = session.exec(
        select(SlotBinding).where(SlotBinding.printer_id == printer_id)
    ).all()
    index = {(b.ams_id, b.tray_id): b.spool_id for b in bindings if b.spool_id}

    spool_ids = {sid for sid in index.values() if sid}
    spools = {}
    if spool_ids:
        for spool in session.exec(select(Spool).where(Spool.id.in_(spool_ids))).all():  # type: ignore[attr-defined]
            spools[spool.id] = spool

    for usage in usages:
        if usage.ams_id < 0:
            continue
        spool_id = index.get((usage.ams_id, usage.tray_id))
        if spool_id and spool_id in spools:
            usage.spool_id = spool_id
            usage.spool_name = spools[spool_id].name


def apply_deduction(session: Session, job: PrintJob, usages: list[FilamentUsage]) -> float:
    """执行扣减，写入使用流水。返回本次总扣减克重。"""
    total = 0.0
    for usage in usages:
        if usage.weight_g <= 0:
            continue
        if usage.spool_id is None:
            # 没绑定料盘也要留一条流水，界面上可以事后补绑
            session.add(
                UsageRecord(
                    spool_id=None,
                    printer_id=job.printer_id,
                    job_id=job.id,
                    ams_id=usage.ams_id,
                    tray_id=usage.tray_id,
                    filament_index=usage.index,
                    weight_g=usage.weight_g,
                    source="auto",
                    note=f"{job.title or '打印任务'} · 未绑定料盘",
                )
            )
            continue

        spool = session.get(Spool, usage.spool_id)
        if spool is None:
            continue

        cost = usage_cost(spool, usage.weight_g)
        usage.cost = round(cost, 2)

        spool.used_weight = round(spool.used_weight + usage.weight_g, 2)
        spool.remaining_weight = round(max(0.0, spool.remaining_weight - usage.weight_g), 2)
        spool.updated_at = utcnow()
        session.add(spool)

        session.add(
            UsageRecord(
                spool_id=spool.id,
                printer_id=job.printer_id,
                job_id=job.id,
                ams_id=usage.ams_id,
                tray_id=usage.tray_id,
                filament_index=usage.index,
                weight_g=usage.weight_g,
                source="auto",
                note=job.title or "打印任务",
            )
        )
        usage.deducted = True
        usage.deducted_g = usage.weight_g
        total += usage.weight_g

    job.filaments_json = _dump(usages)
    job.total_weight_g = round(sum(u.weight_g for u in usages), 2)
    job.deduction_applied = True
    session.add(job)
    return round(total, 2)


def _dump(usages: list[FilamentUsage]) -> str:
    import json

    return json.dumps([asdict(u) for u in usages], ensure_ascii=False)


def load_usages(job: PrintJob) -> list[FilamentUsage]:
    import json

    try:
        raw = json.loads(job.filaments_json or "[]")
    except ValueError:
        return []
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        allowed = {f for f in FilamentUsage().__dataclass_fields__}  # type: ignore[attr-defined]
        result.append(FilamentUsage(**{k: v for k, v in item.items() if k in allowed}))
    return result


def remain_based_usage(state: Optional[PrinterState], start_remain: dict[str, int]) -> list[FilamentUsage]:
    """兜底方案：拿不到云任务记录时，用官方 RFID 料盘的余量百分比差值估算。

    精度受限于 remain 的整数百分比（1kg 料盘 1% ≈ 10g），仅在没有更好数据时使用。
    """
    if state is None:
        return []
    usages: list[FilamentUsage] = []
    for tray in state.loaded_trays:
        key = f"{tray.ams_id}:{tray.tray_id}"
        before = start_remain.get(key)
        after = tray.remain
        if before is None or after is None or before < 0 or after < 0:
            continue
        delta_percent = before - after
        if delta_percent <= 0:
            continue
        grams = round(delta_percent / 100.0 * (tray.tray_weight or 1000.0), 2)
        usages.append(
            FilamentUsage(
                index=len(usages),
                filament_id=tray.info_idx,
                material=tray.tray_type,
                color=tray.color,
                weight_g=grams,
                ams_id=tray.ams_id,
                tray_id=tray.tray_id,
                slot_label=_slot_label(tray.ams_id, tray.tray_id),
                match_strategy=f"余量差 {before}% → {after}%",
            )
        )
    return usages
