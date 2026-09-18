"""REST 接口与 WebSocket。

命名沿用一个原则：所有写操作都返回受影响对象的完整状态，方便前端直接刷新。
"""
from __future__ import annotations

import base64
import io
import json
import qrcode
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import auth as auth_mod
from ..auth import (
    client_ip,
    is_https,
    is_private_host,
    peer_ip,
    resolve_session,
    token_from_request,
)
from ..brands import add_custom_brand, brand_choices, load_custom_brands, remove_custom_brand
from ..printer_art import printer_image_map
from ..catalog import (
    BRAND_COLOR_SERIES,
    BRAND_PRESETS,
    COLOR_PRESETS,
    FINISH_PRESETS,
    MATERIAL_COLOR_SERIES,
    MATERIALS,
    MODEL_CODE_TO_NAME,
    brand_lookup_map,
    build_spool_name,
    model_display_name,
    normalize_brand,
    normalize_color,
    normalize_finish,
    spool_weight_options,
)
from ..core.covers import cover_dir, cover_media_type
from ..colors import (
    catalog_index,
    match_catalog,
    match_inventory,
    recommend_brands,
    resolve_colors,
)
from ..config import settings
from ..core.deduction import apply_deduction, build_usages, load_usages, resolve_spools, usage_cost
from ..core.hub import ams_display_name, hub
from ..db import get_session
from ..models import PrintJob, Printer, SlotBinding, Spool, UsageRecord, utcnow

router = APIRouter()


# ══ 鉴权 ═══════════════════════════════════════════════════
# 登录态校验统一由 app.main 的中间件完成（HTTP）与 websocket_endpoint（WS）完成。
# 这里只放登录/登出/初始化等免鉴权接口。


def _setup_allowed(request: Request) -> bool:
    """首次创建管理员是否被允许。

    默认只认「内网直连」——看的是 TCP 对端地址而非 X-Forwarded-For，
    所以即使挂在反向代理后面，外面的人也伪造不出内网来源。
    """
    if settings.allow_public_setup:
        return True
    return is_private_host(peer_ip(request))


def _client_meta(request: Request) -> dict:
    return {"ip": client_ip(request), "ua": request.headers.get("user-agent", "")[:300]}


# ══ 通用 ═══════════════════════════════════════════════════
def spool_dict(spool: Spool) -> dict:
    return {
        "id": spool.id,
        "name": spool.name,
        "brand": spool.brand,
        "material": spool.material,
        "color_name": spool.color_name,
        "color_hex": spool.color_hex,
        "spool_weight": spool.spool_weight,
        "initial_weight": spool.initial_weight,
        "remaining_weight": spool.remaining_weight,
        "used_weight": spool.used_weight,
        "total_weight": spool.total_weight,
        "price": round(spool.price, 2),
        "price_per_g": round(spool.price_per_g, 5),
        "stock_value": round(spool.stock_value, 2),
        "remaining_percent": spool.remaining_percent,
        "is_low": spool.is_low,
        "tray_info_idx": spool.tray_info_idx,
        "tag_uid": spool.tag_uid,
        "location": spool.location,
        "note": spool.note,
        "archived": spool.archived,
        # 真实字段。历史上的实现是从 color_name 里现算（含「哑光」就是哑光），
        # 那种猜法没法表示丝绸、亮面这些工艺，也没法给同色的两盘料分别标。
        "finish": spool.finish or "普通",
        "created_at": spool.created_at.isoformat(),
        "updated_at": spool.updated_at.isoformat(),
    }


def job_dict(job: PrintJob, session: Session, with_filaments: bool = True) -> dict:
    data = {
        "id": job.id,
        "printer_id": job.printer_id,
        "serial": job.serial,
        "title": job.title,
        "status": job.status,
        "task_id": job.task_id,
        "cloud_task_id": job.cloud_task_id,
        "started_at": job.started_at.isoformat(),
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "duration_seconds": job.duration_seconds,
        "progress_at_end": job.progress_at_end,
        "total_weight_g": job.total_weight_g,
        "source": job.source,
        # 云端给的原始 URL（OSS 预签名，过期后取不到），只用于排查
        "cover_url": job.cover_url,
        # 界面真正该用的：抓下来存在本地的成果图文件名，空串表示这次没有
        "cover_file": job.cover_file,
        # 给前端一个明确的布尔量，免得前端自己拼 `cover_file ? ... : ...` 时
        # 把 null/undefined 当成「有图」；口径 = 有文件名 **且** 文件真的在
        "has_cover": bool(job.cover_file) and (cover_dir() / job.cover_file).is_file(),
        "deduction_applied": job.deduction_applied,
        "note": job.note,
        "pending": job.id in hub.pending_jobs() if job.id else False,
    }
    printer = session.get(Printer, job.printer_id)
    data["printer_name"] = printer.name if printer else ""
    if with_filaments:
        cost_total, usages = job_cost(job, session)
        data["cost_total"] = cost_total
        # 每条用量补上它对应的扣重流水 id：打印记录里的「更改料盘」要调
        # /api/usages/{id}/move，光有 spool_id 是改不动的（流水才是扣重的账本）。
        # UsageRecord 按 (job_id, filament_index) 与明细一一对应。
        records = session.exec(
            select(UsageRecord).where(UsageRecord.job_id == job.id)
        ).all()
        by_index = {r.filament_index: r.id for r in records}
        for u in usages:
            u.usage_id = by_index.get(u.index)
        data["filaments"] = [u.__dict__ for u in usages]
    else:
        data["cost_total"] = 0.0
    return data


def _slot_label(ams_id: int, tray_id: int) -> str:
    """槽位的展示名（列表里显示「装在哪儿」用）。

    直接写 `AMS {ams_id + 1}` 会把 AMS HT 的 128 拼成「AMS 129」—— 编号语义见
    core.hub.ams_display_name。外挂料盘在上报里是 ams_id = -1，单独写。
    """
    if ams_id < 0:
        return "外挂料盘"
    return f"{ams_display_name(ams_id)} · 槽位 {tray_id + 1}"


def binding_dict(binding: SlotBinding, session: Session) -> dict:
    spool = session.get(Spool, binding.spool_id) if binding.spool_id else None
    return {
        "id": binding.id,
        "printer_id": binding.printer_id,
        "ams_id": binding.ams_id,
        "tray_id": binding.tray_id,
        "spool_id": binding.spool_id,
        "spool": spool_dict(spool) if spool else None,
        "bound_at": binding.bound_at.isoformat(),
        "note": binding.note,
    }


def job_cost(job: PrintJob, session: Session) -> tuple[float, list]:
    """计算一次打印任务消耗的料材费用（¥）。

    优先用 filaments_json 里快照的 cost（即使料盘后来被删或改价也稳定）；
    没快照时（老数据）按当前料盘单价实时折算。
    返回 (本次耗材费合计, 含 cost 的用量明细列表)。
    """
    usages = load_usages(job)
    spool_ids = {u.spool_id for u in usages if u.spool_id}
    spools: dict[int, Spool] = {}
    if spool_ids:
        for s in session.exec(select(Spool).where(Spool.id.in_(spool_ids))).all():  # type: ignore[attr-defined]
            spools[s.id] = s

    total = 0.0
    for u in usages:
        cost = getattr(u, "cost", 0.0) or 0.0
        if cost == 0.0 and u.spool_id and u.spool_id in spools:
            cost = usage_cost(spools[u.spool_id], u.weight_g)
        cost = round(cost, 2)
        u.cost = cost
        total += cost
    return round(total, 2), usages


