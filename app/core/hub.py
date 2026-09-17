"""中枢：账号会话、云 MQTT 连接、打印任务生命周期、自动结算。

整体流程：
  1. 用拓竹账号登录，拿到 accessToken（约 24 小时有效期，到期自动续）
  2. 拉取账号下的设备列表，落库成 Printer
  3. 维持一条账号级云 MQTT 连接，订阅各设备的 report 主题 → 实时槽位状态
  4. 监听打印状态机：进入打印 → 开一条任务；进入完成/失败 → 关任务
  5. 关任务后进入待结算队列，轮询云端任务历史拿到每槽位克重 → 扣减对应料盘

没有打印机时可用 BAMBU_MOCK=1 走模拟数据源，全流程一样跑通。
"""
from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlmodel import select

from ..catalog import model_display_name
from ..cloud.api import ApiClient, AuthRequired, BambuCloudError, token_valid_for
from ..cloud.mock import MockSource
from ..cloud.mqtt import CloudMqttConnection
from ..config import settings
from .covers import save_cover
from ..db import session_scope
from ..models import CloudAccount, Printer, PrintJob, parse_cloud_time, utcnow
from ..notify import notify
from ..security import decrypt, encrypt
from .deduction import (
    apply_deduction,
    build_usages,
    load_usages,
    remain_based_usage,
    resolve_spools,
)
from .status import PrinterState, diff_summary, parse_report

logger = logging.getLogger(__name__)

ACTIVE_STATES = {"PREPARE", "RUNNING", "PAUSE"}
FINISH_STATES = {"FINISH"}
FAIL_STATES = {"FAILED"}
IDLE_STATES = {"IDLE", "OFFLINE"}

# ── AMS 编号语义 ────────────────────────────────────────
# 官方上报的 ams[].id：0..3 是普通 AMS（A/B/C/D），128..131 是 AMS HT（HT A..HT D）。
# tray_now 里 254 表示外挂料盘、255 表示无料。
# 老代码直接拿 ams_id + 1 当编号，AMS HT 就会显示成「129」，必须归一。
AMS_LETTERS = "ABCD"
AMS_HT_FIRST = 128
AMS_HT_LAST = 131
AMS_EXTERNAL = 254


def ams_kind(ams_id: int) -> str:
    """归一 AMS 类型：普通 AMS 还是高温烘干版 AMS HT。"""
    return "ht" if AMS_HT_FIRST <= ams_id <= AMS_HT_LAST else "ams"


def ams_display_name(ams_id: int) -> str:
    """AMS 用 A/B/C/D 编号，AMS HT 用 HT A/HT B 编号。"""
    if AMS_HT_FIRST <= ams_id <= AMS_HT_LAST:
        return f"HT {AMS_LETTERS[ams_id - AMS_HT_FIRST]}"
    if 0 <= ams_id < len(AMS_LETTERS):
        return f"AMS {AMS_LETTERS[ams_id]}"
    return f"AMS {ams_id}"


def clean_ams_model(raw: str, ams_id: int) -> str:
    """部分固件把 AMS 序列号塞进 info 字段（纯数字），这种不能当型号展示。"""
    text = (raw or "").strip()
    if text.isdigit() and len(text) >= 6:
        text = ""
    if text:
        return text
    return "AMS HT" if ams_kind(ams_id) == "ht" else "AMS"


def remain_grams(tray) -> Optional[float]:
    """按 remain 百分比 × 官方标称满重估一个克重。未上报 remain 时返回 None。"""
    if not tray.occupied or tray.remain < 0:
        return None
    return round((tray.tray_weight or 1000.0) * tray.remain / 100.0, 1)


# 云端任务回查最大次数（每次一个轮询周期）
MAX_SETTLE_ATTEMPTS = 10


