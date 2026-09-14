"""REST 接口与 WebSocket。

命名沿用一个原则：所有写操作都返回受影响对象的完整状态，方便前端直接刷新。
"""
from __future__ import annotations

import base64
import io
import json
import qrcode
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
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
from ..catalog import (
    BRAND_COLOR_SERIES,
    BRAND_PRESETS,
    COLOR_PRESETS,
    MATERIAL_COLOR_SERIES,
    MATERIALS,
    MODEL_CODE_TO_NAME,
    build_spool_name,
    model_display_name,
    normalize_color,
    spool_weight_options,
)
from ..config import settings
from ..core.deduction import apply_deduction, build_usages, load_usages, resolve_spools
from ..core.hub import hub
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
        "remaining_percent": spool.remaining_percent,
        "is_low": spool.is_low,
        "tray_info_idx": spool.tray_info_idx,
        "tag_uid": spool.tag_uid,
        "location": spool.location,
        "note": spool.note,
        "archived": spool.archived,
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
        "cover_url": job.cover_url,
        "deduction_applied": job.deduction_applied,
        "note": job.note,
        "pending": job.id in hub.pending_jobs() if job.id else False,
    }
    printer = session.get(Printer, job.printer_id)
    data["printer_name"] = printer.name if printer else ""
    if with_filaments:
        data["filaments"] = [u.__dict__ for u in load_usages(job)]
    return data


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


# ══ 系统 ═══════════════════════════════════════════════════
@router.get("/api/system/status")
def system_status(request: Request, session: Session = Depends(get_session)) -> dict:
    acc = hub.account()
    snapshot = hub.snapshot()
    spools = session.exec(select(Spool).where(Spool.archived == False)).all()  # noqa: E712
    jobs = session.exec(select(PrintJob).order_by(PrintJob.id.desc()).limit(20)).all()  # type: ignore[attr-defined]
    return {
        "version": "0.2.0",
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
        },
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
                "label": f"AMS {binding.ams_id + 1} · 槽位 {binding.tray_id + 1}",
            })
    for item in items:
        item["slots"] = slot_of.get(item["id"], [])  # type: ignore[index]
    return {"spools": items}


class SpoolCreate(BaseModel):
    brand: str = ""
    material: str = ""
    color_name: str = ""
    color_hex: str = "#000000"
    name: str = ""
    spool_weight: float = 0.0
    initial_weight: float = 1000.0
    remaining_weight: Optional[float] = None
    location: str = ""
    note: str = ""
    tray_info_idx: str = ""


@router.post("/api/spools")
def create_spool(payload: SpoolCreate, session: Session = Depends(get_session)) -> dict:
    remaining = payload.remaining_weight
    if remaining is None:
        remaining = payload.initial_weight
    spool = Spool(
        name=payload.name or build_spool_name(payload.brand, payload.material, payload.color_name),
        brand=payload.brand,
        material=payload.material,
        color_name=payload.color_name,
        color_hex=normalize_color(payload.color_hex),
        spool_weight=payload.spool_weight,
        initial_weight=payload.initial_weight,
        remaining_weight=round(max(0.0, min(remaining, payload.initial_weight)), 2),
        used_weight=round(max(0.0, payload.initial_weight - remaining), 2),
        location=payload.location,
        note=payload.note,
        tray_info_idx=payload.tray_info_idx,
    )
    session.add(spool)
    session.commit()
    session.refresh(spool)
    return spool_dict(spool)


class SpoolPatch(BaseModel):
    brand: Optional[str] = None
    material: Optional[str] = None
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

    for field in ("brand", "material", "color_name", "name", "location", "note", "tray_info_idx"):
        value = getattr(payload, field)
        if value is not None:
            setattr(spool, field, value)
    if payload.color_hex is not None:
        spool.color_hex = normalize_color(payload.color_hex)
    if payload.spool_weight is not None:
        spool.spool_weight = payload.spool_weight
    if payload.initial_weight is not None:
        spool.initial_weight = payload.initial_weight
    if payload.archived is not None:
        spool.archived = payload.archived
    if payload.remaining_weight is not None:
        spool.remaining_weight = round(max(0.0, payload.remaining_weight), 2)
        spool.used_weight = round(max(0.0, spool.initial_weight - spool.remaining_weight), 2)

    spool.updated_at = utcnow()
    session.add(spool)
    session.commit()
    session.refresh(spool)
    return spool_dict(spool)


@router.delete("/api/spools/{spool_id}")
def delete_spool(spool_id: int, session: Session = Depends(get_session)) -> dict:
    spool = session.get(Spool, spool_id)
    if spool is None:
        raise HTTPException(status_code=404, detail="料盘不存在")
    session.delete(spool)
    session.commit()
    return {"ok": True}


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
            job.filaments_json = json.dumps([e.__dict__ for e in entries], ensure_ascii=False)
            session.add(job)

    session.commit()
    return {"ok": True, "usage": {"id": record.id, "spool_id": target.id, "weight_g": weight}}


# ══ 统计与目录 ═════════════════════════════════════════════
@router.get("/api/stats")
def stats(session: Session = Depends(get_session)) -> dict:
    spools = session.exec(select(Spool)).all()
    jobs = session.exec(select(PrintJob).order_by(PrintJob.id.desc()).limit(200)).all()  # type: ignore[attr-defined]
    records = session.exec(select(UsageRecord).order_by(UsageRecord.id.desc()).limit(1000)).all()  # type: ignore[attr-defined]

    by_material: dict[str, float] = {}
    for spool in spools:
        by_material[spool.material] = round(
            by_material.get(spool.material, 0.0) + spool.remaining_weight, 1
        )

    by_day: dict[str, float] = {}
    for record in records:
        if record.source in ("auto", "manual"):
            day = record.created_at.strftime("%Y-%m-%d")
            by_day[day] = round(by_day.get(day, 0.0) + max(0.0, record.weight_g), 1)

    return {
        "spool_count": len([s for s in spools if not s.archived]),
        "archived_count": len([s for s in spools if s.archived]),
        "remaining_total": round(sum(s.remaining_weight for s in spools if not s.archived), 1),
        "used_total": round(sum(s.used_weight for s in spools), 1),
        "low_count": sum(1 for s in spools if not s.archived and s.is_low),
        "job_count": len(jobs),
        "by_material": by_material,
        "by_day": dict(sorted(by_day.items())[-30:]),
    }


@router.get("/api/catalog")
def catalog() -> dict:
    return {
        "brands": BRAND_PRESETS,
        "materials": MATERIALS,
        "colors": COLOR_PRESETS,
        "color_series": BRAND_COLOR_SERIES,
        "material_color_series": MATERIAL_COLOR_SERIES,
        "spool_weights": {b: spool_weight_options(b) for b in BRAND_PRESETS},
        "model_codes": MODEL_CODE_TO_NAME,
    }


# ══ 二维码标签 ═════════════════════════════════════════════
def _qr_png(content: str) -> bytes:
    qr = qrcode.QRCode(version=None, box_size=8, border=2)
    qr.add_data(content)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.get("/api/labels/spool/{spool_id}.png")
def spool_label(spool_id: int, request: Request, session: Session = Depends(get_session)):
    spool = session.get(Spool, spool_id)
    if spool is None:
        raise HTTPException(status_code=404, detail="料盘不存在")
    return Response(content=_qr_png(f"{_base_url(request)}/#spool={spool_id}"), media_type="image/png")


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