# ══ 系统 ═══════════════════════════════════════════════════
@router.get("/api/system/status")
def system_status(request: Request, session: Session = Depends(get_session)) -> dict:
    acc = hub.account()
    snapshot = hub.snapshot()
    spools = session.exec(select(Spool).where(Spool.archived == False)).all()  # noqa: E712
    jobs = session.exec(select(PrintJob).order_by(PrintJob.id.desc()).limit(20)).all()  # type: ignore[attr-defined]
    return {
        "version": "0.12.2",
        "mock": settings.mock_mode,
        "region": acc.region if acc else settings.region,
        "security": {
            "session_days": settings.session_ttl_days,
            "https": is_https(request),
            "trust_proxy": settings.trust_proxy,
            "account_count": auth_mod.user_count(),
        },
        "account": {
            "logged_in": bool(acc and acc.access_token),
            "account": acc.account if acc else "",
            "uid": acc.uid if acc else "",
            # region 必须带上：设置页要显示「中国大陆 / 海外」。
            # 漏掉这一项的后果是前端拿到 undefined，`undefined === "china"` 为假，
            # 于是无论账号真实区域是什么，设置页都写「海外」。
            "region": acc.region if acc else settings.region,
            "status": acc.status if acc else "logged_out",
            "status_message": acc.status_message if acc else "",
            "has_password_saved": bool(acc.password_enc) if acc else False,
            "token_expires_at": acc.token_expires_at.isoformat() if acc and acc.token_expires_at else None,
            "last_login_at": acc.last_login_at.isoformat() if acc and acc.last_login_at else None,
        },
        "stats": {
            "spool_count": len(spools),
            "remaining_total": round(sum(s.remaining_weight for s in spools), 1),
            "low_count": sum(1 for s in spools if s.is_low),
            "price_total": round(sum(s.price for s in spools if not s.archived), 2),
            "stock_value": round(sum(s.stock_value for s in spools if not s.archived), 2),
        },
        # 仪表盘用的真机照片：目录里有什么就报什么，前端按机型取；
        # 没配照片的机型前端会自动退回内联 SVG 示意图。
        "printer_images": printer_image_map(),
        "recent_jobs": [job_dict(j, session, with_filaments=False) for j in jobs],
        "events": hub.events()[:60],
        **snapshot,
    }


@router.get("/api/auth/status")
def auth_status(request: Request) -> dict:
    """登录页的引导接口：告诉前端是「初始化」还是「登录」，以及当前登录态。"""
    user = auth_mod.current_user(request)
    return {
        "setup_required": auth_mod.user_count() == 0,
        "setup_allowed": _setup_allowed(request),
        "authenticated": user is not None,
        "user": auth_mod.user_dict(user),
        "https": is_https(request),
    }


@router.post("/api/auth/setup")
def auth_setup(payload: dict = Body(...), request: Request = None, response: Response = None) -> dict:  # type: ignore[assignment]
    """首次初始化管理员账号。已有账号后此接口永久关闭。"""
    if auth_mod.user_count() > 0:
        raise HTTPException(status_code=409, detail="管理员已存在，请直接登录")
    if not _setup_allowed(request):
        raise HTTPException(
            status_code=403,
            detail="初始化只允许从内网访问。请先在内网打开一次完成初始化，或设置 ALLOW_PUBLIC_SETUP=1",
        )
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username:
        raise HTTPException(status_code=400, detail="请填写账号")
    try:
        user = auth_mod.create_user(username, password, display_name=username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    token, _ = auth_mod.create_session(user, request, days=auth_mod.settings.session_ttl_days)
    auth_mod.set_session_cookie(response, token, request)
    return {"ok": True, "user": auth_mod.user_dict(user)}


@router.post("/api/auth/login")
def auth_login(payload: dict = Body(...), request: Request = None, response: Response = None) -> dict:  # type: ignore[assignment]
    if auth_mod.user_count() == 0:
        raise HTTPException(status_code=409, detail="尚未初始化管理员账号")
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    remember = bool(payload.get("remember", True))
    if not username or not password:
        raise HTTPException(status_code=400, detail="请填写账号和密码")

    user = auth_mod.authenticate(username, password, request)
    days = auth_mod.settings.session_ttl_days if remember else 1
    token, _ = auth_mod.create_session(user, request, days=days)
    auth_mod.set_session_cookie(response, token, request, days=days)
    return {"ok": True, "user": auth_mod.user_dict(user)}


@router.post("/api/auth/logout")
def auth_logout(request: Request = None, response: Response = None) -> dict:  # type: ignore[assignment]
    auth_mod.revoke_session(token_from_request(request))
    auth_mod.clear_session_cookie(response)
    return {"ok": True}


@router.get("/api/auth/me")
def auth_me(request: Request) -> dict:
    user = auth_mod.current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    return {
        "user": auth_mod.user_dict(user),
        "active_sessions": auth_mod.active_session_count(int(user.id or 0)),
    }


@router.post("/api/auth/password")
def auth_change_password(payload: dict = Body(...), request: Request = None) -> dict:  # type: ignore[assignment]
    """修改自己的口令。改完除当前会话外的其它登录都会失效。"""
    user = auth_mod.current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    old = str(payload.get("old_password", ""))
    new = str(payload.get("new_password", ""))
    try:
        revoked = auth_mod.change_password(user, old, new, keep_token=token_from_request(request))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "revoked_other_sessions": revoked}


@router.post("/api/auth/logout-all")
def auth_logout_all(request: Request = None, response: Response = None) -> dict:  # type: ignore[assignment]
    """退出所有设备。"""
    user = auth_mod.current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    count = auth_mod.revoke_user_sessions(int(user.id or 0))
    auth_mod.clear_session_cookie(response)
    return {"ok": True, "revoked": count}


# ══ 账号 ═══════════════════════════════════════════════════
@router.get("/api/account")
def get_account() -> dict:
    acc = hub.account()
    if acc is None:
        return {"logged_in": False, "region": settings.region}
    return {
        "logged_in": bool(acc.access_token),
        "account": acc.account,
        "uid": acc.uid,
        "region": acc.region,
        "status": acc.status,
        "status_message": acc.status_message,
        "has_password_saved": bool(acc.password_enc),
        "token_expires_at": acc.token_expires_at.isoformat() if acc.token_expires_at else None,
        "last_login_at": acc.last_login_at.isoformat() if acc.last_login_at else None,
    }


@router.post("/api/account/login")
async def account_login(payload: dict = Body(...)) -> dict:
    account = str(payload.get("account") or "").strip()
    password = str(payload.get("password") or "")
    region = str(payload.get("region") or settings.region)
    remember = bool(payload.get("remember", True))
    if not account or not password:
        raise HTTPException(status_code=400, detail="请填写账号与密码")
    try:
        return await hub.login(account, password, region, remember)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/account/code")