class PrinterHub:
    def __init__(self) -> None:
        self.states: dict[int, PrinterState] = {}
        self._raw: dict[str, dict] = {}
        self._printer_by_serial: dict[str, int] = {}
        self._mqtt: Optional[CloudMqttConnection] = None
        self._mqtt_token: str = ""
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._queues: set[asyncio.Queue] = set()
        self._open: dict[int, dict] = {}
        self._pending: dict[int, int] = {}
        self._used_cloud_tasks: set[str] = set()
        # 待结算任务的开局余量快照，用于云任务记录缺失时的兜底估算
        self._settle_context: dict[int, dict] = {}
        self._events: deque[dict] = deque(maxlen=300)
        self._tasks: list[asyncio.Task] = []
        self._running = False
        self._token_lock = asyncio.Lock()
        self._mock: Optional[MockSource] = None

        self.mqtt_info: dict[str, Any] = {"connected": False, "message": "", "since": None}
        self.cloud_info: dict[str, Any] = {
            "last_poll": None,
            "last_error": "",
            "tasks_seen": 0,
        }

    # ══ 生命周期 ═══════════════════════════════════════════
    async def start(self) -> None:
        self._running = True
        self._loop = asyncio.get_running_loop()

        if settings.mock_mode:
            self._ensure_mock_printer()
        self._load_printers()

        if settings.mock_mode:
            self._mock = MockSource(self._mock_serial())
            self._mock.start(self._on_mqtt_message)
            logger.info("已启用模拟打印机模式")
        else:
            self._tasks.append(asyncio.create_task(self._token_loop(), name="token-loop"))
            self._tasks.append(asyncio.create_task(self._mqtt_loop(), name="mqtt-loop"))

        self._tasks.append(asyncio.create_task(self._poll_loop(), name="poll-loop"))

    @staticmethod
    def _mock_serial() -> str:
        return "01S00A0000000000"

    def _ensure_mock_printer(self) -> None:
        """模拟模式下也要有一条设备记录，否则状态无处挂载。"""
        serial = self._mock_serial()
        with session_scope() as session:
            printer = session.exec(select(Printer).where(Printer.serial == serial)).first()
            if printer is None:
                printer = Printer(serial=serial)
            printer.name = printer.name or "模拟 P2S"
            printer.model_code = "N7-V2"
            printer.model = model_display_name("N7-V2")
            printer.online = True
            printer.last_seen = utcnow()
            session.add(printer)

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        if self._mqtt:
            self._mqtt.stop()
            self._mqtt = None
        if self._mock:
            self._mock.stop()
            self._mock = None

    # ══ 账号 ═══════════════════════════════════════════════
    def account(self) -> Optional[CloudAccount]:
        with session_scope() as session:
            return session.exec(select(CloudAccount)).first()

    def logged_in(self) -> bool:
        acc = self.account()
        return bool(acc and acc.access_token and acc.status in ("ok", "need_code"))

    def _save_account(self, **fields: Any) -> CloudAccount:
        with session_scope() as session:
            acc = session.exec(select(CloudAccount)).first()
            if acc is None:
                acc = CloudAccount(region=settings.region)
                session.add(acc)
                session.flush()
            for key, value in fields.items():
                setattr(acc, key, value)
            acc.updated_at = utcnow()
            session.add(acc)
            session.flush()
            session.refresh(acc)
            return acc

    async def login(self, account: str, password: str, region: str, remember: bool = True) -> dict:
        api = ApiClient(region)
        try:
            result = api.login(account, password)
        except AuthRequired as exc:
            self._save_account(
                region=region, account=account, status=exc.login_type,
                status_message=str(exc), access_token="", uid="",
            )
            raise
        return await self._finish_login(api, account, region, result, password if remember else "")

    async def request_code(self, account: str, region: str) -> str:
        api = ApiClient(region)
        if "@" in account:
            api.request_email_code(account)
            message = f"验证码已发送到邮箱 {account}"
        else:
            api.request_sms_code(account)
            message = f"验证码已发送到手机 {account}"
        # 记下「正在等验证码」的状态，前端据此显示验证码输入框
        self._save_account(
            region=region, account=account, status="verifyCode",
            status_message=message, access_token="", uid="",
        )
        return message

    async def login_with_code(self, account: str, code: str, region: str) -> dict:
        api = ApiClient(region)
        result = api.login_with_code(account, code)
        return await self._finish_login(api, account, region, result, "")

    async def login_with_tfa(self, account: str, tfa_key: str, code: str, region: str) -> dict:
        api = ApiClient(region)
        result = api.login_with_tfa(tfa_key, code)
        return await self._finish_login(api, account, region, result, "")

    async def _finish_login(
        self, api: ApiClient, account: str, region: str, result: dict, password: str
    ) -> dict:
        token = result.get("access_token", "")
        uid = api.get_uid(token)
        if not uid:
            raise BambuCloudError("已拿到令牌，但无法解析出用户 ID，请稍后重试。")
        expiry = token_expiry_safe(token)
        fields: dict[str, Any] = {
            "region": region,
            "account": account,
            "access_token": token,
            "refresh_token": result.get("refresh_token", ""),
            "uid": uid,
            "token_expires_at": expiry,
            "status": "ok",
            "status_message": "",
            "last_login_at": utcnow(),
        }
        if password:
            fields["password_enc"] = encrypt(password)
        self._save_account(**fields)
        self._emit("账号已登录", f"用户 {uid}，区域 {region}", level="success")

        # 登录成功后立刻同步设备并重连
        try:
            await self.sync_devices()
        except BambuCloudError as exc:
            self._emit("设备同步失败", str(exc), level="warning")
        self._restart_mqtt()
        return {"uid": uid, "region": region, "expires_at": expiry.isoformat() if expiry else None}

    async def logout(self) -> None:
        if self._mqtt:
            self._mqtt.stop()
            self._mqtt = None
        self._save_account(
            access_token="", refresh_token="", password_enc="", uid="",
            token_expires_at=None, status="logged_out", status_message="",
        )
        self._emit("账号已登出", "本地凭据已清除", level="info")

    async def set_region(self, region: str) -> dict:
        """切换拓竹账号区域（china / global）。

        拓竹账号只存在于一个区域：区域选错的表现不是登录失败，而是
        「登录成功却同步不到任何设备」——因为设备列表接口打到了另一个域名上。
        所以已登录状态下必须允许改区域，否则用户只能靠登出重登来纠正。

        有保存密码就顺手在新区域重新登录并同步设备；没有就只改区域，
        把旧令牌清掉并提示重新登录（留着旧令牌只会在错误区域上反复报错）。
        """
        region = (region or "").strip().lower()
        if region not in ApiClient.DOMAINS:
            raise BambuCloudError("区域只能是 china 或 global。")
        acc = self.account()
        if acc is None:
            raise BambuCloudError("尚未登录拓竹账号。")
        if acc.region == region:
            return {"region": region, "relogin": "same", "message": "区域没有变化。"}

        password = decrypt(acc.password_enc)
        self._save_account(region=region)
        if not password:
            if self._mqtt:
                self._mqtt.stop()
                self._mqtt = None
            self._save_account(
                access_token="", refresh_token="", uid="", token_expires_at=None,
                status="logged_out", status_message="区域已切换，请重新登录。",
            )
            self._emit("区域已切换", "请用正确区域的账号重新登录", level="warning")
            return {"region": region, "relogin": "required", "message": "区域已切换，请重新登录。"}

        result = await self.login(acc.account, password, region, remember=True)
        return {
            "region": region,
            "relogin": "ok",
            "message": "区域已切换，并已用保存的密码重新登录。",
            "uid": result.get("uid", ""),
        }

    async def ensure_token(self, force: bool = False) -> str:
        """确保有一枚可用令牌；快过期时用保存的密码自动续期。"""
        async with self._token_lock:
            acc = self.account()
            if acc is None or not acc.access_token:
                raise BambuCloudError("尚未登录拓竹账号。")
            if not force and token_valid_for(acc.access_token, settings.token_renew_before_hours):
                return acc.access_token

            password = decrypt(acc.password_enc)
            if not password:
                self._save_account(
                    status="need_code",
                    status_message="令牌已过期，且没有保存密码，请重新登录。",
                )
                raise BambuCloudError("令牌已过期，请重新登录（或在登录时勾选保存密码以便自动续期）。")

            api = ApiClient(acc.region)
            try:
                result = api.login(acc.account, password)
            except AuthRequired as exc:
                self._save_account(status=exc.login_type, status_message=str(exc))
                raise BambuCloudError(f"自动续期需要验证码：{exc}") from exc

            token = result.get("access_token", "")
            self._save_account(
                access_token=token,
                refresh_token=result.get("refresh_token", ""),
                token_expires_at=token_expiry_safe(token),
                status="ok",
                status_message="",
                last_login_at=utcnow(),
            )
            self._emit("令牌已自动续期", "拓竹账号会话已刷新", level="success")
            self._restart_mqtt()
            return token

    async def _token_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(900)
                if self.account() and self.account().access_token:  # type: ignore[union-attr]
                    await self.ensure_token()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.warning("令牌续期检查失败：%s", exc)

    # ══ 设备 ═══════════════════════════════════════════════
    def _load_printers(self) -> None:
        with session_scope() as session:
            printers = session.exec(select(Printer)).all()
            self._printer_by_serial = {p.serial: p.id for p in printers if p.id}

    async def sync_devices(self) -> list[dict]:
        acc = self.account()
        if acc is None:
            raise BambuCloudError("尚未登录拓竹账号。")
        token = await self.ensure_token()
        api = ApiClient(acc.region)
        devices = api.get_devices(token)

        out: list[dict] = []
        with session_scope() as session:
            for item in devices:
                serial = str(item.get("dev_id") or "").strip()
                if not serial:
                    continue
                code = str(item.get("dev_model_name") or "")
                printer = session.exec(select(Printer).where(Printer.serial == serial)).first()
                if printer is None:
                    printer = Printer(serial=serial)
                printer.name = str(item.get("name") or printer.name or serial[-6:])
                printer.model_code = code
                printer.model = model_display_name(code)
                printer.access_code = str(item.get("dev_access_code") or "")
                printer.online = bool(item.get("online"))
                printer.last_seen = utcnow()
                session.add(printer)
                session.flush()
                out.append({
                    "id": printer.id,
                    "serial": serial,
                    "name": printer.name,
                    "model": printer.model,
                    "online": printer.online,
                })
        self._load_printers()
        self._restart_mqtt()
        return out

    async def refresh_printer_status(self) -> None:
        """从云端设备列表刷新在线状态。"""
        acc = self.account()
        if acc is None:
            return
        try:
            token = await self.ensure_token()
            devices = ApiClient(acc.region).get_devices(token)
        except BambuCloudError:
            return
        online_map = {str(d.get("dev_id")): bool(d.get("online")) for d in devices}
        with session_scope() as session:
            for printer in session.exec(select(Printer)).all():
                if printer.serial in online_map:
                    printer.online = online_map[printer.serial]
                    session.add(printer)

    def printer_records(self) -> list[Printer]:
        with session_scope() as session:
            return list(session.exec(select(Printer)).all())

    # ══ MQTT ═══════════════════════════════════════════════
    def _restart_mqtt(self) -> None:
        if settings.mock_mode:
            return
        acc = self.account()
        if acc is None or not acc.access_token or not acc.uid:
            return
        if self._mqtt and self._mqtt_token == acc.access_token:
            return
        if self._mqtt:
            self._mqtt.stop()
        api = ApiClient(acc.region)
        self._mqtt = CloudMqttConnection(
            host=api.mqtt_host,
            username=acc.uid,
            password=acc.access_token,
            on_message=self._on_mqtt_message,
            on_status=self._on_mqtt_status,
            keepalive=settings.mqtt_keepalive,
        )
        self._mqtt_token = acc.access_token
        self._mqtt.set_serials(self._enabled_serials())
        self._mqtt.start()

    def _enabled_serials(self) -> list[str]:
        with session_scope() as session:
            return [
                p.serial
                for p in session.exec(select(Printer).where(Printer.enabled == True)).all()  # noqa: E712
            ]

    async def _mqtt_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(15)
                acc = self.account()
                if acc and acc.access_token:
                    self._restart_mqtt()
                    if self._mqtt:
                        self._mqtt.set_serials(self._enabled_serials())
                    # 云端设备在线状态变慢，低频刷新即可
                    if int(datetime.now().timestamp()) % 300 < 20:
                        await self.refresh_printer_status()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.warning("MQTT 维护循环异常：%s", exc)

    def _on_mqtt_status(self, scope: str, connected: bool, message: str) -> None:
        self.mqtt_info = {
            "connected": connected,
            "message": message,
            "since": utcnow().isoformat(),
        }
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(
                    self.broadcast({"type": "mqtt", "connected": connected, "message": message})
                )
            )

    def _on_mqtt_message(self, serial: str, payload: dict) -> None:
        """从 paho 线程或模拟线程回调进来，切回事件循环处理。"""
        if self._loop is None or not self._loop.is_running():
            return
        self._loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self._apply_payload(serial, payload))
        )

    # ══ 状态处理 ═══════════════════════════════════════════
    async def _apply_payload(self, serial: str, payload: dict) -> None:
        block = payload.get("print")
        if not isinstance(block, dict):
            return
        # P1/A1 只推增量，这里做一层合并后再解析
        merged = {**(self._raw.get(serial) or {}), **block}
        self._raw[serial] = merged

        state = parse_report({"print": merged}, serial)
        if state is None:
            return

        printer_id = self._printer_by_serial.get(serial)
        if printer_id is None:
            self._load_printers()
            printer_id = self._printer_by_serial.get(serial)
            if printer_id is None:
                return

        old = self.states.get(printer_id)
        self.states[printer_id] = state

        for text in diff_summary(old, state):
            self._emit(text, state.subtask_name or state.serial, level="info")

        await self._handle_transition(printer_id, serial, old, state)
        await self.broadcast({"type": "state", "printer_id": printer_id, "data": self.state_dict(state, printer_id)})

    async def _handle_transition(
        self,
        printer_id: int,
        serial: str,
        old: Optional[PrinterState],
        new: PrinterState,
    ) -> None:
        job = self._open.get(printer_id)
        active = new.gcode_state in ACTIVE_STATES

        if active:
            # 同一台机器上换了任务
            if job and new.task_id and job.get("task_id") and job["task_id"] != new.task_id:
                await self._close_job(printer_id, serial, job, "cancelled", new)
                job = None
                self._open.pop(printer_id, None)

            if not job:
                self._open[printer_id] = {
                    "task_id": new.task_id,
                    "title": new.subtask_name or new.gcode_file or "未命名任务",
                    "started_at": utcnow(),
                    "remain_start": {
                        f"{t.ams_id}:{t.tray_id}": t.remain for t in new.loaded_trays
                    },
                    "last_progress": new.progress,
                }
                self._emit("开始打印", f"{new.subtask_name or '任务'}", level="info")
            else:
                job["last_progress"] = max(job.get("last_progress", 0), new.progress)
                if not job.get("task_id") and new.task_id:
                    job["task_id"] = new.task_id
                if not job.get("title") and (new.subtask_name or new.gcode_file):
                    job["title"] = new.subtask_name or new.gcode_file
            return

        if not job:
            return

        if new.gcode_state in FINISH_STATES:
            await self._close_job(printer_id, serial, job, "finished", new)
        elif new.gcode_state in FAIL_STATES:
            await self._close_job(printer_id, serial, job, "failed", new)
        elif new.gcode_state in IDLE_STATES:
            progress = max(job.get("last_progress", 0), new.progress)
            status = "finished" if progress >= 99 else "cancelled"
            await self._close_job(printer_id, serial, job, status, new)
        else:
            return
        self._open.pop(printer_id, None)

    async def _close_job(
        self,
        printer_id: int,
        serial: str,
        job: dict,
        status: str,
        state: PrinterState,
    ) -> None:
        progress = max(job.get("last_progress", 0), state.progress)
        started = job.get("started_at") or utcnow()
        finished = utcnow()
        duration = int((finished - started).total_seconds())

        if status == "cancelled" and progress < settings.min_progress_to_record:
            self._emit("忽略误触任务", f"进度仅 {progress}%", level="info")
            return

        with session_scope() as session:
            record = PrintJob(
                printer_id=printer_id,
                serial=serial,
                task_id=str(job.get("task_id") or ""),
                title=str(job.get("title") or "未命名任务"),
                status=status,
                started_at=started,
                finished_at=finished,
                duration_seconds=duration,
                progress_at_end=progress,
                source="none",
                note="",
            )
            session.add(record)
            session.flush()
            job_id = record.id

        label = {"finished": "已完成", "failed": "已失败", "cancelled": "已取消"}.get(status, status)
        self._emit(f"打印{label}", f"{job.get('title')} · 用了 {duration // 60} 分钟", level="info")

        should_settle = settings.auto_deduct and (
            status == "finished" or (status == "failed" and settings.deduct_on_failure)
        )
        if should_settle and job_id:
            job["remain_end"] = {f"{t.ams_id}:{t.tray_id}": t.remain for t in state.loaded_trays}
            self._settle_context[job_id] = job
            self._pending[job_id] = 0
            await self.broadcast({"type": "job_created", "job_id": job_id})

    # ══ 结算 ═══════════════════════════════════════════════
    async def _poll_loop(self) -> None:
        # 启动后先等一会儿，避免和初始化抢资源
        await asyncio.sleep(20)
        while self._running:
            try:
                if self._pending:
                    await self.settle_pending()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.warning("任务轮询异常：%s", exc)
                self.cloud_info["last_error"] = str(exc)
            await asyncio.sleep(settings.task_poll_interval)

    async def fetch_cloud_tasks(self) -> list[dict]:
        if settings.mock_mode:
            self.cloud_info["last_poll"] = utcnow().isoformat()
            return [self._mock.build_task()] if self._mock else []

        acc = self.account()
        if acc is None:
            return []
        token = await self.ensure_token()
        tasks = ApiClient(acc.region).get_tasks(token)
        self.cloud_info["last_poll"] = utcnow().isoformat()
        self.cloud_info["tasks_seen"] = len(tasks)
        self.cloud_info["last_error"] = ""
        return tasks

    @staticmethod
    def match_task(job: PrintJob, tasks: list[dict], used: set[str]) -> Optional[dict]:
        candidates = [
            t for t in tasks
            if str(t.get("deviceId") or "") == job.serial
            and str(t.get("id") or "") not in used
        ]
        if not candidates:
            return None

        # 1) 打印机上报的 task_id 直接命中云端记录
        if job.task_id:
            for t in candidates:
                if str(t.get("id")) == str(job.task_id):
                    return t

        # 2) 时间窗口 + 标题加权
        window_end = (job.finished_at or job.started_at) + timedelta(
            minutes=settings.task_match_window_minutes
        )
        window_start = job.started_at - timedelta(minutes=10)
        best: Optional[dict] = None
        best_score: Optional[tuple] = None
        for t in candidates:
            start = parse_cloud_time(str(t.get("startTime") or ""))
            if start is None:
                continue
            if not (window_start <= start <= window_end):
                continue
            delta = abs((start - job.started_at).total_seconds())
            title = str(t.get("title") or "")
            title_penalty = 0 if (job.title and job.title.split(".")[0] in title) else 1
            score = (title_penalty, delta)
            if best_score is None or score < best_score:
                best_score = score
                best = t
        return best

    async def settle_pending(self, force_job_id: Optional[int] = None) -> dict:
        """尝试为待结算任务拉取云端用量并扣重。"""
        targets = [force_job_id] if force_job_id else list(self._pending.keys())
        if not targets:
            return {"settled": 0, "waiting": 0, "failed": 0}

        try:
            tasks = await self.fetch_cloud_tasks()
        except BambuCloudError as exc:
            self.cloud_info["last_error"] = str(exc)
            return {"settled": 0, "waiting": len(targets), "failed": 0, "error": str(exc)}

        settled = waiting = failed = 0
        for job_id in targets:
            with session_scope() as session:
                job = session.get(PrintJob, job_id)
                if job is None or job.deduction_applied:
                    self._pending.pop(job_id, None)
                    continue

                task = self.match_task(job, tasks, self._used_cloud_tasks)
                if task is None:
                    attempts = self._pending.get(job_id, 0) + 1
                    if attempts >= MAX_SETTLE_ATTEMPTS:
                        job.note = "云端未找到对应的任务记录（可能是本地打印），可手动录入用量或重试。"
                        session.add(job)
                        self._pending.pop(job_id, None)
                        failed += 1
                        await notify("耗材未自动扣减", f"{job.title}：云端没有对应记录")
                    else:
                        self._pending[job_id] = attempts
                        waiting += 1
                    continue

                state = self.states.get(job.printer_id)
                usages = build_usages(task, state)
                if not usages:
                    # 明细为空时退回用总量
                    total = task.get("weight") or 0
                    if total:
                        usages = build_usages(
                            {"weight": total, "amsDetailMapping": [{"weight": total}]}, state
                        )
                resolve_spools(session, job.printer_id, usages)

                if job.status == "failed":
                    factor = max(0.0, min(1.0, (job.progress_at_end or 0) / 100.0))
                    for usage in usages:
                        usage.weight_g = round(usage.weight_g * factor, 3)
                        usage.match_strategy += f"（失败任务按 {int(factor * 100)}% 计）"

                total = apply_deduction(session, job, usages)
                job.cloud_task_id = str(task.get("id") or "")
                job.source = "cloud_task"
                cover = str(task.get("cover") or "")
                job.cover_url = cover
                # 封面是 OSS 预签名链接，30 分钟就过期——必须现在抓下来存本地，
                # 存 URL 过一会儿就是 403。抓图失败不影响扣重（save_cover 内部吞异常）。
                if cover and not job.cover_file and job.id:
                    job.cover_file = await asyncio.to_thread(
                        save_cover, cover, int(job.id)
                    )
                session.add(job)
                self._used_cloud_tasks.add(str(task.get("id")))
                self._pending.pop(job_id, None)
                settled += 1

                self._emit(
                    "已自动扣重",
                    f"{job.title} · 共 {total} g",
                    level="success",
                )
                await notify(
                    "耗材已自动扣重",
                    f"{job.title}\n本次消耗 {total} g，已扣减对应料盘。",
                )
                await self.broadcast({"type": "job_settled", "job_id": job_id})

        return {"settled": settled, "waiting": waiting, "failed": failed}

    def retry_settle(self, job_id: int) -> None:
        self._pending[job_id] = 0

    def pending_jobs(self) -> list[int]:
        return list(self._pending.keys())

    def remain_fallback(self, job_id: int) -> list[dict]:
        """手动触发的兜底：用 AMS 余量差值估算。"""
        context = self._settle_context.get(job_id) or {}
        with session_scope() as session:
            job = session.get(PrintJob, job_id)
            if job is None:
                return []
            state = self.states.get(job.printer_id)
        usages = remain_based_usage(state, context.get("remain_start") or {})
        return [u.__dict__ for u in usages]

    # ══ 对外快照 ═══════════════════════════════════════════
    def state_dict(self, state: PrinterState, printer_id: int) -> dict:
        # 辅助风扇：P2S / X2 把它报在自适应风道组件里（state 已是百分比），
        # 其它机型走 big_fan1（0-15 档位）。谁有就用谁，两者都没有则用 big_fan1 的 0。
        aux_pct = (
            state.airduct_fan_pct
            if state.airduct_fan_pct is not None
            else state.aux_fan_pct
        )
        return {
            "printer_id": printer_id,
            "serial": state.serial,
            "online": state.online,
            "gcode_state": state.gcode_state,
            "state_label": state.state_label,
            "stage_label": state.stage_label,
            "progress": state.progress,
            "remaining_minutes": state.remaining_minutes,
            "layer_num": state.layer_num,
            "total_layer_num": state.total_layer_num,
            "subtask_name": state.subtask_name,
            "task_id": state.task_id,
            "nozzle_temper": state.nozzle_temper,
            "nozzle_target": state.nozzle_target,
            "bed_temper": state.bed_temper,
            "bed_target": state.bed_target,
            "chamber_temper": state.chamber_temper,
            "chamber_target": state.chamber_target,
            # 全部为百分比（0/10/…/100）。命名对齐拓竹官方 App 的「空调系统」页：
            #   cooling=部件 / aux=右(辅助) / secondary=左(辅助) / exhaust=外排
            #   chamber 只在没有自适应风道组件的机型（X1/P1/A1/H2）上是「腔体风扇」
            # secondary / exhaust 为 null 表示机器没装那一件（选配件）
            "fans": {
                "cooling": state.cooling_fan_pct,
                "aux": aux_pct,
                "chamber": state.chamber_fan_pct,
                "heatbreak": state.heatbreak_fan_pct,
                "secondary": state.secondary_aux_fan_pct,
                "exhaust": state.exhaust_fan_pct,
            },
            "wifi_signal": state.wifi_signal,
            "lights": state.lights,
            "hms": [h.__dict__ for h in state.hms],
            "tray_now": state.tray_now,
            "updated_at": state.updated_at.isoformat(),
            "ams": [
                {
                    "ams_id": unit.ams_id,
                    "kind": ams_kind(unit.ams_id),
                    "name": ams_display_name(unit.ams_id),
                    "model": clean_ams_model(unit.model, unit.ams_id),
                    "humidity": unit.humidity,
                    "temp": unit.temp,
                    "slot_count": len(unit.trays),
                    "trays": [
                        {
                            "ams_id": t.ams_id,
                            "tray_id": t.tray_id,
                            "slot_index": t.slot_index,
                            "occupied": t.occupied,
                            "label": t.label,
                            "tray_type": t.tray_type,
                            "sub_brands": t.sub_brands,
                            "color": t.color,
                            "remain": t.remain,
                            "remain_weight_g": remain_grams(t),
                            "info_idx": t.info_idx,
                            "has_rfid": t.has_rfid,
                            "tray_weight": t.tray_weight,
                            "is_active": state.tray_now == t.slot_index,
                        }
                        for t in unit.trays
                    ],
                }
                for unit in state.ams_units
            ],
            "external_spool": (
                {
                    "occupied": state.external_spool.occupied,
                    "label": state.external_spool.label,
                    "tray_type": state.external_spool.tray_type,
                    "color": state.external_spool.color,
                    "remain": state.external_spool.remain,
                    "remain_weight_g": remain_grams(state.external_spool),
                    "has_rfid": state.external_spool.has_rfid,
                    "is_active": state.tray_now == AMS_EXTERNAL,
                }
                if state.external_spool
                else None
            ),
            "mqtt_signature_required": state.mqtt_signature_required,
        }

    def snapshot(self) -> dict:
        out = []
        for printer in self.printer_records():
            state = self.states.get(printer.id or -1)
            out.append({
                "printer": {
                    "id": printer.id,
                    "serial": printer.serial,
                    "name": printer.name,
                    "model": printer.model,
                    "model_code": printer.model_code,
                    "online": printer.online,
                    "enabled": printer.enabled,
                    "note": printer.note,
                },
                "state": self.state_dict(state, printer.id or 0) if state else None,
            })
        return {
            "printers": out,
            "mock": settings.mock_mode,
            "mqtt": self.mqtt_info,
            "cloud": self.cloud_info,
            "pending_jobs": self.pending_jobs(),
        }

    # ══ 事件与广播 ═════════════════════════════════════════
    def _emit(self, title: str, detail: str = "", level: str = "info") -> None:
        event = {
            "type": "event",
            "title": title,
            "detail": detail,
            "level": level,
            "at": utcnow().isoformat(),
        }
        self._events.appendleft(event)
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.broadcast(event))
            )

    def events(self) -> list[dict]:
        return list(self._events)

    async def broadcast(self, event: dict) -> None:
        dead = []
        for queue in list(self._queues):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(queue)
        for queue in dead:
            self._queues.discard(queue)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._queues.discard(queue)


def token_expiry_safe(token: str):
    from ..cloud.api import token_expiry

    return token_expiry(token)


hub = PrinterHub()
