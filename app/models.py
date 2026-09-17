"""数据库模型。

数据流概览：
  拓竹云 ──> CloudAccount（账号与令牌）
            └─> Printer（设备，来自云设备列表）
  云 MQTT ──> 实时槽位状态（内存态，不落库）
  云任务历史 ──> PrintJob（一次打印任务，含每槽位克重）
                  └─> UsageRecord（扣重流水）──> Spool（料盘余量）

SlotBinding 维护「AMS 槽位 → 当前装着的料盘」的映射，是自动扣重的落点。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """统一的 UTC 时间戳。

    刻意返回 naive datetime：SQLite 不保存时区，aware/naive 混用会在比较时炸掉。
    全项目一律用「无时区的 UTC」，展示时再按本地时区格式化。
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_cloud_time(value: str) -> Optional[datetime]:
    """解析拓竹云返回的 ISO 时间（如 2023-12-21T19:02:16Z）为 naive UTC。"""
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(str(value)[:19], "%Y-%m-%dT%H:%M:%S")
            return parsed
        except ValueError:
            return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


class CloudAccount(SQLModel, table=True):
    """拓竹云账号。单实例部署通常只有一行。"""

    __tablename__ = "cloud_account"

    id: Optional[int] = Field(default=None, primary_key=True)
    region: str = "china"           # china / global
    account: str = ""               # 邮箱或手机号
    # 加密后的登录密码（可选）。仅当用户希望令牌过期后自动重新登录时才需要。
    password_enc: str = ""
    access_token: str = ""
    refresh_token: str = ""
    uid: str = ""                   # 形如 u_123456789
    token_expires_at: Optional[datetime] = None
    # ok / need_code / need_tfa / error / logged_out
    status: str = "logged_out"
    status_message: str = ""
    last_login_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=utcnow)


class Printer(SQLModel, table=True):
    """一台打印机。来自云设备列表（含设备访问码，局域网可用时也用得上）。"""

    __tablename__ = "printer"

    id: Optional[int] = Field(default=None, primary_key=True)
    serial: str = Field(index=True, unique=True)
    name: str = ""
    model_code: str = ""            # 底层型号码，如 C12 / BL-P001 / N7-V2
    model: str = ""                 # 映射后的展示名，如 P2S
    access_code: str = ""
    online: bool = False
    enabled: bool = True
    note: str = ""
    last_seen: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)


class Spool(SQLModel, table=True):
    """一盘耗材。所有克重单位为 g。"""

    __tablename__ = "spool"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = ""
    brand: str = ""
    material: str = ""
    # 外观（也叫表面工艺）：普通 / 亮面 / 哑光 / 丝绸 / 磨砂 … 自填值也允许。
    # 单独成一列而不是从 color_name 里猜：同一种颜色可能同时有哑光和丝绸两种货。
    finish: str = ""
    color_name: str = ""
    color_hex: str = "#000000"

    spool_weight: float = 0.0        # 空盘皮重
    initial_weight: float = 1000.0   # 满盘净料重
    remaining_weight: float = 1000.0
    used_weight: float = 0.0

    # 整盘（满盘）购买价格，单位 ¥（人民币）。0 表示未登记。
    price: float = 0.0

    # 拓竹官方 RFID 料盘的标识，用于自动识别
    tag_uid: str = ""
    tray_uuid: str = ""
    tray_info_idx: str = ""          # 如 GFA00 / GFL99，对应云任务里的 filamentId

    location: str = ""
    note: str = ""
    archived: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @property
    def total_weight(self) -> float:
        """含盘总重，称重校准时用。"""
        return round(self.spool_weight + self.remaining_weight, 2)

    @property
    def remaining_percent(self) -> float:
        if self.initial_weight <= 0:
            return 0.0
        return round(max(0.0, min(1.0, self.remaining_weight / self.initial_weight)) * 100, 1)

    @property
    def is_low(self) -> bool:
        return self.remaining_weight <= 100.0

    @property
    def price_per_g(self) -> float:
        """每克单价（¥/g），按整盘价与满盘净重折算。用于按用量计算费用。"""
        if self.initial_weight <= 0:
            return 0.0
        return round(self.price / self.initial_weight, 5)

    @property
    def stock_value(self) -> float:
        """当前余量对应的价值（¥）。"""
        return round(self.price_per_g * self.remaining_weight, 2)


class SlotBinding(SQLModel, table=True):
    """AMS 槽位与料盘的绑定关系。ams_id/tray_id 为拓竹上报的原始编号。"""

    __tablename__ = "slot_binding"

    id: Optional[int] = Field(default=None, primary_key=True)
    printer_id: int = Field(index=True)
    ams_id: int = 0
    tray_id: int = 0
    spool_id: Optional[int] = Field(default=None, index=True)
    bound_at: datetime = Field(default_factory=utcnow)
    note: str = ""


class PrintJob(SQLModel, table=True):
    """一次打印任务。"""

    __tablename__ = "print_job"

    id: Optional[int] = Field(default=None, primary_key=True)
    printer_id: int = Field(index=True)
    serial: str = ""
    # 打印机上报的任务标识与云端任务记录 id，用于把两边对上
    task_id: str = Field(default="", index=True)
    cloud_task_id: str = ""
    job_id: str = ""

    title: str = ""
    status: str = "running"          # running / finished / failed / cancelled
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: Optional[datetime] = None
    duration_seconds: int = 0
    progress_at_end: float = 0.0

    # 每槽位用量，JSON 数组：
    # [{index, filament_id, material, color, weight_g, ams_id, tray_id,
    #   spool_id, match_strategy, deducted_g, deducted}]
    filaments_json: str = "[]"
    total_weight_g: float = 0.0
    # 数据来源：cloud_task / manual / none
    source: str = "none"
    # 云端任务给的封面 URL。注意它是 OSS 预签名链接，**30 分钟就过期**，
    # 只能当时抓下来用，存着没意义（留着是为了排查）
    cover_url: str = ""
    # 抓下来存在本地的成果图文件名（空=这次没有）。真正给界面用的是这个
    cover_file: str = ""

    deduction_applied: bool = False
    note: str = ""


class UsageRecord(SQLModel, table=True):
    """一条扣重流水。「使用历史」与「纠错」都建立在这张表上。"""

    __tablename__ = "usage_record"

    id: Optional[int] = Field(default=None, primary_key=True)
    spool_id: Optional[int] = Field(default=None, index=True)
    printer_id: Optional[int] = Field(default=None, index=True)
    job_id: Optional[int] = Field(default=None, index=True)

    ams_id: int = 0
    tray_id: int = 0
    filament_index: int = 0
    weight_g: float = 0.0
    # auto 自动扣重 / manual 手动补录 / calibrate 称重校准 / correction 纠错 / adjust 手动调整
    source: str = "auto"
    note: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Setting(SQLModel, table=True):
    """运行期可改的键值配置。"""

    __tablename__ = "setting"

    key: str = Field(primary_key=True)
    value: str = ""