async def account_send_code(payload: dict = Body(...)) -> dict:
    account = str(payload.get("account") or "").strip()
    region = str(payload.get("region") or settings.region)
    if not account:
        raise HTTPException(status_code=400, detail="请填写邮箱或手机号")
    try:
        return {"message": await hub.request_code(account, region)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/account/login-code")
async def account_login_code(payload: dict = Body(...)) -> dict:
    account = str(payload.get("account") or "").strip()
    code = str(payload.get("code") or "").strip()
    region = str(payload.get("region") or settings.region)
    try:
        return await hub.login_with_code(account, code, region)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/account/login-tfa")
async def account_login_tfa(payload: dict = Body(...)) -> dict:
    account = str(payload.get("account") or "").strip()
    tfa_key = str(payload.get("tfa_key") or "")
    code = str(payload.get("code") or "").strip()
    region = str(payload.get("region") or settings.region)
    try:
        return await hub.login_with_tfa(account, tfa_key, code, region)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/account/region")
async def account_set_region(payload: dict = Body(...)) -> dict:
    """切换拓竹账号区域。区域选错会导致「登录成功但同步不到设备」。"""
    region = str(payload.get("region") or "").strip().lower()
    try:
        return await hub.set_region(region)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/account/logout")
async def account_logout() -> dict:
    await hub.logout()
    return {"ok": True}


@router.post("/api/devices/sync")
async def devices_sync() -> dict:
    try:
        return {"devices": await hub.sync_devices()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ══ 打印机 ═════════════════════════════════════════════════
@router.get("/api/printers")
def list_printers(session: Session = Depends(get_session)) -> dict:
    result = []
    for printer in session.exec(select(Printer)).all():
        state = hub.states.get(printer.id or -1)
        result.append({
            "id": printer.id,
            "serial": printer.serial,
            "name": printer.name,
            "model": printer.model,
            "model_code": printer.model_code,
            "online": printer.online,
            "enabled": printer.enabled,
            "note": printer.note,
            "has_access_code": bool(printer.access_code),
            "state": hub.state_dict(state, printer.id or 0) if state else None,
        })
    return {"printers": result}


class PrinterPatch(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    note: Optional[str] = None


@router.patch("/api/printers/{printer_id}")
def patch_printer(
    printer_id: int,
    payload: PrinterPatch,
    session: Session = Depends(get_session),
) -> dict:
    printer = session.get(Printer, printer_id)
    if printer is None:
        raise HTTPException(status_code=404, detail="打印机不存在")
    if payload.name is not None:
        printer.name = payload.name
    if payload.enabled is not None:
        printer.enabled = payload.enabled
    if payload.note is not None:
        printer.note = payload.note
    session.add(printer)
    session.commit()
    return {"ok": True}


@router.post("/api/printers/{printer_id}/pushall")
def printer_pushall(printer_id: int, session: Session = Depends(get_session)) -> dict:
    printer = session.get(Printer, printer_id)
    if printer is None:
        raise HTTPException(status_code=404, detail="打印机不存在")
    if hub._mqtt and hub._mqtt.connected:
        hub._mqtt.request_pushall(printer.serial)
        return {"ok": True, "message": "已请求全量状态"}
    return {"ok": False, "message": "云连接未建立"}


@router.delete("/api/printers/{printer_id}")
def delete_printer(printer_id: int, session: Session = Depends(get_session)) -> dict:
    printer = session.get(Printer, printer_id)
    if printer is None:
        raise HTTPException(status_code=404, detail="打印机不存在")
    for binding in session.exec(
        select(SlotBinding).where(SlotBinding.printer_id == printer_id)
    ).all():
        session.delete(binding)
    session.delete(printer)
    session.commit()
    hub.states.pop(printer_id, None)
    hub._load_printers()
    return {"ok": True}


# ══ 料盘 ═══════════════════════════════════════════════════
@router.get("/api/spools")
def list_spools(
    q: str = "",
    material: str = "",
    brand: str = "",
    archived: bool = False,
    low_only: bool = False,
    session: Session = Depends(get_session),
) -> dict:
    spools = session.exec(select(Spool)).all()
    keyword = q.strip().lower()

    def match(spool: Spool) -> bool:
        if spool.archived != archived:
            return False
        if material and spool.material != material:
            return False
        if brand and spool.brand != brand:
            return False
        if low_only and not spool.is_low:
            return False
        if keyword:
            haystack = " ".join(
                [spool.name, spool.brand, spool.material, spool.color_name, spool.location or ""]
            ).lower()
            if keyword not in haystack:
                return False
        return True

    items = [spool_dict(s) for s in spools if match(s)]
    items.sort(key=lambda x: (x["remaining_weight"], x["id"] or 0))

    # 附上料盘当前所在槽位
    bindings = session.exec(select(SlotBinding)).all()
    slot_of: dict[int, list[dict]] = {}
    for binding in bindings:
        if binding.spool_id:
            slot_of.setdefault(binding.spool_id, []).append({
                "printer_id": binding.printer_id,
                "ams_id": binding.ams_id,
                "tray_id": binding.tray_id,
                "label": _slot_label(binding.ams_id, binding.tray_id),
            })

    # 首次 / 最后使用时间与流水条数：列表要展示，删除确认框也要用条数做判断。
    # 一次全表查询在内存里归并，比每个料盘各查一次省事。
    usage_stats: dict[int, dict] = {}
    for record in session.exec(select(UsageRecord)).all():
        if not record.spool_id:
            continue
        stat = usage_stats.setdefault(record.spool_id, {"count": 0, "first": None, "last": None})
        stamp = record.created_at.isoformat()
        stat["count"] += 1
        if stat["first"] is None or stamp < stat["first"]:
            stat["first"] = stamp
        if stat["last"] is None or stamp > stat["last"]:
            stat["last"] = stamp

    for item in items:
        item["slots"] = slot_of.get(item["id"], [])  # type: ignore[index]
        stat = usage_stats.get(item["id"], {})
        item["first_used_at"] = stat.get("first")
        item["last_used_at"] = stat.get("last")
        item["usage_count"] = stat.get("count", 0)
    return {"spools": items}


class SpoolCreate(BaseModel):
    brand: str = ""
    material: str = ""
    finish: str = ""
    color_name: str = ""
    color_hex: str = "#000000"
    name: str = ""
    spool_weight: float = 0.0
    initial_weight: float = 1000.0
    remaining_weight: Optional[float] = None
    location: str = ""
    note: str = ""
    tray_info_idx: str = ""
    price: float = 0.0


@router.post("/api/spools")
def create_spool(payload: SpoolCreate, session: Session = Depends(get_session)) -> dict:
    remaining = payload.remaining_weight
    if remaining is None:
        remaining = payload.initial_weight
    # 品牌统一成规范名，避免「Bambu Lab」和「拓竹」两套写法并存
    brand = normalize_brand(payload.brand)
    finish = normalize_finish(payload.finish) or "普通"
    # 手打的品牌顺手记进自定义清单，下次新增时就能在下拉里直接选到
    if brand and brand not in BRAND_PRESETS:
        add_custom_brand(session, brand)
    spool = Spool(
        name=payload.name or build_spool_name(brand, payload.material, payload.color_name, finish),
        brand=brand,
        material=payload.material,
        finish=finish,
        color_name=payload.color_name,
        color_hex=normalize_color(payload.color_hex),
        spool_weight=payload.spool_weight,
        initial_weight=payload.initial_weight,
        remaining_weight=round(max(0.0, min(remaining, payload.initial_weight)), 2),
        used_weight=round(max(0.0, payload.initial_weight - remaining), 2),
        location=payload.location,
        note=payload.note,
        tray_info_idx=payload.tray_info_idx,
        price=payload.price,
    )
    session.add(spool)
    session.commit()
    session.refresh(spool)
    return spool_dict(spool)


class SpoolPatch(BaseModel):
    brand: Optional[str] = None
    material: Optional[str] = None
    finish: Optional[str] = None
    color_name: Optional[str] = None
    color_hex: Optional[str] = None
    name: Optional[str] = None
    spool_weight: Optional[float] = None
    initial_weight: Optional[float] = None
    remaining_weight: Optional[float] = None
    location: Optional[str] = None
    note: Optional[str] = None
    tray_info_idx: Optional[str] = None
    archived: Optional[bool] = None
    price: Optional[float] = None


@router.get("/api/spools/{spool_id}")
def get_spool(spool_id: int, session: Session = Depends(get_session)) -> dict:
    spool = session.get(Spool, spool_id)
    if spool is None:
        raise HTTPException(status_code=404, detail="料盘不存在")
    records = session.exec(
        select(UsageRecord).where(UsageRecord.spool_id == spool_id).order_by(UsageRecord.id.desc()).limit(200)  # type: ignore[attr-defined]
    ).all()
    bindings = session.exec(
        select(SlotBinding).where(SlotBinding.spool_id == spool_id)
    ).all()

    usage_list = []
    for record in records:
        job = session.get(PrintJob, record.job_id) if record.job_id else None
        usage_list.append({
            "id": record.id,
            "weight_g": record.weight_g,
            "source": record.source,
            "note": record.note,
            "created_at": record.created_at.isoformat(),
            "job_id": record.job_id,
            "job_title": job.title if job else "",
            "ams_id": record.ams_id,
            "tray_id": record.tray_id,
            "slot_label": (
                f"AMS {record.ams_id + 1} · 槽位 {record.tray_id + 1}"
                if record.ams_id >= 0 else "外挂料盘"
            ),
        })

    data = spool_dict(spool)
    data["usages"] = usage_list
    data["bindings"] = [binding_dict(b, session) for b in bindings]
    return data


@router.patch("/api/spools/{spool_id}")
def patch_spool(
    spool_id: int, payload: SpoolPatch, session: Session = Depends(get_session)
) -> dict:
    spool = session.get(Spool, spool_id)
    if spool is None:
        raise HTTPException(status_code=404, detail="料盘不存在")

    # 动手改字段之前，先按「老参数」算一遍默认名。改完再比一次：
    #   名字 == 默认名 → 说明它一直是自动生成的，跟着新参数一起更新
    #   （用户反馈的外观丢失，是前端漏传 finish；补上之后回头重存老料盘时，
    #    名字若还留着旧的「品牌 材料 颜色」，外观就白改了）；
    #   名字 != 默认名 → 已经被人改过，原样保留，不去覆盖。
    auto_name = build_spool_name(spool.brand, spool.material, spool.color_name, spool.finish)

    for field in ("material", "color_name", "name", "location", "note", "tray_info_idx"):
        value = getattr(payload, field)
        if value is not None:
            setattr(spool, field, value)
    if payload.brand is not None:
        spool.brand = normalize_brand(payload.brand)
        if spool.brand and spool.brand not in BRAND_PRESETS:
            add_custom_brand(session, spool.brand)
    if payload.finish is not None:
        spool.finish = normalize_finish(payload.finish) or "普通"
    if payload.color_hex is not None:
        spool.color_hex = normalize_color(payload.color_hex)
    if payload.spool_weight is not None:
        spool.spool_weight = payload.spool_weight
    if payload.initial_weight is not None:
        spool.initial_weight = payload.initial_weight
    if payload.price is not None:
        spool.price = payload.price
    if payload.archived is not None:
        spool.archived = payload.archived
    if payload.remaining_weight is not None:
        spool.remaining_weight = round(max(0.0, payload.remaining_weight), 2)
        spool.used_weight = round(max(0.0, spool.initial_weight - spool.remaining_weight), 2)

    if spool.name == auto_name:
        spool.name = build_spool_name(spool.brand, spool.material, spool.color_name, spool.finish)

    spool.updated_at = utcnow()
    session.add(spool)
    session.commit()
    session.refresh(spool)
    return spool_dict(spool)


@router.delete("/api/spools/{spool_id}")
def delete_spool(
    spool_id: int,
    force: bool = False,
    session: Session = Depends(get_session),
) -> dict:
    """删除料盘（用于录错了要删掉的情况）。

    默认有保护：料盘上还挂着使用流水时先拦一道（409），界面会弹二次确认，
    确认后带 force=true 再来。强制删除会顺带收拾干净引用关系，避免留下悬空数据：

      · 删掉该料盘的槽位绑定（否则 AMS 槽位会指向不存在的料盘）
      · 删掉该料盘名下的使用流水（「使用历史」里的那批记录）
      · 把打印任务明细里的料盘引用置空，但保留克重与任务本身

    注意：整盘价格是记在料盘上的，删掉之后那部分历史打印费用会退回
    「按当前单价实时折算」的口径，不再有快照。
    """
    spool = session.get(Spool, spool_id)
    if spool is None:
        raise HTTPException(status_code=404, detail="料盘不存在")

    records = session.exec(
        select(UsageRecord).where(UsageRecord.spool_id == spool_id)
    ).all()
    bindings = session.exec(
        select(SlotBinding).where(SlotBinding.spool_id == spool_id)
    ).all()

    if records and not force:
        raise HTTPException(
            status_code=409,
            detail=(
                f"「{spool.name}」还有 {len(records)} 条使用记录，"
                "删除后这些记录会一并消失且无法恢复。"
            ),
        )

    # 打印任务明细里指向这盘料的行：解绑但保留克重，任务本身不动
    jobs_updated = 0
    for job in session.exec(select(PrintJob)).all():
        entries = load_usages(job)
        touched = False
        for entry in entries:
            if entry.spool_id == spool_id:
                entry.spool_id = None
                entry.spool_name = ""
                entry.match_strategy = f"{entry.match_strategy}（料盘已删除）".strip()
                touched = True
        if touched:
            job.filaments_json = json.dumps([e.__dict__ for e in entries], ensure_ascii=False)
            session.add(job)
            jobs_updated += 1

    for binding in bindings:
        session.delete(binding)
    for record in records:
        session.delete(record)
    session.delete(spool)
    session.commit()

    return {
        "ok": True,
        "name": spool.name,
        "deleted_usages": len(records),
        "deleted_bindings": len(bindings),
        "jobs_updated": jobs_updated,
    }


class UsePayload(BaseModel):
    weight_g: float
    note: str = "手动补录"


@router.post("/api/spools/{spool_id}/use")
def use_spool(
    spool_id: int, payload: UsePayload, session: Session = Depends(get_session)
) -> dict:
    spool = session.get(Spool, spool_id)
    if spool is None:
        raise HTTPException(status_code=404, detail="料盘不存在")
    if payload.weight_g <= 0:
        raise HTTPException(status_code=400, detail="消耗量必须大于 0")
    spool.used_weight = round(spool.used_weight + payload.weight_g, 2)
    spool.remaining_weight = round(max(0.0, spool.remaining_weight - payload.weight_g), 2)
    spool.updated_at = utcnow()
    session.add(spool)
    session.add(
        UsageRecord(
            spool_id=spool.id, weight_g=payload.weight_g, source="manual", note=payload.note
        )
    )
    session.commit()
    session.refresh(spool)
    return spool_dict(spool)


class MeasurePayload(BaseModel):
    total_weight: float
    note: str = "按称重校准"


@router.post("/api/spools/{spool_id}/measure")
def measure_spool(
    spool_id: int, payload: MeasurePayload, session: Session = Depends(get_session)
) -> dict:
    """按实际称重校准剩余量。无需关心料盘皮重，会自动扣除。"""
    spool = session.get(Spool, spool_id)
    if spool is None:
        raise HTTPException(status_code=404, detail="料盘不存在")
    if payload.total_weight <= 0:
        raise HTTPException(status_code=400, detail="称重值必须大于 0")

    net = round(max(0.0, payload.total_weight - spool.spool_weight), 2)
    before = spool.remaining_weight
    delta = round(net - before, 2)

    spool.remaining_weight = net
    spool.used_weight = round(max(0.0, spool.initial_weight - net), 2)
    spool.updated_at = utcnow()
    session.add(spool)
    session.add(
        UsageRecord(
            spool_id=spool.id,
            weight_g=delta,
            source="calibrate",
            note=f"{payload.note}：{before} g → {net} g",
        )
    )
    session.commit()
    session.refresh(spool)
    result = spool_dict(spool)
    result["delta"] = delta
    return result


# ══ 槽位绑定 ═══════════════════════════════════════════════
@router.get("/api/bindings")
def list_bindings(
    printer_id: Optional[int] = None, session: Session = Depends(get_session)
) -> dict:
    stmt = select(SlotBinding)
    if printer_id is not None:
        stmt = stmt.where(SlotBinding.printer_id == printer_id)
    bindings = session.exec(stmt).all()
    return {"bindings": [binding_dict(b, session) for b in bindings]}


class BindingPayload(BaseModel):
    printer_id: int
    ams_id: int
    tray_id: int
    spool_id: Optional[int] = None
    note: str = ""


@router.put("/api/bindings")
def upsert_binding(payload: BindingPayload, session: Session = Depends(get_session)) -> dict:
    if session.get(Printer, payload.printer_id) is None:
        raise HTTPException(status_code=404, detail="打印机不存在")
    if payload.spool_id is not None and session.get(Spool, payload.spool_id) is None:
        raise HTTPException(status_code=404, detail="料盘不存在")

    binding = session.exec(
        select(SlotBinding).where(
            SlotBinding.printer_id == payload.printer_id,
            SlotBinding.ams_id == payload.ams_id,
            SlotBinding.tray_id == payload.tray_id,
        )
    ).first()

    if payload.spool_id is None:
        # 解绑
        if binding:
            session.delete(binding)
            session.commit()
        return {"ok": True, "unbound": True}

    # 同一盘料不应该同时出现在两个槽位
    others = session.exec(
        select(SlotBinding).where(SlotBinding.spool_id == payload.spool_id)
    ).all()
    for other in others:
        if (other.printer_id, other.ams_id, other.tray_id) != (
            payload.printer_id, payload.ams_id, payload.tray_id
        ):
            session.delete(other)

    if binding is None:
        binding = SlotBinding(
            printer_id=payload.printer_id, ams_id=payload.ams_id, tray_id=payload.tray_id
        )
    binding.spool_id = payload.spool_id
    binding.bound_at = utcnow()
    binding.note = payload.note
    session.add(binding)
    session.commit()
    session.refresh(binding)
    return binding_dict(binding, session)


@router.delete("/api/bindings/{binding_id}")
def delete_binding(binding_id: int, session: Session = Depends(get_session)) -> dict:
    binding = session.get(SlotBinding, binding_id)
    if binding is None:
        raise HTTPException(status_code=404, detail="绑定不存在")
    session.delete(binding)
    session.commit()
    return {"ok": True}


# ══ 打印任务 ═══════════════════════════════════════════════
@router.get("/api/jobs")
def list_jobs(
    limit: int = 50,
    status: str = "",
    printer_id: Optional[int] = None,
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(PrintJob).order_by(PrintJob.id.desc()).limit(min(limit, 300))  # type: ignore[attr-defined]
    if status:
        stmt = select(PrintJob).where(PrintJob.status == status).order_by(PrintJob.id.desc()).limit(min(limit, 300))  # type: ignore[attr-defined]
    if printer_id is not None:
        stmt = select(PrintJob).where(PrintJob.printer_id == printer_id).order_by(PrintJob.id.desc()).limit(min(limit, 300))  # type: ignore[attr-defined]
    jobs = session.exec(stmt).all()
    return {"jobs": [job_dict(j, session) for j in jobs]}


@router.get("/api/jobs/{job_id}")
def get_job(job_id: int, session: Session = Depends(get_session)) -> dict:
    job = session.get(PrintJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job_dict(job, session)


@router.get("/api/jobs/{job_id}/cover")
def job_cover(job_id: int, session: Session = Depends(get_session)) -> Response:
    """取这次打印的成果图（结算时从云端抓下来存本地的那张）。

    为什么不让前端直接拿云端的 URL：那个链接是 OSS 预签名地址，30 分钟就过期，
    存在列表里过一会儿就是 403。所以只暴露本地缓存的这一张。
    """
    job = session.get(PrintJob, job_id)
    if job is None or not job.cover_file:
        raise HTTPException(status_code=404, detail="这次打印没有云端成果图")
    path = cover_dir() / job.cover_file
    if not path.is_file():
        raise HTTPException(status_code=404, detail="成果图文件已丢失")
    return FileResponse(path, media_type=cover_media_type(job.cover_file))


@router.post("/api/jobs/{job_id}/retry")
async def retry_job(job_id: int, session: Session = Depends(get_session)) -> dict:
    job = session.get(PrintJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.deduction_applied:
        raise HTTPException(status_code=400, detail="该任务已经扣过重了")
    hub.retry_settle(job_id)
    result = await hub.settle_pending(force_job_id=job_id)
    return result


class ManualUsageItem(BaseModel):
    ams_id: int = -1
    tray_id: int = -1
    spool_id: Optional[int] = None
    weight_g: float = 0.0


class ManualUsagePayload(BaseModel):
    items: list[ManualUsageItem]
    mark_applied: bool = True


@router.post("/api/jobs/{job_id}/manual")
def manual_job_usage(
    job_id: int, payload: ManualUsagePayload, session: Session = Depends(get_session)
) -> dict:
    """手工录入某次打印的用量（云端无记录时使用）。"""
    job = session.get(PrintJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.deduction_applied:
        raise HTTPException(status_code=400, detail="该任务已经扣过重了")

    usages = []
    for idx, item in enumerate(payload.items):
        usages.append(
            {
                "index": idx,
                "filament_id": "",
                "material": "",
                "color": "#000000",
                "weight_g": item.weight_g,
                "ams_id": item.ams_id,
                "tray_id": item.tray_id,
                "slot_label": (
                    f"AMS {item.ams_id + 1} · 槽位 {item.tray_id + 1}" if item.ams_id >= 0 else "外挂料盘"
                ),
                "spool_id": item.spool_id,
                "spool_name": "",
                "match_strategy": "手动录入",
                "deducted_g": 0.0,
                "deducted": False,
            }
        )

    from ..core.deduction import FilamentUsage

    usage_objs = [FilamentUsage(**u) for u in usages]
    resolve_spools(session, job.printer_id, usage_objs)
    total = apply_deduction(session, job, usage_objs)
    job.source = "manual"
    session.add(job)
    session.commit()
    return {"ok": True, "total_weight_g": total, "job": job_dict(job, session)}


class CorrectPayload(BaseModel):
    spool_id: int


@router.post("/api/usages/{usage_id}/move")
def move_usage(
    usage_id: int, payload: CorrectPayload, session: Session = Depends(get_session)
) -> dict:
    """纠错：把一条扣重流水从一个料盘转到另一个料盘。"""
    record = session.get(UsageRecord, usage_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    target = session.get(Spool, payload.spool_id)
    if target is None:
        raise HTTPException(status_code=404, detail="目标料盘不存在")

    weight = record.weight_g
    source_id = record.spool_id

    if source_id == target.id:
        return {"ok": True, "message": "来源与目标相同，无需调整"}

    if source_id:
        old = session.get(Spool, source_id)
        if old:
            old.used_weight = round(max(0.0, old.used_weight - weight), 2)
            old.remaining_weight = round(min(old.initial_weight, old.remaining_weight + weight), 2)
            old.updated_at = utcnow()
            session.add(old)

    target.used_weight = round(target.used_weight + weight, 2)
    target.remaining_weight = round(max(0.0, target.remaining_weight - weight), 2)
    target.updated_at = utcnow()
    session.add(target)

    record.spool_id = target.id
    record.source = "correction"
    record.note = f"{record.note} · 已转至 {target.name}"
    session.add(record)

    # 同步更新任务里的明细，保证两边一致
    if record.job_id:
        job = session.get(PrintJob, record.job_id)
        if job:
            entries = load_usages(job)
            for entry in entries:
                if entry.index == record.filament_index:
                    entry.spool_id = target.id
                    entry.spool_name = target.name
                    entry.match_strategy += "（已人工纠正）"
                    entry.cost = round(usage_cost(target, entry.weight_g), 2)
            job.filaments_json = json.dumps([e.__dict__ for e in entries], ensure_ascii=False)
            session.add(job)

    session.commit()
    return {"ok": True, "usage": {"id": record.id, "spool_id": target.id, "weight_g": weight}}


# ══ 统计与目录 ═════════════════════════════════════════════
def _client_tz(tz_minutes) -> timezone:
    """客户端时区。JS 传的是「UTC 以东多少分钟」（北京时间 = 480）。

    库里的时间一律是无时区 UTC，而「今天」「本周」是**用户本地**的概念。
    东八区晚上 8 点看到的「今天」在 UTC 里已经是明天，不换算就会算错桶。

    为什么不直接写 `int(tz_minutes)`：自测里是 `routes.stats(session)` 直接调函数，
    这时 FastAPI 的默认值是个 Query 对象而不是 0，int() 会 TypeError。
    转不动就当 0（=UTC），比让整个统计接口 500 好。
    """
    try:
        minutes = int(tz_minutes or 0)
    except (TypeError, ValueError):
        minutes = 0
    return timezone(timedelta(minutes=max(-840, min(840, minutes))))


def _local_day(moment: Optional[datetime], tz: timezone) -> str:
    """把库里的 naive-UTC 时间换算成客户端本地日期（YYYY-MM-DD）。"""
    if moment is None:
        return ""
    return moment.replace(tzinfo=timezone.utc).astimezone(tz).strftime("%Y-%m-%d")


def _local_day_start(days: int, tz: timezone) -> datetime:
    """最近 N 个自然日（含今天）的起点，返回 naive UTC 供查询使用。"""
    now_local = datetime.now(timezone.utc).astimezone(tz)
    start_local = (now_local - timedelta(days=max(0, days - 1))).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return start_local.astimezone(timezone.utc).replace(tzinfo=None)


def _group_summary(spools: list[Spool], key_of) -> list[dict]:
    """按某个维度（品牌 / 材料 / 外观）把料盘分组汇总。

    每组给出：多少盘、满盘净重、已用、剩余、采购金额、剩余价值，
    以及余量百分比（按组内满盘总重折算），方便直接画条形图。
    """
    buckets: dict[str, dict] = {}
    for spool in spools:
        name = (key_of(spool) or "").strip() or "未填写"
        item = buckets.setdefault(name, {
            "name": name, "count": 0, "initial_g": 0.0, "remaining_g": 0.0,
            "used_g": 0.0, "price": 0.0, "stock_value": 0.0, "priced_count": 0,
        })
        item["count"] += 1
        item["initial_g"] += spool.initial_weight
        item["remaining_g"] += spool.remaining_weight
        item["used_g"] += spool.used_weight
        item["price"] += spool.price
        item["stock_value"] += spool.stock_value
        # 登记过价格的盘数。算「每盘均价」必须拿它当分母 —— 用 count 当分母的话，
        # 组里混进几盘没填价的就会把均价算低，看起来像数据错了。
        if spool.price > 0:
            item["priced_count"] += 1
    out: list[dict] = []
    for item in buckets.values():
        item["initial_g"] = round(item["initial_g"], 1)
        item["remaining_g"] = round(item["remaining_g"], 1)
        item["used_g"] = round(item["used_g"], 1)
        item["price"] = round(item["price"], 2)
        item["stock_value"] = round(item["stock_value"], 2)
        item["remaining_percent"] = (
            round(item["remaining_g"] / item["initial_g"] * 100, 1) if item["initial_g"] > 0 else 0.0
        )
        out.append(item)
    out.sort(key=lambda x: (-x["count"], -x["remaining_g"]))
    return out


@router.get("/api/stats")
def stats(
    # session 必须留在第一位：自测里直接 routes.stats(session) 位置传参，
    # 把 tz_minutes 放前面会让 Session 被当成时区解析（踩过一次）。
    session: Session = Depends(get_session),
    tz_minutes: int = Query(0, description="客户端时区（UTC 以东的分钟数，北京时间 = 480）"),
) -> dict:
    tz = _client_tz(tz_minutes)
    spools = session.exec(select(Spool)).all()
    jobs = session.exec(select(PrintJob).order_by(PrintJob.id.desc()).limit(200)).all()  # type: ignore[attr-defined]
    records = session.exec(select(UsageRecord).order_by(UsageRecord.id.desc()).limit(1000)).all()  # type: ignore[attr-defined]

    by_material: dict[str, float] = {}
    for spool in spools:
        by_material[spool.material] = round(
            by_material.get(spool.material, 0.0) + spool.remaining_weight, 1
        )

    # 价格维度汇总
    price_total = round(sum(s.price for s in spools if not s.archived), 2)        # 在用料盘总采购价
    stock_value = round(sum(s.stock_value for s in spools if not s.archived), 2)  # 当前库存余值
    used_value = round(  # 已消耗部分按当前单价折算（近似，未登记价格的盘不计）
        sum(s.price_per_g * s.used_weight for s in spools), 2
    )
    archived_value = round(sum(s.price for s in spools if s.archived), 2)
    by_material_price: dict[str, float] = {}
    for spool in spools:
        if spool.price <= 0:
            continue
        by_material_price[spool.material] = round(
            by_material_price.get(spool.material, 0.0) + spool.price, 2
        )

    # 累计打印耗材费：逐任务按快照 cost（缺失则按当前单价实时折算）
    spool_map = {s.id: s for s in spools}
    print_cost_total = 0.0
    by_day_cost: dict[str, float] = {}
    for job in jobs:
        for u in load_usages(job):
            cost = getattr(u, "cost", 0.0) or 0.0
            if cost == 0.0 and u.spool_id and u.spool_id in spool_map:
                cost = usage_cost(spool_map[u.spool_id], u.weight_g)
            cost = round(cost, 2)
            print_cost_total += cost
            if job.started_at:
                day = _local_day(job.started_at, tz)
                by_day_cost[day] = round(by_day_cost.get(day, 0.0) + cost, 2)

    by_day: dict[str, float] = {}
    for record in records:
        if record.source in ("auto", "manual"):
            day = _local_day(record.created_at, tz)
            by_day[day] = round(by_day.get(day, 0.0) + max(0.0, record.weight_g), 1)

    # ── 本周（最近 7 个自然日，含今天）：概览页三张卡的数据源 ──
    week_start = _local_day_start(7, tz)
    week_jobs = session.exec(
        select(PrintJob).where(PrintJob.started_at >= week_start)  # type: ignore[arg-type]
    ).all()
    now_utc = utcnow()
    week_seconds = 0
    week_success = 0
    for job in week_jobs:
        seconds = int(job.duration_seconds or 0)
        # 正在打印的任务还没有落 duration，按「开始到现在」实时算，卡上不会一直显示 0
        if job.status == "running" and job.started_at:
            seconds = max(seconds, int((now_utc - job.started_at).total_seconds()))
        week_seconds += max(0, seconds)
        if job.status == "finished":
            week_success += 1

    week_records = session.exec(
        select(UsageRecord).where(UsageRecord.created_at >= week_start)  # type: ignore[arg-type]
    ).all()
    week_used = round(
        sum(max(0.0, r.weight_g) for r in week_records if r.source in ("auto", "manual")), 1
    )

    # ── 分组汇总（耗材汇总页） ──
    live = [s for s in spools if not s.archived]
    by_brand = _group_summary(live, lambda s: s.brand)
    by_material_detail = _group_summary(live, lambda s: s.material)
    by_finish = _group_summary(live, lambda s: s.finish or "普通")

    return {
        "spool_count": len([s for s in spools if not s.archived]),
        "archived_count": len([s for s in spools if s.archived]),
        "remaining_total": round(sum(s.remaining_weight for s in spools if not s.archived), 1),
        "used_total": round(sum(s.used_weight for s in spools), 1),
        "low_count": sum(1 for s in spools if not s.archived and s.is_low),
        "job_count": len(jobs),
        "price_total": price_total,
        "stock_value": stock_value,
        "used_value": used_value,
        "archived_value": archived_value,
        "by_material": by_material,
        "by_material_price": by_material_price,
        "print_cost_total": round(print_cost_total, 2),
        "by_day": dict(sorted(by_day.items())[-30:]),
        "by_day_cost": dict(sorted(by_day_cost.items())[-30:]),
        # 最近 7 个自然日（含今天）。日期按客户端时区切，否则东八区晚上看到的
        # 「今天」会被算到上一个桶里。
        "week": {
            "days": 7,
            "start": week_start,
            "print_seconds": week_seconds,
            "print_hours": round(week_seconds / 3600, 1),
            "success_count": week_success,
            "job_count": len(week_jobs),
            "used_g": week_used,
        },
        # 分组汇总：每个维度一组（在库料盘，不含已归档）
        "by_brand": by_brand,
        "by_material_detail": by_material_detail,
        "by_finish": by_finish,
    }


@router.get("/api/catalog")
def catalog(session: Session = Depends(get_session)) -> dict:
    brands = brand_choices(session)
    return {
        "brands": brands,
        "preset_brands": BRAND_PRESETS,
        "custom_brands": load_custom_brands(session),
        "materials": MATERIALS,
        "finishes": FINISH_PRESETS,
        "colors": COLOR_PRESETS,
        "color_series": BRAND_COLOR_SERIES,
        "material_color_series": MATERIAL_COLOR_SERIES,
        "spool_weights": {b: spool_weight_options(b) for b in brands},
        "model_codes": MODEL_CODE_TO_NAME,
    }


# ══ 自定义品牌 ═══════════════════════════════════════════
@router.get("/api/brands")
def list_brands(session: Session = Depends(get_session)) -> dict:
    return {
        "brands": brand_choices(session),
        "preset_brands": BRAND_PRESETS,
        "custom_brands": load_custom_brands(session),
    }


@router.post("/api/brands")
def create_brand(payload: dict = Body(...), session: Session = Depends(get_session)) -> dict:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="请填写品牌名")
    custom = add_custom_brand(session, name)
    session.commit()
    return {"custom_brands": custom, "brands": brand_choices(session)}


@router.delete("/api/brands/{name}")
def delete_brand(name: str, session: Session = Depends(get_session)) -> dict:
    """删除自定义品牌。

    只从下拉候选里移除，**不动已经录好的料盘**——那些料盘的品牌字段照旧，
    只是变成「不在候选里」的写法，新建时仍可重新加回来。
    """
    custom = remove_custom_brand(session, name)
    session.commit()
    return {"custom_brands": custom, "brands": brand_choices(session)}


# ══ 图片识色：配色匹配 ═══════════════════════════════════════
class ColorQuery(BaseModel):
    hex: str = ""
    weight: float = 1.0


class ColorMatchPayload(BaseModel):
    # 既接受 ["#3A7D44", ...]，也接受 [{"hex": "...", "weight": 0.4}, ...]
    colors: list[ColorQuery | str] = []
    material: str = ""
    brands: list[str] = []
    # both / catalog / inventory
    scope: str = "both"
    limit: int = 5
    # 超过这个 ΔE00 就不算「接近」；界面上的灰字提示用得到
    max_delta_e: float = 12.0
    include_archived: bool = False


@router.post("/api/color/match")
def color_match(
    payload: ColorMatchPayload, session: Session = Depends(get_session)
) -> dict:
    """把一组颜色（通常来自图片识色）匹配到品牌色卡与自家料盘。

    图像的主色提取在前端完成（Canvas），这里只管配色比对——所以容器不需要
    任何图像处理依赖，而且客户端还能是脚本或 Home Assistant 之类。
    """
    queries = resolve_colors(payload.colors)
    if not queries:
        raise HTTPException(status_code=400, detail="没有可用的颜色，请检查传入的色值")

    scope = payload.scope if payload.scope in ("both", "catalog", "inventory") else "both"
    limit = max(1, min(int(payload.limit or 5), 20))
    threshold = max(0.5, min(float(payload.max_delta_e or 12.0), 60.0))
    brands = payload.brands or []

    spools: list[Spool] = []
    if scope in ("both", "inventory"):
        spools = list(session.exec(select(Spool)).all())

    results = []
    for query in queries:
        item: dict = {"hex": query["hex"], "weight": query["weight"], "lab": query["lab"]}

        if scope in ("both", "catalog"):
            matches = match_catalog(
                query["hex"], payload.material, brands, limit=limit, max_delta_e=threshold
            )
            item["catalog"] = matches
            item["brands"] = recommend_brands(matches)
            if not matches:
                # 全都不在阈值内时，也给一个「最接近的」用于兜底提示
                nearest = match_catalog(
                    query["hex"], payload.material, brands, limit=1, max_delta_e=100.0
                )
                item["nearest_catalog"] = nearest[0] if nearest else None

        if scope in ("both", "inventory"):
            inventory = match_inventory(
                query["hex"],
                spools,
                payload.material,
                brands,
                limit=limit,
                max_delta_e=threshold,
                include_archived=payload.include_archived,
            )
            item["inventory"] = inventory
            if not inventory:
                nearest = match_inventory(
                    query["hex"],
                    spools,
                    payload.material,
                    brands,
                    limit=1,
                    max_delta_e=100.0,
                    include_archived=payload.include_archived,
                )
                item["nearest_inventory"] = nearest[0] if nearest else None

        results.append(item)

    all_entries = catalog_index().get("*", [])
    by_brand: dict[str, int] = {}
    for entry in all_entries:
        by_brand[entry["brand"]] = by_brand.get(entry["brand"], 0) + 1

    return {
        "colors": results,
        "filters": {
            "material": payload.material,
            "brands": brands,
            "scope": scope,
            "max_delta_e": threshold,
        },
        "catalog": {
            "total": len(all_entries),
            "by_brand": dict(sorted(by_brand.items(), key=lambda kv: -kv[1])),
        },
        "spool_count": len(spools),
    }


# ══ 二维码标签 ═════════════════════════════════════════════
def _qr_png(content: str, box: int = 8, border: int = 2) -> bytes:
    # qrcode 的 box_size 必须 > 0，给 0 会直接抛 ValueError；box_size 过大又会
    # 吃内存。这里收口成 1..64，调用方就不用各自防一遍。
    box = max(1, min(64, int(box)))
    qr = qrcode.QRCode(version=None, box_size=box, border=border)
    qr.add_data(content)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _qr_module_count(content: str, border: int = 2) -> int:
    """二维码的总模块数（含静区），供前端按模块物理尺寸反推合适的倍率。"""
    probe = qrcode.QRCode(version=None, box_size=1, border=border)
    probe.add_data(content)
    probe.make(fit=True)
    return probe.modules_count + border * 2


def _qr_png_fit(content: str, target_dots: int, border: int = 2) -> tuple[bytes, int]:
    """按目标点宽输出二维码，且保证每个模块落在整数个像素上。

    标签位图里二维码是 1:1 贴上去的，缩放会让模块边界糊掉、扫不出来。
    所以先取「不超过目标宽度」的最大整数倍率，返回 (PNG 字节, 实际点宽)。
    实际值可能略小于目标值，用 X-QR-Dots 告诉前端。
    """
    total = _qr_module_count(content, border=border)
    box = max(1, int(target_dots) // total)
    return _qr_png(content, box=box, border=border), total * box


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.get("/api/labels/spool/{spool_id}.png")
def spool_label(
    spool_id: int,
    request: Request,
    dots: int = 0,
    box: int = 0,
    session: Session = Depends(get_session),
):
    """料盘二维码。

    两种给尺寸的方式，都是为了在 1 位标签位图里贴图不糊（模块必须整数像素）：
      ?box=N   指定每个模块占 N 个点 —— 前端按「模块物理尺寸」算，推荐；
      ?dots=N  指定总点宽，服务端取不超过它的最大整数倍率（旧接口，保留）。
    两种情况都会通过 X-QR-Dots / X-QR-Modules 回传实际值。
    """
    spool = session.get(Spool, spool_id)
    if spool is None:
        raise HTTPException(status_code=404, detail="料盘不存在")
    content = f"{_base_url(request)}/#spool={spool_id}"
    if box > 0:
        total = _qr_module_count(content)
        actual_box = max(1, min(16, int(box)))
        return Response(
            content=_qr_png(content, box=actual_box),
            media_type="image/png",
            headers={
                "X-QR-Dots": str(total * actual_box),
                "X-QR-Modules": str(total),
                "Cache-Control": "no-store",
            },
        )
    if dots > 0:
        payload, actual = _qr_png_fit(content, dots)
        return Response(
            content=payload,
            media_type="image/png",
            headers={
                "X-QR-Dots": str(actual),
                "X-QR-Modules": str(_qr_module_count(content)),
                "Cache-Control": "no-store",
            },
        )
    return Response(content=_qr_png(content), media_type="image/png")


@router.get("/api/labels/slot/{printer_id}/{ams_id}/{tray_id}.png")
def slot_label(printer_id: int, ams_id: int, tray_id: int, request: Request):
    payload = f"{_base_url(request)}/#bind={printer_id}:{ams_id}:{tray_id}"
    return Response(content=_qr_png(payload), media_type="image/png")


@router.get("/api/labels/sheet", response_class=HTMLResponse)
def label_sheet(request: Request, ids: str = "", session: Session = Depends(get_session)) -> str:
    """打印用标签页：把多盘料生成一张 A4 可打印标签。"""
    wanted = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    spools = session.exec(select(Spool)).all()
    if wanted:
        spools = [s for s in spools if s.id in wanted]

    base = _base_url(request)
    cards = []
    for spool in spools:
        content = f"{base}/#spool={spool.id}"
        data_uri = base64.b64encode(_qr_png(content)).decode("ascii")
        cards.append(f"""
        <div class="card">
          <div class="head">
            <span class="dot" style="background:{spool.color_hex}"></span>
            <span class="name">{spool.name}</span>
          </div>
          <img src="data:image/png;base64,{data_uri}" alt="qr" />
          <div class="meta">
            <div>编号 #{spool.id}</div>
            <div>余量 {spool.remaining_weight:.0f} g / {spool.initial_weight:.0f} g</div>
            <div>皮重 {spool.spool_weight:.0f} g</div>
          </div>
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>耗材标签</title>
<style>
  body {{ font-family: system-ui, "Microsoft YaHei", sans-serif; margin: 16px; }}
  .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
  .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 12px; text-align: center;
           page-break-inside: avoid; }}
  .head {{ display: flex; align-items: center; justify-content: center; gap: 6px;
           font-size: 13px; font-weight: 500; margin-bottom: 6px; }}
  .dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block;
          border: 1px solid #bbb; }}
  .name {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 150px; }}
  img {{ width: 118px; height: 118px; }}
  .meta {{ font-size: 11px; color: #555; line-height: 1.5; margin-top: 4px; }}
  @media print {{ .noprint {{ display: none; }} }}
</style></head>
<body>
  <p class="noprint">共 {len(cards)} 张标签。直接按 Ctrl+P 打印，建议缩放 100%。</p>
  <div class="grid">{"".join(cards)}</div>
</body></html>"""


# ══ 事件流 ═════════════════════════════════════════════════
@router.get("/api/events")
def list_events() -> dict:
    return {"events": hub.events()}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """实时推送。

    注意：HTTP 中间件不会作用于 WebSocket，握手必须单独校验，
    否则带口令部署时 /ws 仍会把全部状态裸奔出去。
    """
    if resolve_session(token_from_request(websocket)) is None:  # type: ignore[arg-type]
        # 必须先 accept 才能给出自定义关闭码；直接 close 只会变成握手期 HTTP 403，
        # 前端拿到的是 1006，无法区分「未登录」和「网络抖动」，就会无限重连。
        await websocket.accept()
        await websocket.close(code=4401, reason="unauthenticated")
        return

    await websocket.accept()
    queue = hub.subscribe()
    try:
        await websocket.send_json({"type": "hello", "data": hub.snapshot()})
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        hub.unsubscribe(queue)
